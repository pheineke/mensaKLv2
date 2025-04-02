from apscheduler.schedulers.background import BackgroundScheduler
from parser import scrape_meals
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # Schedule scraping every 12 hours
    scheduler.add_job(scrape_meals, 'interval', hours=12)
    
    # Run immediately on startup
    scrape_meals()
    
    scheduler.start()
    logger.info("Scheduler started - scraping every 12 hours")
    return scheduler 