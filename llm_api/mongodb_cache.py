import time
import functools
from typing import Generator, Any
from pymongo import MongoClient
import hashlib
import json
import datetime
import random

from config import ENABLE_MONOGODB, ENABLE_MONOGODB_CACHE, CACHE_REPLAY_SPEED, CACHE_REPLAY_MAX_DELAY

from .chat_messages import ChatMessages
from .mongodb_cost import record_api_cost, check_cost_limits
from .mongodb_init import mongo_client as client

def create_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """创建缓存键"""
    # 将参数转换为可序列化的格式
    cache_dict = {
        'func_name': func_name,
        'args': args,
        'kwargs': kwargs
    }
    # 转换为JSON字符串并创建哈希
    cache_string = json.dumps(cache_dict, sort_keys=True)
    return hashlib.md5(cache_string.encode()).hexdigest()



def llm_api_cache(db_name: str, collection_name: str):
    """MongoDB缓存装饰器"""
    
    def dummy_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 移除 use_cache 参数，避免传递给原函数
            kwargs.pop('use_cache', None)
            return func(*args, **kwargs)
        return wrapper
    

    if not ENABLE_MONOGODB:
        return dummy_decorator
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            check_cost_limits()

            use_cache = kwargs.pop('use_cache', True)   # pop很重要
            
            if not ENABLE_MONOGODB_CACHE:
                use_cache = False

            db = client[db_name]
            collection = db[collection_name]
            
            # 创建缓存键
            cache_key = create_cache_key(func.__name__, args, kwargs)
            
            # 检查缓存
            if use_cache:
                cached_data = list(collection.aggregate([
                    {'$match': {'cache_key': cache_key}},
                    {'$sample': {'size': 1}}
                ]))
                cached_data = cached_data[0] if cached_data else None
                if cached_data:
                    # 如果有缓存，yield缓存的结果
                    messages = ChatMessages(cached_data['return_value'])
                    prompt_messages = messages if messages[-1]['role'] == 'user' else messages[:-1]
                    for item in cached_data['yields']:
                        time.sleep(min(item['delay'] / CACHE_REPLAY_SPEED, CACHE_REPLAY_MAX_DELAY))  # 应用加速倍数
                        if item['index'] > 0:
                            yield prompt_messages + [{'role': 'assistant', 'content': messages.response[:item['index']]}]
                        else:
                            yield prompt_messages
                    return messages
            
            # 如果没有缓存，执行原始函数并记录结果
            yields_data = []
            last_time = time.time()
            
            generator = func(*args, **kwargs)
            
            try:
                while True:
                    current_time = time.time()
                    value = next(generator)
                    delay = current_time - last_time
                    
                    yields_data.append({
                        'index': len(value.response),
                        'delay': delay
                    })
                    
                    last_time = current_time
                    yield value
                    
            except StopIteration as e:
                return_value = e.value
                
                # 记录API调用费用
                record_api_cost(return_value)
                
                # 存储到MongoDB
                cache_data = {
                    'created_at':datetime.datetime.now(),
                    'return_value': return_value,
                    'func_name': func.__name__,
                    'args': args,
                    'kwargs': kwargs,
                    'yields': yields_data,
                    'cache_key': cache_key,
                }
                collection.insert_one(cache_data)
                
                return return_value
            
        return wrapper
    return decorator
