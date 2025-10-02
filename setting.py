import json
from datetime import datetime, time as dtime
from db import get_conn

def get_user_settings(user_id: int) -> dict:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {}
    return {
        'busy': row[2],
        'auto_reply': str(row[3]) if row[3] is not None else "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.",
        'importance_threshold': row[4] if row[4] in ['Low', 'Medium', 'High'] else 'Medium',  # Default to 'Medium' if invalid
        'keywords': row[5] if row[5] else 'urgent,emergency,ASAP,critical,deal,contract,money,help',
        'busy_schedules': row[6] if row[6] else '[]',
        'user_name': row[7] if row[7] else 'Owner',
        'user_info': row[8] if row[8] else 'The owner is a professional who works on AI projects.'
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