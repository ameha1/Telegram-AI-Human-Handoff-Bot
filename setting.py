# This file is deprecated. Use db.py for all database operations with Upstash Redis.
# Remove or refactor to align with Redis-based implementation if needed.

import json
from datetime import datetime, time as dtime
from db import get_conn  # Placeholder to avoid breaking imports

def get_user_settings(user_id: int) -> dict:
    return {}  # Deprecated, use db.py instead

def update_user_setting(owner_id: int, field: str, value: any):
    pass  # Deprecated

def is_scheduled_busy(settings: dict) -> bool:
    return False  # Deprecated

def is_busy(owner_id: int) -> bool:
    return False  # Deprecated

def add_schedule(owner_id: int, days_str: str, start: str, end: str):
    pass  # Deprecated