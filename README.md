# Telegram-AI-Human-Handoff-Bot

This is a Telegram bot that handles AI-human handoff for conversations.

Prerequisites:

- Python 3.8+: Ensure Python is installed. Verify with python --version or python3 --version.
- Git: For cloning the repository. Install via git --version to check.
- Telegram Account: To create and manage the bot.
- OpenAI API Key: Required for AI functionality. Sign up at OpenAI Platform.
-Your Telegram User ID: Obtain from @userinfobot with /start.

Step-by-Step Installation

1. Clone the Repository

Open a terminal and run:
  git clone https://github.com/ameha1/Telegram-AI-Human-Handoff-Bot.git
  cd Telegram-AI-Human-Handoff


2. Create a Virtual Environment

Set up a virtual environment to manage dependencies:
  - python -m venv venv
  - venv\Scripts\activate  # Windows
  # or
  - source venv/bin/activate  # macOS/Linux

3. Install Dependencies

Install the required Python packages:
  - pip install -r requirements.txt

4. Configure Environment Variables

Create a .env file in the project root directory with the following content:
  - TELEGRAM_TOKEN=your_telegram_bot_token_here
  - OPENAI_API_KEY=your_openai_api_key_here
  
-TELEGRAM_TOKEN: Obtain this by creating a bot via @BotFather. Send /newbot, follow the prompts, and copy the token.
-OPENAI_API_KEY: Generate from the OpenAI dashboard.

5. Initialize the Database

The bot uses SQLite (autopilot.db) for storage. Running the bot for the first time will create it automatically, but you can manually initialize it by running :
  - python -c "from db import init_db; init_db(int(input('Enter OWNER_ID: ')))"

Enter your OWNER_ID when prompted.

6. Run the Bot

Start the bot with:
  - python main.py


Testing the Bot:

- Open Telegram: Search for your bot’s username (e.g., @YourAutopilotBot) and start a chat.
- Send a Command: As the owner, send /start to see available commands.
- Set Busy Mode: Run /busy to enable AI handling.
- Test with Another Account: From a different Telegram account, message the bot (e.g., "Urgent: Need help!"). The bot should reply and, if urgent, notify the owner.




