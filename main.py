import os
import asyncio
import logging
from flask import Flask, request, render_template_string, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import threading
import signal
import sys

load_dotenv()

from db import get_conn
from handlers import setup_handlers

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global application instance with thread safety
application = None
application_lock = threading.Lock()
is_shutting_down = False
initialization_event = threading.Event()
app_initialized = False

async def initialize_app():
    """Initialize Telegram application properly"""
    global application
    try:
        logger.info("Initializing Telegram application...")
        
        # Create application with proper initialization
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Setup handlers
        await setup_handlers(application)
        
        # Initialize the application
        await application.initialize()
        
        # Start the application
        await application.start()
        
        # Test Redis connection
        conn = await get_conn()
        await conn.ping()
        logger.info("Redis connection established successfully")
        
        return application
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        application = None
        raise

async def shutdown_application():
    """Shutdown application properly"""
    global application, is_shutting_down, initialization_event, app_initialized
    
    is_shutting_down = True
    if application:
        try:
            logger.info("Shutting down Telegram application...")
            await application.shutdown()
            await application.stop()
            logger.info("Telegram application shut down successfully")
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
        finally:
            application = None
            initialization_event.clear()
            app_initialized = False

def initialize_application_sync():
    """Initialize application synchronously with proper event loop management"""
    global application, initialization_event, app_initialized
    
    with application_lock:
        if application is not None and initialization_event.is_set():
            return application
            
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize application
            application = loop.run_until_complete(initialize_app())
            
            initialization_event.set()
            app_initialized = True
            logger.info("Telegram application initialized and started successfully")
            return application
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {str(e)}")
            application = None
            initialization_event.clear()
            app_initialized = False
            raise

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    
    # Schedule cleanup
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(shutdown_application())
        loop.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# HTML template (keep your existing template)
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

@app.before_request
def check_shutdown():
    """Reject requests during shutdown"""
    if is_shutting_down:
        return "Service is shutting down", 503

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram with proper initialization checks"""
    global application
    
    if is_shutting_down:
        return "Service is shutting down", 503
        
    try:
        # Ensure application is initialized
        if application is None or not initialization_event.is_set():
            logger.info("Application not initialized, initializing now...")
            initialize_application_sync()
            
        if application is None:
            logger.error("Application initialization failed after attempt")
            return "Service temporarily unavailable", 503
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data in webhook request")
            abort(400)
            
        logger.info(f"Received webhook data for update_id: {data.get('update_id', 'unknown')}")
        
        # Process update in a dedicated event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            update = Update.de_json(data, application.bot)
            if update:
                # Process update with timeout
                loop.run_until_complete(
                    asyncio.wait_for(
                        application.process_update(update), 
                        timeout=30.0  # 30 second timeout
                    )
                )
                chat_id = update.effective_chat.id if update.effective_chat else 'unknown'
                logger.info(f"Successfully processed update for chat {chat_id}")
                return '', 200
            else:
                logger.error("Failed to parse Telegram update")
                abort(400)
                
        except asyncio.TimeoutError:
            logger.error("Update processing timed out")
            return 'Timeout', 408
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}", exc_info=True)
            return 'Error', 500
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return 'Error', 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test Redis connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conn = loop.run_until_complete(get_conn())
        loop.run_until_complete(conn.ping())
        loop.close()
        
        return {
            "status": "healthy",
            "service": "Telegram AI Human Handoff Bot",
            "application_initialized": application is not None and initialization_event.is_set(),
            "shutting_down": is_shutting_down
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "application_initialized": application is not None and initialization_event.is_set(),
            "shutting_down": is_shutting_down
        }, 500

def start_scheduler():
    """Start the scheduler in a separate thread"""
    def run_scheduler_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Import here to avoid circular imports
            from utils import run_scheduler as run_scheduler_task
            loop.run_until_complete(run_scheduler_task())
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        finally:
            loop.close()
    
    scheduler_thread = threading.Thread(target=run_scheduler_sync, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler started")

# Initialize application immediately for better reliability
def initialize_on_startup():
    """Initialize application when the app starts"""
    try:
        initialize_application_sync()
        start_scheduler()
        logger.info("Application initialized on startup")
    except Exception as e:
        logger.error(f"Failed to initialize application on startup: {e}")

# Call initialization on module import
initialize_on_startup()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

    