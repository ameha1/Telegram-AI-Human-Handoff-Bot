import os
import asyncio
import logging
from flask import Flask, request, render_template_string, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import gevent.monkey
import threading

# Apply gevent monkey patching at the start
gevent.monkey.patch_all()

load_dotenv()

from db import get_conn
from handlers import (
    start, busy, available, set_auto_reply, set_threshold, set_keywords,
    add_schedule_handler, set_name, set_user_info, handle_message, deactivate, test_as_contact
)
from utils import run_scheduler

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Global application instance and loop
application = None
loop = None

async def initialize_app():
    global application, loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    conn = await get_conn()
    try:
        await conn.ping()
        logging.info("Redis connection established successfully")
    except Exception as e:
        logging.error(f"Failed to connect to Redis: {str(e)}")
    await application.initialize()
    return application

async def setup_handlers(application):
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
    logging.info("Handlers registered successfully")

async def initialize():
    global application
    application = await initialize_app()
    await setup_handlers(application)
    application.add_error_handler(error_handler)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Exception while handling an update: {context.error}")

# Lazy initialization of Telegram Application on first request
def lazy_init():
    global application
    if application is None:
        asyncio.run(initialize())
    return application

# HTML template for the elegant landing page
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram AI Human Handoff Bot</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f4f7fa;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: #333;
        }
        .container {
            text-align: center;
            background: white;
            padding: 2rem 3rem;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            max-width: 500px;
        }
        h1 {
            color: #2c3e50;
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        p {
            font-size: 1.1rem;
            line-height: 1.5;
            margin-bottom: 2rem;
        }
        a.button {
            display: inline-block;
            padding: 0.8rem 1.5rem;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        a.button:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Telegram AI Human Handoff Bot</h1>
        <p>Enhance your productivity with an AI-powered assistant that manages Telegram messages, escalates urgent requests, and enables seamless human handoffs. Try it now!</p>
        <a href="https://t.me/switchtoAI_bot" class="button" target="_blank">Start Chatting</a>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE)

@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    if application is None:
        application = lazy_init()
    if application is None:
        logging.error("Application initialization failed")
        abort(500)
    try:
        data = request.get_json()
        logging.info(f"Received webhook data: {data}")
        if not data:
            logging.error("No JSON data in webhook request")
            abort(400)
        update = Update.de_json(data, application.bot)
        if update:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.process_update(update))
            logging.info(f"Processed update for chat {update.effective_chat.id if update.effective_chat else 'unknown'}")
            return '', 200
        else:
            logging.error("Failed to parse Telegram update")
            abort(400)
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}", exc_info=True)
        abort(500)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=port)
    