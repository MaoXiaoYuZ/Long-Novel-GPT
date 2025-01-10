import hashlib
import re
import json
import os

def count_characters(text):
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    english_pattern = re.compile(r'[a-zA-Z]+')
    other_pattern = re.compile(r'[^\u4e00-\u9fffa-zA-Z]+')

    chinese_characters = chinese_pattern.findall(text)
    english_characters = english_pattern.findall(text)
    other_characters = other_pattern.findall(text)

    chinese_count = sum(len(char) for char in chinese_characters)
    english_count = sum(len(char) for char in english_characters)
    other_count = sum(len(char) for char in other_characters)

    return chinese_count, english_count, other_count


model_config = {}


model_prices = {}
try:
    model_prices_path = os.path.join(os.path.dirname(__file__), 'model_prices.json')
    with open(model_prices_path, 'r') as f:
        model_prices = json.load(f)
except Exception as e:
    print(f"Warning: Failed to load model_prices.json: {e}")

class ChatMessages(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.model = kwargs['model'] if 'model' in kwargs else None
        self.finished = False
        
        assert 'currency_symbol' not in kwargs

        if not model_config:
            from .baidu_api import wenxin_model_config
            from .doubao_api import doubao_model_config
            from .openai_api import gpt_model_config
            from .zhipuai_api import zhipuai_model_config
            model_config.update({**wenxin_model_config, **doubao_model_config, **gpt_model_config, **zhipuai_model_config})
    
    def __getitem__(self, index):
        result = super().__getitem__(index)
        if isinstance(index, slice):
            return ChatMessages(result, model=self.model)
        return result
    
    def __add__(self, other):
        if isinstance(other, list):
            return ChatMessages(super().__add__(other), model=self.model)
        return NotImplemented 

    def count_message_tokens(self):
        return self.get_estimated_tokens()
    
    def copy(self):
        return ChatMessages(self, model=self.model)
    
    def get_estimated_tokens(self):
        num_tokens = 0
        for message in self:
            for key, value in message.items():
                chinese_count, english_count, other_count = count_characters(value)
                num_tokens += chinese_count // 2 + english_count // 5 + other_count // 2
        return num_tokens
    
    def get_prompt_messages_hash(self):
        # 转换为JSON字符串并创建哈希
        cache_string = json.dumps(self.prompt_messages, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    @property
    def cost(self):
        if len(self) == 0:
            return 0
        
        if self.model in model_config:
            return model_config[self.model]["Pricing"][0] * self[:-1].count_message_tokens() / 1_000 + model_config[self.model]["Pricing"][1] * self[-1:].count_message_tokens() / 1_000
        elif self.model in model_prices:
            return (
                model_prices[self.model]["input_cost_per_token"] * self[:-1].count_message_tokens() +
                model_prices[self.model]["output_cost_per_token"] * self[-1:].count_message_tokens()
            )
        return 0
    
    @property
    def response(self):
        return self[-1]['content'] if self[-1]['role'] == 'assistant' else ''
    
    @property
    def prompt_messages(self):
        return self[:-1] if self.response else self
    
    @property
    def currency_symbol(self):
        if self.model in model_config:
            return model_config[self.model]["currency_symbol"]
        else:
            return '$'
    
    @property
    def cost_info(self):
        formatted_cost = f"{self.cost:.7f}".rstrip('0').rstrip('.')
        return f"{self.model}: {formatted_cost}{self.currency_symbol}"
    
    def print(self):
        for message in self:
            print(f"{message['role']}".center(100, '-') + '\n')
            print(message['content'])
            print()
