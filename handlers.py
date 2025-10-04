import json
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from db import get_conn, get_conversation, save_conversation
from setting import get_user_settings, is_busy, update_user_setting, add_schedule
from ai import generate_ai_response, analyze_importance, generate_summary, generate_key_points, generate_suggested_action
import logging

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.effective_user.username
    conn = await get_conn()
    try:
        result = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not result.fetchone():
            await conn.execute("INSERT INTO users (user_id, username, auto_reply) VALUES (?, ?, ?)", 
                               (user_id, username, "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries."))
            await conn.commit()
        await update.message.reply_text("""
Welcome to Autopilot AI, your intelligent Telegram assistant! I'm here to manage your messages when you're busy. Below are the available commands:

- /start: Displays this help message.
- /busy: Set yourself as busy to enable AI message handling.
- /available: Set yourself as available to disable AI handling.
- /set_auto_reply <message>: Set a custom reply for new chats (e.g., /set_auto_reply Hi, I'm busy, my AI will assist!).
- /set_threshold <Low/Medium/High>: Set sensitivity for important messages (e.g., /set_threshold Medium).
- /set_keywords <word1,word2,...>: Set urgent keywords (e.g., /set_keywords urgent,emergency,ASAP).
- /add_schedule <days> <start> <end>: Set busy times (e.g., /add_schedule weekdays 09:00 17:00 or /add_schedule mon,tue 08:00 12:00).
- /set_name <name>: Set your name (e.g., /set_name Alice).
- /set_user_info <info>: Set info about you for FAQs (e.g., /set_user_info Software engineer working on AI projects).
- /deactivate: Remove yourself as an owner and deactivate the bot for you.
- /test_as_contact: Test the bot as a contact by specifying your own @username.

When busy, I'll handle messages, escalate important ones, and summarize them for you! Your username (@{username}) is registered for contacts to reach you.
        """.format(username=username or 'unknown'))
    finally:
        # libSQL doesn't need explicit close; it's pooled
        pass

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
        await update.message.reply_text("Invalid: Low, Medium, High")
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
        await update.message.reply_text("Usage: /add_schedule weekdays 09:00 17:00 or /add_schedule mon,tue,wed 09:00 17:00")
        return
    days_str = context.args[0].lower()
    start = context.args[1]
    end = context.args[2]
    await add_schedule(user_id, days_str, start, end)
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
    logging.info(f"Received /deactivate from user_id: {user_id}")
    settings = await get_user_settings(user_id)
    if not settings:
        logging.info(f"User {user_id} not found in users table")
        await update.message.reply_text("You are not registered as an owner.")
        return
    logging.info(f"User {user_id} found, prompting for confirmation")
    await update.message.reply_text("Are you sure you want to deactivate the bot for yourself? This will remove you as an owner. Reply with 'YES' to confirm.")
    await update_user_setting(user_id, 'auto_reply', "DEACTIVATE_PENDING")

async def test_as_contact(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    settings = await get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("You are not registered as an owner.")
        return
    username = settings.get('username', update.effective_user.username)
    await update.message.reply_text(f"Testing as contact. Please reply with @{username} to simulate contacting yourself.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    logging.info(f"Handling message from user {update.effective_user.id}: {update.message.text}")
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    if settings:
        logging.info(f"User {user_id} is an owner")
        if settings['auto_reply'] == "DEACTIVATE_PENDING" and update.message.text.strip().upper() == "YES":
            conn = await get_conn()
            await conn.delete(f"users:{user_id}")
            await update.message.reply_text("You have been deactivated as an owner. Goodbye!")
            return
        elif settings['auto_reply'] == "DEACTIVATE_PENDING":
            await update.message.reply_text("Deactivation cancelled. Please use /deactivate again if needed.")
            await update_user_setting(user_id, 'auto_reply', "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.")
            return
        await update.message.reply_text("Hi, use commands to manage me.")
        return
    # Contact (including owner testing as contact)
    contact_name = update.effective_user.full_name or f"@{update.effective_user.username}"
    contact_username = update.effective_user.username
    link = f"t.me/{contact_username}" if contact_username else f"Contact ID: {user_id}"

    conv = await get_conversation(user_id)
    messages = conv['conversation']
    escalated = conv['escalated']
    owner_id = conv['owner_id']
    state = conv['state']

    if not conv:
        await update.message.reply_text("Hi, who are you trying to reach? Reply with @username of the person.")
        state = 'ASK_OWNER'
        await save_conversation(user_id, {'conversation': [], 'escalated': 0, 'owner_id': None, 'state': state, 'started_at': datetime.now().timestamp()})
        return

    if state == 'ASK_OWNER':
        text = update.message.text.strip()
        if text.startswith('@'):
            username = text[1:]
            result = await conn.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            row = result.fetchone()
            if row:
                owner_id = row[0]
                await save_conversation(user_id, {'conversation': messages, 'escalated': escalated, 'owner_id': owner_id, 'state': None, 'started_at': conv.get('started_at', datetime.now().timestamp())})
                settings = await get_user_settings(owner_id)
                logging.info(f"Debug: Settings for owner {owner_id}: {settings}")
                auto_reply = settings.get('auto_reply', "Hi, this is the owner's AI assistant...")
                if not isinstance(auto_reply, str):
                    auto_reply = str(auto_reply)
                auto_reply = auto_reply.replace("[User's Name]", settings.get('user_name', 'Owner'))
                await update.message.reply_text(auto_reply)
                return
            else:
                await update.message.reply_text("Sorry, username not found. Try again with @username.")
                return
        else:
            await update.message.reply_text("Please reply with @username.")
            return

    # Normal contact message
    if not owner_id:
        await update.message.reply_text("Error: No owner associated. Please start over.")
        return

    if not await is_busy(owner_id):
        await update.message.reply_text("My owner is currently available. Please contact them directly if possible.")
        return

    messages.append({'role': 'user', 'content': update.message.text})
    await save_conversation(user_id, {'conversation': messages, 'escalated': escalated, 'owner_id': owner_id, 'state': state, 'started_at': conv.get('started_at', datetime.now().timestamp())})

    settings = await get_user_settings(owner_id)
    ai_reply = generate_ai_response(messages, settings)
    await update.message.reply_text(ai_reply)
    messages.append({'role': 'assistant', 'content': ai_reply})
    await save_conversation(user_id, {'conversation': messages, 'escalated': escalated, 'owner_id': owner_id, 'state': state, 'started_at': conv.get('started_at', datetime.now().timestamp())})

    # Analyze
    if escalated == 1:
        return

    num_exchanges = len([m for m in messages if m['role'] == 'user'])
    keywords = [kw.strip().lower() for kw in settings['keywords'].split(',')]
    has_keyword = any(any(kw in msg['content'].lower() for kw in keywords) for msg in messages if msg['role'] == 'user')

    analysis = analyze_importance(messages, settings, num_exchanges)

    if analysis['escalate'] or has_keyword:
        await escalate(context, owner_id, user_id, contact_name, link, messages)
        await save_conversation(user_id, {'conversation': messages, 'escalated': 1, 'owner_id': owner_id, 'state': state, 'started_at': conv.get('started_at', datetime.now().timestamp())})

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