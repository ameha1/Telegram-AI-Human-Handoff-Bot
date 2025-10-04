from upstash_redis.asyncio import Redis
import os
import json
from datetime import datetime, timedelta

# Redis client initialization
redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
redis = Redis(url=redis_url, token=redis_token)

async def get_conn():
    return redis  # Return the global Redis client

async def get_user_settings(user_id: int) -> dict:
    data = await redis.hgetall(f"users:{user_id}")
    if not data:
        return {}
    return {k.decode('utf-8'): v.decode('utf-8') if isinstance(v, bytes) else v for k, v in data.items()}

async def update_user_setting(user_id: int, key_or_dict: str | dict, value=None) -> None:
    key = f"users:{user_id}"
    if isinstance(key_or_dict, dict):
        await redis.hmset(key, key_or_dict)
    else:
        await redis.hset(key, key_or_dict, value)

async def get_conversation(user_id: int) -> dict:
    data = await redis.hgetall(f"conversations:{user_id}")
    if not data:
        return {}
    return {
        k.decode('utf-8'): json.loads(v.decode('utf-8')) if k.decode('utf-8') in ['conversation', 'state'] else v.decode('utf-8')
        for k, v in data.items()
    }

async def save_conversation(user_id: int, data: dict) -> None:
    key = f"conversations:{user_id}"
    await redis.hmset(key, {
        'conversation': json.dumps(data.get('conversation', [])),
        'escalated': str(data.get('escalated', 0)),
        'owner_id': str(data.get('owner_id', '')),
        'state': json.dumps(data.get('state', '')),
        'started_at': str(data.get('started_at', datetime.now().timestamp()))
    })

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
    """
    Remove conversations older than max_age_hours.
    Returns the number of deleted conversations.
    """
    deleted_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    async for key in redis.scan_iter(match="conversations:*"):
        conv_data = await get_conversation(int(key.decode('utf-8').split(':')[1]))
        started_at = float(conv_data.get('started_at', 0))
        if started_at < cutoff_time:
            await redis.delete(key.decode('utf-8'))
            deleted_count += 1
    return deleted_count