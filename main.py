# main.py (updated)
import os
import threading
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

from db import init_db
from handlers import (
    start, busy, available, set_auto_reply, set_threshold, set_keywords,
    add_schedule_handler, set_name, set_user_info, handle_message, deactivate
)
from utils import run_scheduler

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

init_db()

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

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))

    # For groups (optional)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Entity("mention"), handle_message))

    application.run_polling()

if __name__ == '__main__':

    print("Bot is starting...")

    main()