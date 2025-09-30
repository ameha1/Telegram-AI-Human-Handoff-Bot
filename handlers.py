# handlers.py
import json
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from db import get_conn
from setting import get_user_settings, is_busy, update_user_setting, add_schedule
from ai import generate_ai_response, analyze_importance, generate_summary, generate_key_points, generate_suggested_action

async def start(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        await update.message.reply_text("Sorry, I'm the personal assistant for my owner. This bot clearly states that the responder is an AI.")
        return
    await update.message.reply_text("Welcome to Autopilot AI - The Intelligent Telegram Assistant. Use commands like /setup, /busy, /available, etc. to configure.")

async def busy(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    update_user_setting(owner_id, 'busy', 1)
    await update.message.reply_text("You are now set as busy.")

async def available(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    update_user_setting(owner_id, 'busy', 0)
    await update.message.reply_text("You are now set as available.")

async def set_auto_reply(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Please provide a message.")
        return
    update_user_setting(owner_id, 'auto_reply', message)
    await update.message.reply_text("Auto-reply message set.")

async def set_threshold(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    if not context.args:
        await update.message.reply_text("Please provide Low, Medium, or High.")
        return
    threshold = context.args[0].capitalize()
    if threshold not in ['Low', 'Medium', 'High']:
        await update.message.reply_text("Invalid: Low, Medium, High")
        return
    update_user_setting(owner_id, 'importance_threshold', threshold)
    await update.message.reply_text(f"Importance threshold set to {threshold}.")

async def set_keywords(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    keywords = ','.join(context.args)
    if not keywords:
        await update.message.reply_text("Please provide comma-separated keywords.")
        return
    update_user_setting(owner_id, 'keywords', keywords)
    await update.message.reply_text("Keywords set.")

async def add_schedule_handler(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add_schedule weekdays 09:00 17:00 or /add_schedule mon,tue,wed 09:00 17:00")
        return
    days_str = context.args[0].lower()
    start = context.args[1]
    end = context.args[2]
    add_schedule(owner_id, days_str, start, end)
    await update.message.reply_text("Busy schedule added.")

async def set_name(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("Please provide a name.")
        return
    update_user_setting(owner_id, 'user_name', name)
    await update.message.reply_text("User name set.")

async def set_user_info(update: Update, context: CallbackContext, owner_id: int) -> None:
    if update.message.from_user.id != owner_id:
        return
    info = ' '.join(context.args)
    if not info:
        await update.message.reply_text("Please provide user info.")
        return
    update_user_setting(owner_id, 'user_info', info)
    await update.message.reply_text("User info set.")

async def handle_message(update: Update, context: CallbackContext, owner_id: int) -> None:
    user_id = update.effective_user.id
    if user_id == owner_id:
        await update.message.reply_text("Hi owner, use commands to manage me.")
        return

    if not is_busy(owner_id):
        await update.message.reply_text("My owner is currently available. Please contact them directly if possible.")
        return

    contact_name = update.effective_user.full_name or f"@{update.effective_user.username}"
    contact_username = update.effective_user.username
    link = f"t.me/{contact_username}" if contact_username else f"Contact ID: {user_id}"

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT conversation, escalated FROM conversations WHERE contact_id = ?", (user_id,))
    conv = cursor.fetchone()

    settings = get_user_settings(owner_id)
    messages = []
    if not conv:
        auto_reply = settings['auto_reply'].replace("[User's Name]", settings['user_name'])
        await update.message.reply_text(auto_reply)
        messages = [{'role': 'user', 'content': update.message.text}]
        cursor.execute(
            "INSERT INTO conversations (contact_id, conversation, started_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(messages), datetime.now().timestamp())
        )
    else:
        messages = json.loads(conv[0])
        messages.append({'role': 'user', 'content': update.message.text})
        cursor.execute("UPDATE conversations SET conversation = ? WHERE contact_id = ?", (json.dumps(messages), user_id))

    conn.commit()

    # Generate AI response
    ai_reply = generate_ai_response(messages, settings)
    await update.message.reply_text(ai_reply)
    messages.append({'role': 'assistant', 'content': ai_reply})
    cursor.execute("UPDATE conversations SET conversation = ? WHERE contact_id = ?", (json.dumps(messages), user_id))
    conn.commit()
    conn.close()

    # Analyze for importance
    num_exchanges = len([m for m in messages if m['role'] == 'user'])
    keywords = [kw.strip().lower() for kw in settings['keywords'].split(',')]
    has_keyword = any(any(kw in msg['content'].lower() for kw in keywords) for msg in messages if msg['role'] == 'user')

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT escalated FROM conversations WHERE contact_id = ?", (user_id,))
    if cursor.fetchone()[0] == 1:
        conn.close()
        return
    conn.close()

    analysis = analyze_importance(messages, settings, num_exchanges)

    if analysis['escalate'] or has_keyword:
        await escalate(context, owner_id, user_id, contact_name, link, messages)

async def escalate(context: CallbackContext, owner_id: int, contact_id: int, contact_name: str, link: str, messages: list) -> None:
    conv_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in messages])
    summary = generate_summary(conv_text)
    key_points = generate_key_points(conv_text)
    suggested = generate_suggested_action(conv_text)

    notification = f"""
🚨 Priority Conversation Alert

From: {contact_name}

Summary: {summary}

Key Points:
{key_points}

Direct Link: {link}

Suggested Action: {suggested}
    """
    await context.bot.send_message(chat_id=owner_id, text=notification)

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET escalated = 1 WHERE contact_id = ?", (contact_id,))
    conn.commit()
    conn.close()