import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from db import get_user_settings, update_user_setting, get_conversation, save_conversation, is_busy, get_user_settings_by_username
from ai import generate_ai_response, analyze_importance, generate_summary, generate_key_points, generate_suggested_action
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or 'unknown'
    logger.info(f"Start command from user {user_id}, username: {username}")
    
    settings = await get_user_settings(user_id)
    if not settings:
        initial_settings = {
            'username': username,
            'auto_reply': "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.",
            'busy': '0',
            'importance_threshold': 'Medium',
            'keywords': '',
            'user_id': str(user_id),
            'user_name': '',
            'user_info': ''
        }
        await update_user_setting(user_id, initial_settings)
        logger.info(f"Created new user {user_id}")
    
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
    user_id = update.effective_user.id
    await update_user_setting(user_id, 'busy', '1')
    await update.message.reply_text("You are now set as busy.")

async def available(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    await update_user_setting(user_id, 'busy', '0')
    await update.message.reply_text("You are now set as available.")

async def set_auto_reply(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please provide a reply message. Usage: /set_auto_reply <message>")
        return
    reply_message = " ".join(context.args)
    await update_user_setting(user_id, 'auto_reply', reply_message)
    await update.message.reply_text(f"Auto-reply set to: {reply_message}")

async def set_threshold(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args or len(context.args) != 1 or context.args[0] not in ['Low', 'Medium', 'High']:
        await update.message.reply_text("Please provide a valid threshold. Usage: /set_threshold <Low/Medium/High>")
        return
    threshold = context.args[0]
    await update_user_setting(user_id, 'importance_threshold', threshold)
    await update.message.reply_text(f"Importance threshold set to: {threshold}")

async def set_keywords(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please provide keywords. Usage: /set_keywords <word1,word2,...>")
        return
    keywords = ",".join(context.args)
    await update_user_setting(user_id, 'keywords', keywords)
    await update.message.reply_text(f"Keywords set to: {keywords}")

async def add_schedule_handler(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args or len(context.args) != 3:
        await update.message.reply_text("Usage: /add_schedule <days> <start> <end> (e.g., Mon-Fri 09:00 17:00)")
        return
    days, start_time, end_time = context.args
    schedule = f"{days} {start_time}-{end_time}"
    await update_user_setting(user_id, 'schedule', schedule)
    await update.message.reply_text(f"Schedule set to: {schedule}")

async def set_name(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /set_name <name>")
        return
    name = context.args[0]
    await update_user_setting(user_id, 'user_name', name)
    await update.message.reply_text(f"Name set to: {name}")

async def set_user_info(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /set_user_info <info>")
        return
    info = " ".join(context.args)
    await update_user_setting(user_id, 'user_info', info)
    await update.message.reply_text(f"User info set to: {info}")

async def deactivate(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("You are not registered as an owner.")
        return
    await update.message.reply_text("Are you sure you want to deactivate? Reply 'YES' to confirm.")
    await update_user_setting(user_id, 'auto_reply', "DEACTIVATE_PENDING")

async def test_as_contact(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text("Testing as contact: Simulating a contact message. Use /busy to enable AI handling.")
    # Simulate a contact message (e.g., log or store for testing)
    logger.info(f"Test as contact initiated by user {user_id}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    logger.info(f"Handling message from user {update.effective_user.id}: {update.message.text}")
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("You are not registered. Use /start to begin.")
        return

    # Initialize conversation data
    conv = await get_conversation(user_id)
    if not conv:
        conv = {
            'conversation': [],
            'escalated': '0',
            'owner_id': str(user_id),
            'state': '',
            'started_at': datetime.now().timestamp()
        }
        await save_conversation(user_id, conv)

    # Set contact_name from the sender
    contact_name = update.effective_user.first_name or update.effective_user.username or 'Unknown Contact'

    # Define a default link (e.g., for escalation or support)
    link = "https://t.me/switchtoAI_bot"

    if settings.get('auto_reply') == "DEACTIVATE_PENDING" and update.message.text.strip().upper() == "YES":
        await update_user_setting(user_id, None)
        await update.message.reply_text("You have been deactivated as an owner. Goodbye!")
        return
    elif settings.get('auto_reply') == "DEACTIVATE_PENDING":
        await update_user_setting(user_id, 'auto_reply', settings.get('auto_reply_backup', "Hi, this is the owner's AI assistant..."))
        await update.message.reply_text("Deactivation cancelled.")
        return

    messages = conv.get('conversation', [])
    escalated = conv.get('escalated', '0')
    owner_id = conv.get('owner_id', str(user_id))
    state = conv.get('state', '')

    if state == 'ASK_OWNER':
        text = update.message.text.strip()
        if text.startswith('@'):
            username = text[1:]
            target_settings = await get_user_settings_by_username(username)
            if target_settings:
                owner_id = target_settings.get('user_id', user_id)
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

    if not await is_busy(int(owner_id)):
        await update.message.reply_text(f"Hi {contact_name}, the owner is currently available. Message sent: {update.message.text}")
        return

    messages.append({'role': 'user', 'content': update.message.text})
    await save_conversation(user_id, {**conv, 'conversation': messages})

    owner_settings = await get_user_settings(int(owner_id))
    ai_reply = generate_ai_response(messages, owner_settings)
    await update.message.reply_text(ai_reply)
    messages.append({'role': 'assistant', 'content': ai_reply})
    await save_conversation(user_id, {**conv, 'conversation': messages})

    if escalated == '1':
        return

    num_exchanges = len([m for m in messages if m['role'] == 'user'])
    keywords = [kw.strip().lower() for kw in owner_settings.get('keywords', '').split(',') if kw.strip()]
    has_keyword = any(any(kw in msg['content'].lower() for kw in keywords) for msg in messages if msg['role'] == 'user')

    analysis = analyze_importance(messages, owner_settings, num_exchanges)
    if analysis.get('escalate', False) or has_keyword:
        await escalate(context, int(owner_id), user_id, contact_name, link, messages)
        await save_conversation(user_id, {**conv, 'escalated': '1'})

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

# Register handlers
def setup_handlers(application: Application) -> None:
    """Register all command and message handlers with the application."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("busy", busy))
    application.add_handler(CommandHandler("available", available))
    application.add_handler(CommandHandler("set_auto_reply", set_auto_reply))
    application.add_handler(CommandHandler("set_threshold", set_threshold))
    application.add_handler(CommandHandler("set_keywords", set_keywords))
    application.add_handler(CommandHandler("add_schedule", add_schedule_handler))
    application.add_handler(CommandHandler("set_name", set_name))
    application.add_handler(CommandHandler("set_user_info", set_user_info))
    application.add_handler(CommandHandler("deactivate", deactivate))
    application.add_handler(CommandHandler("test_as_contact", test_as_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))
    logger.info("Handlers registered successfully")

    