# main.py
import os
import threading
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from db import init_db
from handlers import (
    start, busy, available, set_auto_reply, set_threshold, set_keywords,
    add_schedule_handler, set_name, set_user_info, handle_message
)
from utils import run_scheduler

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))  # Set this to the Telegram user ID of the owner

init_db(OWNER_ID)

def main() -> None:
    threading.Thread(target=run_scheduler, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", lambda u, c: start(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("busy", lambda u, c: busy(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("available", lambda u, c: available(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("set_auto_reply", lambda u, c: set_auto_reply(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("set_threshold", lambda u, c: set_threshold(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("set_keywords", lambda u, c: set_keywords(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("add_schedule", lambda u, c: add_schedule_handler(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("set_name", lambda u, c: set_name(u, c, OWNER_ID)))
    application.add_handler(CommandHandler("set_user_info", lambda u, c: set_user_info(u, c, OWNER_ID)))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, lambda u, c: handle_message(u, c, OWNER_ID)))

    # For groups (configurable, but enabled here)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Entity("mention"), lambda u, c: handle_message(u, c, OWNER_ID)))

    application.run_polling()

if __name__ == '__main__':
    main()