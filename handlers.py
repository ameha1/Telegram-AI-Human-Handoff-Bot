import json
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from db import get_user_settings, update_user_setting, get_conversation, save_conversation, is_busy, get_user_settings_by_username
from ai import generate_ai_response, analyze_importance, generate_summary, generate_key_points, generate_suggested_action
import logging

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.effective_user.username or 'unknown'
    logging.info(f"Start command from user {user_id}, username: {username}")
    
    settings = await get_user_settings(user_id)
    if not settings:  # User not found, create new
        initial_settings = {
            'username': username,
            'auto_reply': "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.",
            'busy': '0',
            'importance_threshold': 'Medium',
            'keywords': '',
            'user_name': '',
            'user_info': ''
        }
        await update_user_setting(user_id, initial_settings)
        logging.info(f"Created new user {user_id}")
    
    await update.message.reply_text(f"""
Welcome to Autopilot AI, your intelligent Telegram assistant! I'm here to manage your messages when you're busy. Below are the available commands:

- /start: Displays this help message.
- /busy: Set yourself as busy to enable AI message handling.
- /available: Set yourself as available to disable AI handling.
- /set_auto_reply <message>: Set a custom reply for new chats.
- /set_threshold <Low/Medium/High>: Set sensitivity for important messages.
- /set_keywords <word1,word2,...>: Set urgent keywords.
- /add_schedule <days> <start> <end>: Set busy times.
- /set_name <name>: Set your name.
- /set_user_info <info>: Set info about you for FAQs.
- /deactivate: Remove yourself as an owner.
- /test_as_contact: Test as a contact.

Your username (@{username}) is registered for contacts to reach you.
    """)

async def busy(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    await update_user_setting(user_id, 'busy', '1')
    await update.message.reply_text("You are now set as busy.")

async def available(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    await update_user_setting(user_id, 'busy', '0')
    await update.message.reply_text("You are now set as available.")

async def set_auto_reply(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Please provide a message.")
        return
    await update_user_setting(user_id, 'auto_reply', message)
    await update.message.reply_text("Auto-reply message set.")

async def set_threshold(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("Please provide Low, Medium, or High.")
        return
    threshold = context.args[0].capitalize()
    if threshold not in ['Low', 'Medium', 'High']:
        await update.message.reply_text("Invalid: Low, Medium, or High")
        return
    await update_user_setting(user_id, 'importance_threshold', threshold)
    await update.message.reply_text(f"Importance threshold set to {threshold}.")

async def set_keywords(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    keywords = ','.join(context.args)
    if not keywords:
        await update.message.reply_text("Please provide comma-separated keywords.")
        return
    await update_user_setting(user_id, 'keywords', keywords)
    await update.message.reply_text("Keywords set.")

async def add_schedule_handler(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add_schedule weekdays 09:00 17:00 or /add_schedule mon,tue 08:00 12:00")
        return
    days_str = context.args[0].lower()
    start = context.args[1]
    end = context.args[2]
    schedule_key = f"schedule:{user_id}"
    await update_user_setting(user_id, 'schedule', json.dumps({'days': days_str, 'start': start, 'end': end}))
    await update.message.reply_text("Busy schedule added.")

async def set_name(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("Please provide a name.")
        return
    await update_user_setting(user_id, 'user_name', name)
    await update.message.reply_text("User name set.")

async def set_user_info(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    info = ' '.join(context.args)
    if not info:
        await update.message.reply_text("Please provide user info.")
        return
    await update_user_setting(user_id, 'user_info', info)
    await update.message.reply_text("User info set.")

async def deactivate(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    settings = await get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("You are not registered as an owner.")
        return
    await update.message.reply_text("Are you sure you want to deactivate? Reply 'YES' to confirm.")
    await update_user_setting(user_id, 'auto_reply', "DEACTIVATE_PENDING")

async def test_as_contact(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    settings = await get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("You are not registered as an owner.")
        return
    username = settings.get('username', update.effective_user.username or 'unknown')
    await update.message.reply_text(f"Testing as contact. Reply with @{username} to simulate.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    logging.info(f"Handling message from user {update.effective_user.id}: {update.message.text}")
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    if settings:
        if settings.get('auto_reply') == "DEACTIVATE_PENDING" and update.message.text.strip().upper() == "YES":
            await update_user_setting(user_id, None)  # Clear all settings
            await update.message.reply_text("You have been deactivated as an owner. Goodbye!")
            return
        elif settings.get('auto_reply') == "DEACTIVATE_PENDING":
            await update_user_setting(user_id, 'auto_reply', settings.get('auto_reply_backup', "Hi, this is the owner's AI assistant..."))
            await update.message.reply_text("Deactivation cancelled.")
            return
        await update.message.reply_text("Hi, use commands to manage me.")
        return
    
    contact_name = update.effective_user.full_name or f"@{update.effective_user.username or 'unknown'}"
    link = f"t.me/{update.effective_user.username}" if update.effective_user.username else f"Contact ID: {user_id}"
    conv = await get_conversation(user_id)
    if not conv:
        await update.message.reply_text("Hi, who are you trying to reach? Reply with @username of the person.")
        await save_conversation(user_id, {'conversation': [], 'escalated': 0, 'owner_id': None, 'state': 'ASK_OWNER', 'started_at': datetime.now().timestamp()})
        return
    
    messages = conv['conversation']
    escalated = conv['escalated']
    owner_id = conv['owner_id']
    state = conv['state']
    
    if state == 'ASK_OWNER':
        text = update.message.text.strip()
        if text.startswith('@'):
            username = text[1:]
            target_settings = await get_user_settings_by_username(username)
            if target_settings:
                owner_id = int(target_settings['user_id'])  # Assume user_id is stored
                await save_conversation(user_id, {**conv, 'owner_id': owner_id, 'state': None})
                auto_reply = target_settings.get('auto_reply', "Hi, this is the owner's AI assistant...")
                await update.message.reply_text(auto_reply)
                return
            else:
                await update.message.reply_text("Username not found. Try again.")
                return
        else:
            await update.message.reply_text("Please reply with @username.")
            return
    
    if not owner_id:
        await update.message.reply_text("Error: No owner associated. Please start over.")
        return
    
    if not await is_busy(owner_id):
        await update.message.reply_text("My owner is currently available. Please contact them directly.")
        return
    
    messages.append({'role': 'user', 'content': update.message.text})
    await save_conversation(user_id, {**conv, 'conversation': messages})
    
    settings = await get_user_settings(owner_id)
    ai_reply = generate_ai_response(messages, settings)
    await update.message.reply_text(ai_reply)
    messages.append({'role': 'assistant', 'content': ai_reply})
    await save_conversation(user_id, {**conv, 'conversation': messages})
    
    if escalated == 1:
        return
    
    num_exchanges = len([m for m in messages if m['role'] == 'user'])
    keywords = [kw.strip().lower() for kw in settings.get('keywords', '').split(',')]
    has_keyword = any(any(kw in msg['content'].lower() for kw in keywords) for msg in messages if msg['role'] == 'user')
    
    analysis = analyze_importance(messages, settings, num_exchanges)
    if analysis['escalate'] or has_keyword:
        await escalate(context, owner_id, user_id, contact_name, link, messages)
        await save_conversation(user_id, {**conv, 'escalated': 1})

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