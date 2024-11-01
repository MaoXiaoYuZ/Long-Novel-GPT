from config import ENABLE_MONOGODB
from pymongo import MongoClient
mongo_uri = 'mongodb://localhost:27017/'
mongo_client = MongoClient(mongo_uri) if ENABLE_MONOGODB else None
