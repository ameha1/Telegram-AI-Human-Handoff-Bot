import os
import logging
import asyncio
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import threading
from db import init_db
from handlers import (
    start, busy, available, set_auto_reply, set_threshold, set_keywords,
    add_schedule_handler, set_name, set_user_info, handle_message, deactivate, test_as_contact
)
from utils import run_scheduler

load_dotenv()

from db import init_db
from handlers import (
    start, busy, available, set_auto_reply, set_threshold, set_keywords,
    add_schedule_handler, set_name, set_user_info, handle_message, deactivate, test_as_contact
)
from utils import run_scheduler

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

init_db()
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()
logging.basicConfig(level=logging.INFO)

def main() -> None:
    threading.Thread(target=run_scheduler, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
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

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))

    # For groups (optional)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Entity("mention"), handle_message))

    application.run_polling()

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json()
        if not json_data:
            logging.error("No JSON data in request")
            abort(400)
        update = Update.de_json(json_data, application.bot)
        if update:
            # Handle async in sync context for serverless
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.process_update(update))
            loop.close()
            logging.info(f"Processed update for chat {update.effective_chat.id}")
            return '', 200
        else:
            logging.error("Failed to parse update")
            abort(400)
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}", exc_info=True)  # Full traceback
        abort(500)

@app.route('/')
def index():
    return "Bot is running!"

if __name__ == '__main__':
    # For local testing: app.run(debug=True)
    # Start scheduler in thread
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(debug=True)