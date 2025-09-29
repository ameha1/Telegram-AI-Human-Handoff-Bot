# Telegram-AI-Human-Handoff-Bot

This is a Telegram bot that handles AI-human handoff for conversations.

## Setup Instructions

1. Create virtual environment: `python -m venv venv`
2. Activate venv: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy .env.example to .env and fill in values
5. Initialize database: `python setup_db.py`
6. Run the bot: `python main.py`
7. For dashboard: `python dashboard/app.py`

For deployment, use Docker: `docker-compose up`
