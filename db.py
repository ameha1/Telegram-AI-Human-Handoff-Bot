import os
from upstash_redis.asyncio import Redis

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

redis = Redis(
    url=REDIS_URL,
    token=REDIS_TOKEN
)

async def get_conn():
    return redis

async def update_user_setting(user_id, settings):
    key = f"user:{user_id}"
    # Unpack the settings dictionary into key-value pairs
    await redis.hset(key, mapping=settings)

async def get_user_setting(user_id, field=None):
    key = f"user:{user_id}"
    if field:
        return await redis.hget(key, field)
    return await redis.hgetall(key)

async def delete_user_setting(user_id):
    key = f"user:{user_id}"
    await redis.delete(key)