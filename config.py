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


MAX_NOVEL_SUMMARY_LENGTH = int(os.getenv('MAX_NOVEL_SUMMARY_LENGTH', 20000))

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
        'available_models': os.getenv('WENXIN_AVAILABLE_MODELS', '').split(','),
        'max_tokens': 4096,
    },
    'doubao': {
        'api_key': os.getenv('DOUBAO_API_KEY', ''),
        'endpoint_ids': os.getenv('DOUBAO_ENDPOINT_IDS', '').split(','),
        'available_models': os.getenv('DOUBAO_AVAILABLE_MODELS', '').split(','),
        'max_tokens': 4096,
    },
    'gpt': {
        'base_url': os.getenv('GPT_BASE_URL', ''),
        'api_key': os.getenv('GPT_API_KEY', ''),
        'proxies': os.getenv('GPT_PROXIES', ''),
        'available_models': os.getenv('GPT_AVAILABLE_MODELS', '').split(','),
        'max_tokens': 4096,
    },
    'zhipuai': {
        'api_key': os.getenv('ZHIPUAI_API_KEY', ''),
        'available_models': os.getenv('ZHIPUAI_AVAILABLE_MODELS', '').split(','),
        'max_tokens': 4096,
    },
    'local': {
        'base_url': os.getenv('LOCAL_BASE_URL', ''),
        'api_key': os.getenv('LOCAL_API_KEY', ''),
        'available_models': os.getenv('LOCAL_AVAILABLE_MODELS', '').split(','),
        'max_tokens': 4096,
    }
}

for model in API_SETTINGS.values():
    model['available_models'] = [e.strip() for e in model['available_models']]

DEFAULT_MAIN_MODEL = os.getenv('DEFAULT_MAIN_MODEL', 'wenxin/ERNIE-Novel-8K')
DEFAULT_SUB_MODEL = os.getenv('DEFAULT_SUB_MODEL', 'wenxin/ERNIE-3.5-8K')

ENABLE_ONLINE_DEMO = os.getenv('ENABLE_ONLINE_DEMO', 'false').lower() == 'true'