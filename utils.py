from db import clean_old_convs
import asyncio
import logging

async def run_scheduler():
    """
    Run a scheduler to clean old conversations periodically (e.g., every 24 hours).
    """
    while True:
        try:
            deleted_count = await clean_old_convs(max_age_hours=24)
            logging.info(f"Cleaned {deleted_count} old conversations")
        except Exception as e:
            logging.error(f"Error in scheduler: {str(e)}")
        await asyncio.sleep(24 * 3600)  # Run every 24 hours