
import logging

import os
import json
from datetime import datetime, timedelta
import asyncio
from upstash_redis.asyncio import Redis
from upstash_redis import UpstashRedisException

# Redis client initialization
redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
redis = Redis(url=redis_url, token=redis_token)

logger = logging.getLogger(__name__)

redis = Redis(
    url=redis_url, 
    token=redis_token,
    retries=3,
    retry_interval=1
)

async def get_conn():
    return redis  # Return the global Redis client

async def get_user_settings(user_id: int) -> dict:
    try:
        data = await redis.hgetall(f"users:{user_id}")
        return data or {}
    except UpstashRedisException as e:
        logger.error(f"Redis error getting user settings for {user_id}: {e}")
        return {}  # Return as is since values are already strings

async def update_user_setting(user_id: int, key_or_dict: str | dict | None, value=None) -> None:
    key = f"users:{user_id}"
    if key_or_dict is None and value is None:
        await redis.delete(key)  # Clear all settings
    elif isinstance(key_or_dict, dict):
        await redis.hset(key, **key_or_dict)
    elif value is not None and key_or_dict is not None:
        await redis.hset(key, key_or_dict, value)
    else:
        # Handle single key deletion if value is None
        await redis.hdel(key, key_or_dict)
    await redis.expire(key, 2592000)  # 30 days

async def get_conversation(user_id: int) -> dict:
    data = await redis.hgetall(f"conversations:{user_id}")
    if not data:
        return {}
    return {
        k: json.loads(v) if k in ['conversation', 'state'] else v
        for k, v in data.items()
    }

async def save_conversation(user_id: int, data: dict) -> None:
    key = f"conversations:{user_id}"
    await redis.hset(key, **{
        'conversation': json.dumps(data.get('conversation', [])),
        'escalated': str(data.get('escalated', '0')),
        'owner_id': str(data.get('owner_id', '')),
        'state': json.dumps(data.get('state', '')),
        'started_at': str(data.get('started_at', datetime.now().timestamp()))
    })
    await redis.expire(key, 86400)  # 24 hours

async def is_busy(user_id: int) -> bool:
    settings = await get_user_settings(user_id)
    return settings.get('busy', '0') == '1'

async def get_user_settings_by_username(username: str) -> dict:
    async for key in redis.scan_iter(match="users:*"):
        settings = await get_user_settings(int(key.decode('utf-8').split(':')[1]))
        if settings.get('username') == username:
            return settings
    return {}

async def clean_old_convs(max_age_hours: int = 24) -> int:
    deleted_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    
    try:
        # Use SCAN command with cursor to get all conversation keys
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="conversations:*", count=100)
            
            for key in keys:
                try:
                    # Get the started_at field from the conversation
                    started_at_str = await redis.hget(key, 'started_at')
                    if started_at_str:
                        started_at = float(started_at_str)
                        if started_at < cutoff_time:
                            await redis.delete(key)
                            deleted_count += 1
                except Exception as e:
                    logger.error(f"Error processing key {key}: {e}")
                    continue
            
            if cursor == 0:
                break
                
    except Exception as e:
        logger.error(f"Error in clean_old_convs: {e}")
    
    return deleted_count