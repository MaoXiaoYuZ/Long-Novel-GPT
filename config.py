import os
from dotenv import dotenv_values, load_dotenv

print("Loading .env file...")
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    env_dict = dotenv_values(env_path)
    
    print("Environment variables to be loaded:")
    for key, value in env_dict.items():
        print(f"{key}={value}")
    print("-" * 50)
    
    os.environ.update(env_dict)
    print(f"Loaded environment variables from: {env_path}")
else:
    print("Warning: .env file not found")


# Thread Configuration
MAX_THREAD_NUM = int(os.getenv('MAX_THREAD_NUM', 5))

# MongoDB Configuration
ENABLE_MONOGODB = os.getenv('ENABLE_MONGODB', 'false').lower() == 'true'
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://127.0.0.1:27017/')
MONOGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'llm_api')
ENABLE_MONOGODB_CACHE = os.getenv('ENABLE_MONGODB_CACHE', 'true').lower() == 'true'
CACHE_REPLAY_SPEED = float(os.getenv('CACHE_REPLAY_SPEED', 2))
CACHE_REPLAY_MAX_DELAY = float(os.getenv('CACHE_REPLAY_MAX_DELAY', 5))

# API Cost Limits
API_COST_LIMITS = {
    'HOURLY_LIMIT_RMB': float(os.getenv('API_HOURLY_LIMIT_RMB', 100)),
    'DAILY_LIMIT_RMB': float(os.getenv('API_DAILY_LIMIT_RMB', 500)),
    'USD_TO_RMB_RATE': float(os.getenv('API_USD_TO_RMB_RATE', 7))
}

# API Settings
API_SETTINGS = {
    'wenxin': {
        'ak': os.getenv('WENXIN_AK', ''),
        'sk': os.getenv('WENXIN_SK', ''),
        'default_model': os.getenv('WENXIN_DEFAULT_MODEL', 'ERNIE-Novel-8K'),
        'default_sub_model': os.getenv('WENXIN_DEFAULT_SUB_MODEL', 'ERNIE-3.5-8K'),
        'max_tokens': 4096,
    },
    'doubao': {
        'api_key': os.getenv('DOUBAO_API_KEY', ''),
        'main_endpoint_id': os.getenv('DOUBAO_MAIN_ENDPOINT_ID', ''),
        'sub_endpoint_id': os.getenv('DOUBAO_SUB_ENDPOINT_ID', ''),
        'default_model': os.getenv('DOUBAO_DEFAULT_MODEL', 'doubao-pro-32k'),
        'default_sub_model': os.getenv('DOUBAO_DEFAULT_SUB_MODEL', 'doubao-lite-32k'),
        'max_tokens': 4096,
    },
    'gpt': {
        'base_url': os.getenv('GPT_BASE_URL', ''),
        'api_key': os.getenv('GPT_API_KEY', ''),
        'proxies': os.getenv('GPT_PROXIES', ''),
        'default_model': os.getenv('GPT_DEFAULT_MODEL', 'gpt-4o'),
        'default_sub_model': os.getenv('GPT_DEFAULT_SUB_MODEL', 'gpt-4o-mini'),
        'max_tokens': 4096,
    },
    'zhipuai': {
        'api_key': os.getenv('ZHIPUAI_API_KEY', ''),
        'default_model': os.getenv('ZHIPUAI_DEFAULT_MODEL', 'glm-4-plus'),
        'default_sub_model': os.getenv('ZHIPUAI_DEFAULT_SUB_MODEL', 'glm-4-flashx'),
        'max_tokens': 4096,
    },
    'others': {
        'base_url': '',
        'api_key': '',
        'default_model': '',
        'default_sub_model': '',
        'max_tokens': 4096,
    }
}