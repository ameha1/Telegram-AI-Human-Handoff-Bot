import os
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import asyncio
import logging
import threading

load_dotenv()

from db import init_db, get_conn
from handlers import (
    start, busy, available, set_auto_reply, set_threshold, set_keywords,
    add_schedule_handler, set_name, set_user_info, handle_message, deactivate, test_as_contact
)
from utils import run_scheduler

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Set as Render env var

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)  # Flask app instance named 'app'
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
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))

async def initialize_app():
    await init_db()
    logging.info("Database initialized successfully")

def run_init():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_app())
    loop.close()

run_init()

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logging.info(f"Received webhook request: {request.get_json()}")
        json_data = request.get_json()
        if not json_data:
            logging.error("No JSON data in request")
            abort(400)
        update = Update.de_json(json_data, application.bot)
        if update:
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
        logging.error(f"Webhook error: {str(e)}", exc_info=True)
        abort(500)

@app.route('/')
def index():
    return "Bot is running!"

if __name__ == '__main__':
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(debug=True)