import threading
import time
import schedule
from db import clean_old_convs

def run_scheduler():
    schedule.every().day.at("00:00").do(clean_old_convs)
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

    