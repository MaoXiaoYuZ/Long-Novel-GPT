import datetime

from config import API_COST_LIMITS, MONOGODB_DB_NAME

from .chat_messages import ChatMessages
from .mongodb_init import mongo_client as client

def record_api_cost(messages: ChatMessages):
    """记录API调用费用"""

    db = client[MONOGODB_DB_NAME]
    collection = db['api_cost']

    cost_data = {
        'created_at': datetime.datetime.now(),
        'model': messages.model,
        'cost': messages.cost,
        'currency_symbol': messages.currency_symbol,
        'input_tokens': messages[:-1].count_message_tokens(),
        'output_tokens': messages[-1:].count_message_tokens(),
        'total_tokens': messages.count_message_tokens()
    }
    collection.insert_one(cost_data)

def get_model_cost_stats(start_date: datetime.datetime, end_date: datetime.datetime) -> list:
    """获取指定时间段内的模型调用费用统计"""
    pipeline = [
        {
            '$match': {
                'created_at': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }
        },
        {
            '$group': {
                '_id': '$model',
                'total_cost': { '$sum': '$cost' },
                'total_calls': { '$sum': 1 },
                'total_input_tokens': { '$sum': '$input_tokens' },
                'total_output_tokens': { '$sum': '$output_tokens' },
                'total_tokens': { '$sum': '$total_tokens' },
                'avg_cost_per_call': { '$avg': '$cost' },
                'currency_symbol': { '$first': '$currency_symbol' }
            }
        },
        {
            '$project': {
                'model': '$_id',
                'total_cost': { '$round': ['$total_cost', 4] },
                'total_calls': 1,
                'total_input_tokens': 1,
                'total_output_tokens': 1,
                'total_tokens': 1,
                'avg_cost_per_call': { '$round': ['$avg_cost_per_call', 4] },
                'currency_symbol': 1,
                '_id': 0
            }
        },
        {
            '$sort': { 'total_cost': -1 }
        }
    ]
    
    # 直接从 api_cost 集合查询数据
    db = client[MONOGODB_DB_NAME]
    collection = db['api_cost']

    stats = list(collection.aggregate(pipeline))
    return stats

# 使用示例：
def print_cost_report(days: int = 30, hours: int = 0):
    """打印最近N天的费用报告"""
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days, hours=hours)
    
    stats = get_model_cost_stats(start_date, end_date)
    
    print(f"\n=== API Cost Report ({start_date.date()} to {end_date.date()}) ===")
    for model_stat in stats:
        print(f"\nModel: {model_stat['model']}")
        print(f"Total Cost: {model_stat['currency_symbol']}{model_stat['total_cost']:.4f}")
        print(f"Total Calls: {model_stat['total_calls']}")
        print(f"Total Tokens: {model_stat['total_tokens']:,}")
        print(f"Avg Cost/Call: {model_stat['currency_symbol']}{model_stat['avg_cost_per_call']:.4f}")

def check_cost_limits() -> bool:
    """
    检查API调用费用是否超过限制
    返回: 如果未超过限制返回True，否则返回False
    """
    now = datetime.datetime.now()
    hour_ago = now - datetime.timedelta(hours=1)
    day_ago = now - datetime.timedelta(days=1)
    
    # 获取统计数据
    hour_stats = get_model_cost_stats(hour_ago, now)
    day_stats = get_model_cost_stats(day_ago, now)
    
    # 计算总费用并根据需要转换为人民币
    hour_total_rmb = sum(
        stat['total_cost'] * (API_COST_LIMITS['USD_TO_RMB_RATE'] if stat['currency_symbol'] == '$' else 1)
        for stat in hour_stats
    )
    day_total_rmb = sum(
        stat['total_cost'] * (API_COST_LIMITS['USD_TO_RMB_RATE'] if stat['currency_symbol'] == '$' else 1)
        for stat in day_stats
    )
    
    # 检查是否超过限制
    if hour_total_rmb >= API_COST_LIMITS['HOURLY_LIMIT_RMB']:
        print(f"警告：最近1小时API费用（￥{hour_total_rmb:.2f}）超过限制（￥{API_COST_LIMITS['HOURLY_LIMIT_RMB']}）")
        raise Exception("最近1小时内API调用费用超过设定上限！")
    
    if day_total_rmb >= API_COST_LIMITS['DAILY_LIMIT_RMB']:
        print(f"警告：最近24小时API费用（￥{day_total_rmb:.2f}）超过限制（￥{API_COST_LIMITS['DAILY_LIMIT_RMB']}）")
        raise Exception("最近1天内API调用费用超过设定上限！")
    
    return True