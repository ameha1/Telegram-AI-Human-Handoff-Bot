import json
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from db import get_conn
from setting import get_user_settings, is_busy, update_user_setting, add_schedule
from ai import generate_ai_response, analyze_importance, generate_summary, generate_key_points, generate_suggested_action

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.effective_user.username
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, auto_reply) VALUES (?, ?, ?)", 
                       (user_id, username, "Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries."))
        conn.commit()
    conn.close()
    await update.message.reply_text("""
Welcome to Autopilot AI, your intelligent Telegram assistant! I'm here to manage your messages when you're busy. Below are the available commands:

- /start: Displays this help message.
- /busy: Set yourself as busy to enable AI message handling.
- /available: Set yourself as available to disable AI handling.
- /set_auto_reply <message>: Set a custom reply for new chats (e.g., /set_auto_reply Hi, I'm busy, my AI will assist!).
- /set_threshold <Low/Medium/High>: Set sensitivity for important messages (e.g., /set_threshold Medium).
- /set_keywords <word1,word2,...>: Set urgent keywords (e.g., /set_keywords urgent,emergency,ASAP).
- /add_schedule <days> <start> <end>: Set busy times (e.g., /add_schedule weekdays 09:00 17:00 or /add_schedule mon,tue 08:00 12:00).
- /set_name <name>: Set your name (e.g., /set_name Alice).
- /set_user_info <info>: Set info about you for FAQs (e.g., /set_user_info Software engineer working on AI projects).
- /deactivate: Remove yourself as an owner and deactivate the bot for you.
- /test_as_contact: Test the bot as a contact by specifying your own @username.

When busy, I'll handle messages, escalate important ones, and summarize them for you! Your username (@{username}) is registered for contacts to reach you.
    """.format(username=username or 'unknown'))

