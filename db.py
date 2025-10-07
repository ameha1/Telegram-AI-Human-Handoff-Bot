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
    # Fix: Use consistent key pattern - either "users:{user_id}" or "user:{user_id}"
    data = await redis.hgetall(f"user:{user_id}")
    if not data:
        # Try the other pattern for backward compatibility
        data = await redis.hgetall(f"users:{user_id}")
    return data

async def update_user_setting(user_id: int, key_or_dict: str | dict, value=None) -> None:
    # Fix: Use consistent key pattern
    key = f"user:{user_id}"
    
    if isinstance(key_or_dict, dict):
        # Handle dictionary input
        for k, v in key_or_dict.items():
            await redis.hset(key, k, str(v))
    elif value is not None:
        # Handle key-value pair
        await redis.hset(key, key_or_dict, str(value))
    else:
        # Handle deletion
        await redis.hdel(key, key_or_dict)
    
    # Set expiration to prevent memory leaks
    await redis.expire(key, 30 * 24 * 3600)  # 30 days

async def get_conversation(user_id: int) -> dict:
    data = await redis.hgetall(f"conversations:{user_id}")
    if not data:
        return {}
    
    result = {}
    for k, v in data.items():
        if k in ['conversation', 'state']:
            try:
                result[k] = json.loads(v)
            except json.JSONDecodeError:
                result[k] = v
        else:
            result[k] = v
    
    return result

async def save_conversation(user_id: int, data: dict) -> None:
    key = f"conversations:{user_id}"
    
    # Prepare data for storage
    storage_data = {}
    for k, v in data.items():
        if k in ['conversation', 'state']:
            storage_data[k] = json.dumps(v)
        else:
            storage_data[k] = str(v)
    
    # Store all fields
    if storage_data:
        await redis.hset(key, mapping=storage_data)
    
    # Set expiration (24 hours for conversations)
    await redis.expire(key, 24 * 3600)

async def is_busy(user_id: int) -> bool:
    settings = await get_user_settings(user_id)
    return settings.get('busy', '0') == '1'

async def get_user_settings_by_username(username: str) -> dict:
    # Scan for user keys with both patterns using KEYS command (for Upstash Redis)
    patterns = ["user:*", "users:*"]
    
    for pattern in patterns:
        keys = await redis.keys(pattern)
        for key in keys:
            try:
                user_id_str = key.split(':')[1]
                settings = await get_user_settings(int(user_id_str))
                if settings.get('username') == username:
                    return settings
            except (IndexError, ValueError, Exception) as e:
                continue
    return {}

async def clean_old_convs(max_age_hours: int = 24) -> int:
    """
    Remove conversations older than max_age_hours.
    Returns the number of deleted conversations.
    """
    deleted_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    
    # Use KEYS instead of SCAN for Upstash Redis
    keys = await redis.keys("conversations:*")
    
    for key in keys:
        try:
            # Extract user_id from key
            user_id_str = key.split(':')[1]
            conv_data = await get_conversation(int(user_id_str))
            started_at = float(conv_data.get('started_at', 0))
            if started_at < cutoff_time:
                await redis.delete(key)
                deleted_count += 1
        except (ValueError, KeyError, Exception) as e:
            # Delete corrupted conversations
            await redis.delete(key)
            deleted_count += 1
    
    return deleted_count