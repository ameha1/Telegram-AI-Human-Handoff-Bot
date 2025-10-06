from db import clean_old_convs
import asyncio
import logging

logger = logging.getLogger(__name__)

async def run_scheduler():
    """
    Run a scheduler to clean old conversations periodically with better error handling.
    """
    while True:
        try:
            deleted_count = await clean_old_convs(max_age_hours=24)
            if deleted_count > 0:
                logger.info(f"Cleaned {deleted_count} old conversations")
            else:
                logger.debug("No old conversations to clean")
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}", exc_info=True)
        
        # Wait for 24 hours with periodic wake-ups to check for shutdown
        for _ in range(24 * 12):  # Check every 5 minutes for 24 hours
            await asyncio.sleep(300)  # 5 minutes