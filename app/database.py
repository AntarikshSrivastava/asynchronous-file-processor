import time
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from .logger import logger
from .env import db_user, db_port

# MongoDB Settings
MONGO_URI = f"mongodb://{db_user}:{db_port}"
DB_NAME = "jobs_db"

# Synchronous MongoDB client for Celery tasks
mongo_client = MongoClient(MONGO_URI, maxPoolSize=50)
db = mongo_client[DB_NAME]

# Asynchronous MongoDB client for FastAPI
async_mongo_client = AsyncIOMotorClient(MONGO_URI, maxPoolSize=50)
async_db = async_mongo_client[DB_NAME]


def retry_with_backoff_mongo(mongo_operation, *args, **kwargs):
    base_delay = 0.1  # seconds
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return mongo_operation(*args, **kwargs)
        except PyMongoError as e:
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
            else:
                logger.error(f"MongoDB operation failed after {max_retries} attempts: {e}")
                raise e  # Re-raise the exception to be caught by the outer exception handler
