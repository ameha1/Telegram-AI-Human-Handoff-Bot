import sqlite3
import json
from datetime import datetime, timedelta

DB = 'autopilot.db'

def init_db(owner_id: int):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        busy INTEGER DEFAULT 0,
        auto_reply TEXT DEFAULT "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.",
        importance_threshold TEXT DEFAULT 'Medium',
        keywords TEXT DEFAULT 'urgent,emergency,ASAP,critical,deal,contract,money,help',
        busy_schedules TEXT DEFAULT '[]',
        user_name TEXT DEFAULT 'Owner',
        user_info TEXT DEFAULT 'The owner is a professional who works on AI projects.'
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        contact_id INTEGER PRIMARY KEY,
        conversation TEXT,
        started_at REAL,
        escalated INTEGER DEFAULT 0
    )
    ''')

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (owner_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (owner_id,))
    
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB)

def clean_old_convs():
    conn = get_conn()
    cursor = conn.cursor()
    thirty_days_ago = datetime.now().timestamp() - timedelta(days=30).total_seconds()
    cursor.execute("DELETE FROM conversations WHERE started_at < ?", (thirty_days_ago,))
    conn.commit()
    conn.close()