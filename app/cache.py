import time
import random
from redis import Redis, RedisError, ConnectionPool
from .env import redis_host, redis_port

# Customize the connection pool
pool = ConnectionPool(host=redis_host, port=redis_port, db=0, decode_responses=True, max_connections=10)

# Use the custom connection pool
redis_client = Redis(connection_pool=pool)


def retry_with_backoff(redis_operation, *args, **kwargs):
    max_retries = kwargs.pop('max_retries', 0)
    base_delay = kwargs.pop('base_delay', 0.1)
    for attempt in range(max_retries):
        try:
            return redis_operation(*args, **kwargs)
        except RedisError:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
            time.sleep(delay)
    return None  # Indicates a fallback is needed