import os
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv
import threading
import signal
import sys
import concurrent.futures
import logging
from logging.handlers import RotatingFileHandler

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

# Global application instance
application = None
application_lock = threading.Lock()
is_shutting_down = False

async def initialize_app():
    """Initialize Telegram application properly"""
    global application
    try:
        logger.info("Initializing Telegram application...")
        
        # Create application
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

def initialize_application_sync():
    """Initialize application synchronously"""
    global application
    
    with application_lock:
        if application is not None:
            return application
            
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            application = loop.run_until_complete(initialize_app())
            logger.info("Telegram application initialized and started successfully")
            return application
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {str(e)}")
            application = None
            raise

async def shutdown_application():
    """Shutdown application properly"""
    global application, is_shutting_down
    
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

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    
    # Schedule cleanup
    try:
        if application:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(shutdown_application())
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    try:
        with application_lock:
            if application is None:
                initialize_application_sync()
            
            data = request.get_json()
            update = Update.de_json(data, application.bot)
            
            if update:
                # Use thread-safe processing
                loop = application._loop
                asyncio.run_coroutine_threadsafe(
                    application.process_update(update),
                    loop
                )
                return '', 200
                
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return 'Error', 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test Redis connection
        def test_redis():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                conn = loop.run_until_complete(get_conn())
                loop.run_until_complete(conn.ping())
                return True
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                return False
            finally:
                loop.close()
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(test_redis)
            redis_healthy = future.result(timeout=10.0)
        
        return jsonify({
            "status": "healthy" if redis_healthy else "unhealthy",
            "service": "Telegram AI Human Handoff Bot",
            "application_initialized": application is not None,
            "shutting_down": is_shutting_down,
            "redis_connected": redis_healthy
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "application_initialized": application is not None,
            "shutting_down": is_shutting_down
        }), 500

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('bot.log', maxBytes=10485760, backupCount=3),
            logging.StreamHandler()
        ]
    )

def start_scheduler():
    """Start the scheduler in a separate thread"""
    def run_scheduler_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from utils import run_scheduler as run_scheduler_task
            loop.run_until_complete(run_scheduler_task())
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        finally:
            loop.close()
    
    scheduler_thread = threading.Thread(target=run_scheduler_sync, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler started")

# Initialize application on startup
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
