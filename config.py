MAX_THREAD_NUM = 5 # 生成时采用的最大线程数

RENDER_SETTING_API_TEST_BTN = True # 是否在API测试界面显示测试按钮
ENABLE_SETTING_SELECT_SUB_MODEL = True # 是否允许选择自行选择辅助模型
RENDER_SAVE_LOAD_BTN = False # 是否显示保存和加载按钮
RENDER_STOP_BTN = False # 是否显示暂停按钮（目前暂停按钮有些小问题，默认关闭）


ENABLE_MONOGODB = False # 是否启用MongoDB，启用后下面三项才有效。本机上启动了MongoDB服务后可以将此项设为True。
MONOGODB_DB_NAME = 'llm_api'
ENABLE_MONOGODB_CACHE = True # 是否启用API缓存
CACHE_REPLAY_SPEED = 2  # 缓存命中后2倍速重放
CACHE_REPLAY_MAX_DELAY = 5 # 缓存命中后最大延迟时间，按秒计算


# API费用限制设置，需要依赖于MonogoDB
API_COST_LIMITS = {
    'HOURLY_LIMIT_RMB': 100,  # 每小时费用上限（人民币）
    'DAILY_LIMIT_RMB': 500,   # 每天费用上限（人民币）
    'USD_TO_RMB_RATE': 7     # 美元兑人民币汇率
}

# 用于配置API，在这里配置可以省去每次启动时在Gradio界面中手动配置的麻烦
API_SETTINGS = {
    # model字典用于配置主模型，如果是OpenAI模型，则api_key和base_url必填；如果文心模型，则ak和sk必填。
    'model': {
        'model': 'gpt-4o',
        'base_url': '',
        'api_key': '',
        'max_tokens': 4096
    },
    # sub_model字典用于配置辅助模型，辅助模型仅仅用于完成一些简单任务，不要选择费用高的模型！！！
    'sub_model': {
        'model': 'gpt-4o-mini',
        'base_url': '',
        'api_key': '',
        'max_tokens': 4096
    },
    'wenxin': {
        'ak': '',
        'sk': '',
    },
    'doubao': {
        'api_key': '',
        'main_endpoint_id': '',
        'sub_endpoint_id': '',
    },
    'gpt': {
        'base_url': '',
        'api_key': '',
        'proxies': '',
    },
    'zhipuai': {
        'api_key': '',
    },
    'others': {
        'base_url': '',
        'api_key': '',
        'default_model': '',
        'default_sub_model': '',
        'available_models': [
        ]
    }
}
