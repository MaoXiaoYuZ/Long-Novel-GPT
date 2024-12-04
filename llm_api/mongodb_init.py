import os
from config import ENABLE_MONOGODB
from pymongo import MongoClient

# 从环境变量获取 MongoDB URI，如果没有则使用默认值
mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
mongo_client = MongoClient(mongo_uri) if ENABLE_MONOGODB else None
