import json
from datetime import datetime, time as dtime
from db import get_conn

def get_user_settings(owner_id: int) -> dict:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (owner_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {}
    return {
        'busy': row[1],
        'auto_reply': row[2],
        'importance_threshold': row[3],
        'keywords': row[4],
        'busy_schedules': row[5],
        'user_name': row[6],
        'user_info': row[7]
    }

def update_user_setting(owner_id: int, field: str, value: any):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, owner_id))
    conn.commit()
    conn.close()

def is_scheduled_busy(settings: dict) -> bool:
    schedules = json.loads(settings['busy_schedules'])
    now = datetime.now()
    day = now.strftime('%A')[:3]
    time_now = now.time()
    for sch in schedules:
        if day in sch['days']:
            start = dtime.fromisoformat(sch['start'])
            end = dtime.fromisoformat(sch['end'])
            if start <= time_now <= end:
                return True
    return False

def is_busy(owner_id: int) -> bool:
    settings = get_user_settings(owner_id)
    return bool(settings.get('busy', 0)) or is_scheduled_busy(settings)

def add_schedule(owner_id: int, days_str: str, start: str, end: str):
    settings = get_user_settings(owner_id)
    if days_str == 'weekdays':
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    elif days_str == 'weekends':
        days = ['Sat', 'Sun']
    else:
        days = [d.capitalize()[:3] for d in days_str.split(',')]
    sch = {'days': days, 'start': start, 'end': end}
    schedules = json.loads(settings['busy_schedules'])
    schedules.append(sch)
    update_user_setting(owner_id, 'busy_schedules', json.dumps(schedules))