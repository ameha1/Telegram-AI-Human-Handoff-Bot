
# Telegram AI Human Handoff Bot

A Telegram bot that enhances productivity by managing messages with an AI-powered assistant, escalating urgent requests, and facilitating human handoffs when needed. Built with Python, Flask, and integrated with OpenAI and Upstash Redis.

## Overview

This bot allows users to:
- Set availability statuses (`/busy`, `/available`).
- Configure AI responses and escalation thresholds.
- Manage schedules and user information.
- Receive priority alerts for important messages.

The project uses a webhook-based architecture deployed on Render, with Gunicorn and gevent for async handling.

## Prerequisites

- Python 3.9+
- A Telegram bot token from [BotFather](https://t.me/BotFather).
- An Upstash Redis instance (URL and token).
- An OpenAI API key.
- A Render account for deployment.

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/ameha1/telegram-ai-human-handoff-bot.git
cd telegram-ai-human-handoff-bot
```

### 2. Install Dependencies
Install the required packages using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory with the following variables:
```
TELEGRAM_TOKEN=your_telegram_bot_token
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_redis_token
OPENAI_API_KEY=your_openai_api_key
PORT=10000  # Optional for local testing, Render overrides this
```
- Replace placeholders with your actual credentials.

### 4. Local Testing
Run the application locally:
```bash
gunicorn main:app --config gunicorn.conf.py --bind 0.0.0.0:10000
```
- Access the bot at `http://localhost:10000` (webhook setup required for full functionality).
- Send `/start` to `@your-bot-username` in Telegram to test.

## Deployment on Render

### 1. Push to GitHub
Ensure your code is committed and pushed to a GitHub repository:
```bash
git add .
git commit -m "Initial commit for Render deployment"
git push origin main
```

### 2. Create a Render Service
- Log in to [Render](https://render.com/).
- Click "New" > "Web Service".
- Connect your GitHub repository.
- Configure the service:
  - **Name**: e.g., `telegram-ai-human-handoff-bot`
  - **Branch**: `main`
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn main:app --config gunicorn.conf.py --bind 0.0.0.0:$PORT`
  - **Instance Type**: Free (or upgrade for more resources)
  - **Runtime**: Python 3
- Add the environment variables from your `.env` file in the Render dashboard under "Environment".
- Deploy the service.

### 3. Set Webhook
After deployment, set the Telegram webhook using the Render URL:
```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://<your-render-url>.onrender.com/webhook"
```
- Replace `<TELEGRAM_TOKEN>` with your bot token and `<your-render-url>` with your Render service URL (e.g., `telegram-ai-human-handoff-bot.onrender.com`).

### 4. Verify Deployment
- Send `/start` to your bot in Telegram.
- Check Render logs for successful startup (e.g., `[INFO] Starting gunicorn 23.0.0`).

## Usage

### Commands
- `/start`: Displays a welcome message and command list.
- `/busy`: Sets the user as busy, enabling AI handling.
- `/available`: Sets the user as available, disabling AI handling.
- `/set_auto_reply <message>`: Sets a custom auto-reply (e.g., `/set_auto_reply Hi, I'm busy`).
- `/set_threshold <Low/Medium/High>`: Sets escalation sensitivity.
- `/set_keywords <word1,word2,...>`: Sets urgent keywords (e.g., `/set_keywords urgent,help`).
- `/add_schedule <days> <start> <end>`: Sets busy times (e.g., `/add_schedule weekdays 09:00 17:00`).
- `/set_name <name>`: Sets the user's name.
- `/set_user_info <info>`: Sets user info for FAQs.
- `/deactivate YES`: Removes the user account.
- `/test_as_contact`: Tests contact mode (placeholder).

### Example Workflow
1. Send `/start` to register.
2. Send `/busy` to enable AI.
3. Send a message (e.g., "urgent help needed") to trigger AI response and escalation if configured.

## Configuration

- **gunicorn.conf.py**: Configures Gunicorn with 1 gevent worker, 120s timeout, and binding to `0.0.0.0:10000` (overridden by `$PORT` on Render).
- **main.py**: Defines the Flask app and Telegram `Application`.
- **db.py**: Manages user settings and conversations in Upstash Redis.
- **ai.py**: Handles AI responses and analysis using OpenAI.
- **handlers.py**: Implements bot commands and message handling.

## Troubleshooting

- **Bot Not Responding**:
  - Check Render logs for errors (e.g., missing environment variables).
  - Verify the webhook is set correctly.
- **Runtime Errors**:
  - Look for `KeyError`, `RuntimeError`, or `NameError` in logs and review the updated code.
  - Ensure all dependencies are installed.
- **Redis Issues**:
  - Confirm `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are valid.
- **Contact Support**: Share logs with the project maintainers or check GitHub issues.

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit changes: `git commit -m "Add feature"`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.

## License

[MIT License](LICENSE) - Feel free to modify and distribute.

## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [OpenAI](https://platform.openai.com/)
- [Upstash Redis](https://upstash.com/)
- [Render](https://render.com/)

---

### Deployment Steps (Recap)
1. **Update README**:
   - Replace the existing `README.md` with the content above.
2. **Commit and Push**:
   ```bash:disable-run
   git add README.md
   git commit -m "Add comprehensive README.md for project guidance"
   git push origin main
   ```
3. **Redeploy on Render**:
   - Trigger redeploy via the Render dashboard to reflect the updated documentation.
4. **Test**:
   - Verify the project setup works as described by sending `/start` to the bot.