async def busy(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    update_user_setting(user_id, 'busy', 1)
    await update.message.reply_text("You are now set as busy.")

async def available(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    update_user_setting(user_id, 'busy', 0)
    await update.message.reply_text("You are now set as available.")

async def set_auto_reply(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Please provide a message.")
        return
    update_user_setting(user_id, 'auto_reply', message)
    await update.message.reply_text("Auto-reply message set.")

async def set_threshold(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("Please provide Low, Medium, or High.")
        return
    threshold = context.args[0].capitalize()
    if threshold not in ['Low', 'Medium', 'High']:
        await update.message.reply_text("Invalid: Low, Medium, High")
        return
    update_user_setting(user_id, 'importance_threshold', threshold)
    await update.message.reply_text(f"Importance threshold set to {threshold}.")

async def set_keywords(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    keywords = ','.join(context.args)
    if not keywords:
        await update.message.reply_text("Please provide comma-separated keywords.")
        return
    update_user_setting(user_id, 'keywords', keywords)
    await update.message.reply_text("Keywords set.")

async def add_schedule_handler(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add_schedule weekdays 09:00 17:00 or /add_schedule mon,tue,wed 09:00 17:00")
        return
    days_str = context.args[0].lower()
    start = context.args[1]
    end = context.args[2]
    add_schedule(user_id, days_str, start, end)
    await update.message.reply_text("Busy schedule added.")

async def set_name(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("Please provide a name.")
        return
    update_user_setting(user_id, 'user_name', name)
    await update.message.reply_text("User name set.")

async def set_user_info(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    info = ' '.join(context.args)
    if not info:
        await update.message.reply_text("Please provide user info.")
        return
    update_user_setting(user_id, 'user_info', info)
    await update.message.reply_text("User info set.")

async def deactivate(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    print(f"Received /deactivate from user_id: {user_id}")  # Debug
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        print(f"User {user_id} not found in users table")  # Debug
        await update.message.reply_text("You are not registered as an owner.")
        conn.close()
        return
    print(f"User {user_id} found, prompting for confirmation")  # Debug
    await update.message.reply_text("Are you sure you want to deactivate the bot for yourself? This will remove you as an owner. Reply with 'YES' to confirm.")
    cursor.execute("UPDATE users SET auto_reply = ? WHERE user_id = ?", ("DEACTIVATE_PENDING", user_id))
    conn.commit()
    conn.close()

async def test_as_contact(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        await update.message.reply_text("You are not registered as an owner.")
        conn.close()
        return
    username = row[0]
    await update.message.reply_text(f"Testing as contact. Please reply with @{username} to simulate contacting yourself.")
    conn.close()

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        settings = {
            'busy': user[2],
            'auto_reply': user[3],
            'importance_threshold': user[4],
            'keywords': user[5],
            'busy_schedules': user[6],
            'user_name': user[7],
            'user_info': user[8]
        }
        if settings['auto_reply'] == "DEACTIVATE_PENDING" and update.message.text.strip().upper() == "YES":
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            await update.message.reply_text("You have been deactivated as an owner. Goodbye!")
            conn.close()
            return
        elif settings['auto_reply'] == "DEACTIVATE_PENDING":
            await update.message.reply_text("Deactivation cancelled. Please use /deactivate again if needed.")
            cursor.execute("UPDATE users SET auto_reply = ? WHERE user_id = ?", ("Hi, this is the owner's AI assistant. They are currently focusing on deep work and may be slow to respond. I'm here to help with initial queries.", user_id))
            conn.commit()
            conn.close()
            return
        await update.message.reply_text("Hi, use commands to manage me.")
        conn.close()
        return
    # Contact (including owner testing as contact)
    contact_name = update.effective_user.full_name or f"@{update.effective_user.username}"
    contact_username = update.effective_user.username
    link = f"t.me/{contact_username}" if contact_username else f"Contact ID: {user_id}"

    cursor.execute("SELECT conversation, escalated, owner_id, state FROM conversations WHERE contact_id = ?", (user_id,))
    conv = cursor.fetchone()

    messages = [] if not conv else json.loads(conv[0])
    escalated = 0 if not conv else conv[1]
    owner_id = None if not conv else conv[2]
    state = None if not conv else conv[3]

    if not conv:
        await update.message.reply_text("Hi, who are you trying to reach? Reply with @username of the person.")
        state = 'ASK_OWNER'
        cursor.execute(
            "INSERT INTO conversations (contact_id, conversation, started_at, state) VALUES (?, ?, ?, ?)",
            (user_id, json.dumps(messages), datetime.now().timestamp(), state)
        )
        conn.commit()
        conn.close()
        return

    if state == 'ASK_OWNER':
        text = update.message.text.strip()
        if text.startswith('@'):
            username = text[1:]
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                owner_id = row[0]
                cursor.execute("UPDATE conversations SET owner_id = ?, state = NULL WHERE contact_id = ?", (owner_id, user_id))
                conn.commit()
                settings = get_user_settings(owner_id)
                print(f"Debug: Settings for owner {owner_id}: {settings}")  # Debug output
                auto_reply = settings.get('auto_reply', "Hi, this is the owner's AI assistant...")
                if not isinstance(auto_reply, str):
                    auto_reply = str(auto_reply)
                auto_reply = auto_reply.replace("[User's Name]", settings.get('user_name', 'Owner'))
                await update.message.reply_text(auto_reply)
                conn.close()
                return
            else:
                await update.message.reply_text("Sorry, username not found. Try again with @username.")
                conn.close()
                return
        else:
            await update.message.reply_text("Please reply with @username.")
            conn.close()
            return

    # Normal contact message
    if not owner_id:
        await update.message.reply_text("Error: No owner associated. Please start over.")
        conn.close()
        return

    if not is_busy(owner_id):
        await update.message.reply_text("My owner is currently available. Please contact them directly if possible.")
        conn.close()
        return

    messages.append({'role': 'user', 'content': update.message.text})
    cursor.execute("UPDATE conversations SET conversation = ? WHERE contact_id = ?", (json.dumps(messages), user_id))
    conn.commit()

    settings = get_user_settings(owner_id)  # Ensure fresh settings
    ai_reply = generate_ai_response(messages, settings)
    await update.message.reply_text(ai_reply)
    messages.append({'role': 'assistant', 'content': ai_reply})
    cursor.execute("UPDATE conversations SET conversation = ? WHERE contact_id = ?", (json.dumps(messages), user_id))
    conn.commit()

    # Analyze
    if escalated == 1:
        conn.close()
        return

    num_exchanges = len([m for m in messages if m['role'] == 'user'])
    keywords = [kw.strip().lower() for kw in settings['keywords'].split(',')]
    has_keyword = any(any(kw in msg['content'].lower() for kw in keywords) for msg in messages if msg['role'] == 'user')

    analysis = analyze_importance(messages, settings, num_exchanges)

    if analysis['escalate'] or has_keyword:
        await escalate(context, owner_id, user_id, contact_name, link, messages)
        cursor.execute("UPDATE conversations SET escalated = 1 WHERE contact_id = ?", (user_id,))
        conn.commit()

    conn.close()

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