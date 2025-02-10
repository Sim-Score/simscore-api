from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.credits import CreditService

scheduler = AsyncIOScheduler()

def init_schedulers():
    scheduler.add_job(
        CreditService.refresh_daily_credits,
        trigger=CronTrigger(hour=0, minute=0),  # Run at midnight
        id='refresh_credits',
        name='Refresh daily credits',
        replace_existing=True
    )
    scheduler.start()
