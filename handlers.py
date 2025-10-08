import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext  # Added CallbackContext
from db import get_user_settings, update_user_setting, get_conversation, save_conversation, is_busy, get_user_settings_by_username
from ai import generate_ai_response, analyze_importance, generate_summary, generate_key_points, generate_suggested_action
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    try:
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
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await update.message.reply_text("Sorry, there was an error processing your request. Please try again.")

async def busy(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        await update_user_setting(user_id, 'busy', '1')
        await update.message.reply_text("You are now set as busy.")
    except Exception as e:
        logger.error(f"Error in busy command: {e}", exc_info=True)
        await update.message.reply_text("Failed to update your status. Please try again.")

async def available(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        await update_user_setting(user_id, 'busy', '0')
        await update.message.reply_text("You are now set as available.")
    except Exception as e:
        logger.error(f"Error in available command: {e}", exc_info=True)
        await update.message.reply_text("Failed to update your status. Please try again.")

async def set_auto_reply(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Please provide a reply message, e.g., /set_auto_reply Hi, I'm busy.")
            return
        user_id = update.effective_user.id
        reply = ' '.join(context.args)
        await update_user_setting(user_id, 'auto_reply', reply)
        await update.message.reply_text(f"Auto reply set to: {reply}")
    except Exception as e:
        logger.error(f"Error in set_auto_reply command: {e}", exc_info=True)
        await update.message.reply_text("Failed to set auto reply. Please try again.")

async def set_threshold(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args or context.args[0].lower() not in ['low', 'medium', 'high']:
            await update.message.reply_text("Please specify 'Low', 'Medium', or 'High', e.g., /set_threshold Medium")
            return
        user_id = update.effective_user.id
        threshold = context.args[0].capitalize()
        await update_user_setting(user_id, 'importance_threshold', threshold)
        await update.message.reply_text(f"Importance threshold set to: {threshold}")
    except Exception as e:
        logger.error(f"Error in set_threshold command: {e}", exc_info=True)
        await update.message.reply_text("Failed to set threshold. Please try again.")

async def set_keywords(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Please provide keywords separated by commas, e.g., /set_keywords urgent,help")
            return
        user_id = update.effective_user.id
        keywords = ','.join(context.args)
        await update_user_setting(user_id, 'keywords', keywords)
        await update.message.reply_text(f"Keywords set to: {keywords}")
    except Exception as e:
        logger.error(f"Error in set_keywords command: {e}", exc_info=True)
        await update.message.reply_text("Failed to set keywords. Please try again.")

async def add_schedule_handler(update: Update, context: CallbackContext) -> None:
    try:
        if len(context.args) != 3:
            await update.message.reply_text("Usage: /add_schedule <days> <start_time> <end_time>, e.g., /add_schedule weekdays 09:00 17:00")
            return
        days, start, end = context.args
        user_id = update.effective_user.id
        # Placeholder for schedule logic - to be implemented with db.py
        await update.message.reply_text(f"Schedule set: {days} from {start} to {end} (implementation pending)")
    except Exception as e:
        logger.error(f"Error in add_schedule command: {e}", exc_info=True)
        await update.message.reply_text("Failed to set schedule. Please try again.")

async def set_name(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Please provide a name, e.g., /set_name John Doe")
            return
        user_id = update.effective_user.id
        name = ' '.join(context.args)
        await update_user_setting(user_id, 'user_name', name)
        await update.message.reply_text(f"Name set to: {name}")
    except Exception as e:
        logger.error(f"Error in set_name command: {e}", exc_info=True)
        await update.message.reply_text("Failed to set name. Please try again.")

async def set_user_info(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Please provide info, e.g., /set_user_info I am an AI developer")
            return
        user_id = update.effective_user.id
        info = ' '.join(context.args)
        await update_user_setting(user_id, 'user_info', info)
        await update.message.reply_text(f"User info set to: {info}")
    except Exception as e:
        logger.error(f"Error in set_user_info command: {e}", exc_info=True)
        await update.message.reply_text("Failed to set user info. Please try again.")

async def deactivate(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        if context.args and context.args[0].lower() == 'yes':
            await update_user_setting(user_id, None, None)  # Clear all settings
            await update.message.reply_text("Your account has been deactivated.")
        else:
            await update.message.reply_text("To deactivate, please type /deactivate YES")
    except Exception as e:
        logger.error(f"Error in deactivate command: {e}", exc_info=True)
        await update.message.reply_text("Failed to deactivate. Please try again.")

async def test_as_contact(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        await update.message.reply_text("Testing as contact mode (placeholder).")
    except Exception as e:
        logger.error(f"Error in test_as_contact command: {e}", exc_info=True)
        await update.message.reply_text("Failed to test as contact. Please try again.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        contact_name = update.effective_user.first_name or update.effective_user.username or 'Unknown'
        link = f"tg://user?id={user_id}"
        conv = await get_conversation(user_id)
        messages = conv.get('conversation', [])
        escalated = conv.get('escalated', '0')
        owner_id = conv.get('owner_id', user_id)

        if not await is_busy(owner_id):
            logger.info(f"Owner {owner_id} is currently available. Message sent: {update.message.text}")
            return

        messages.append({'role': 'user', 'content': update.message.text})
        await save_conversation(user_id, {**conv, 'conversation': messages})

        owner_settings = await get_user_settings(int(owner_id))
        owner_settings.setdefault('user_name', 'Owner')
        owner_settings.setdefault('user_info', 'The owner is a professional who works on AI projects.')
        
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
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I encountered an error processing your message.")

async def escalate(context: CallbackContext, owner_id: int, contact_id: int, contact_name: str, link: str, messages: list) -> None:
    try:
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
    except Exception as e:
        logger.error(f"Error in escalate: {e}", exc_info=True)

# Register handlers
async def setup_handlers(application: Application) -> None:
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