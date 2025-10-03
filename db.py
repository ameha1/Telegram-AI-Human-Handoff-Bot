# db.py (updated for Upstash Redis)
import os
import json
from upstash_redis.asyncio import Redis
from datetime import datetime, timedelta

REDIS_URL = os.getenv('UPSTASH_REDIS_REST_URL')
REDIS_TOKEN = os.getenv('UPSTASH_REDIS_REST_TOKEN')
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

async def init_db():
    # No schema needed for Redis; initialize defaults if missing
    pass

async def get_conn():
    return redis

async def clean_old_convs():
    thirty_days_ago = datetime.now().timestamp() - timedelta(days=30).total_seconds()
    async for key in redis.scan_iter(match="conversations:*"):
        conv_data = await redis.hgetall(key)
        if conv_data and float(conv_data.get(b'started_at', 0)) < thirty_days_ago:
            await redis.delete(key)

async def get_user_settings(user_id: int) -> dict:
    settings = await redis.hgetall(f"users:{user_id}")
    if not settings:
        return {
            'busy': 0,
            'auto_reply': "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.",
            'importance_threshold': 'Medium',
            'keywords': 'urgent,emergency,ASAP,critical,deal,contract,money,help',
            'busy_schedules': '[]',
            'user_name': 'Owner',
            'user_info': 'The owner is a professional who works on AI projects.'
        }
    return {k.decode(): v.decode() for k, v in settings.items()}

async def update_user_setting(user_id: int, key: str, value: str):
    await redis.hset(f"users:{user_id}", key, value)

async def get_conversation(contact_id: int) -> dict:
    conv_data = await redis.hgetall(f"conversations:{contact_id}")
    if not conv_data:
        return {'conversation': [], 'escalated': 0, 'owner_id': None, 'state': None}
    return {
        'conversation': json.loads(conv_data[b'conversation'].decode()) if conv_data.get(b'conversation') else [],
        'escalated': int(conv_data.get(b'escalated', 0).decode()),
        'owner_id': int(conv_data.get(b'owner_id', 0).decode()) if conv_data.get(b'owner_id') else None,
        'state': conv_data.get(b'state', b'None').decode()
    }

async def save_conversation(contact_id: int, data: dict):
    await redis.hmset(f"conversations:{contact_id}", {
        'conversation': json.dumps(data['conversation']),
        'escalated': data['escalated'],
        'owner_id': data['owner_id'],
        'state': data['state']
    })