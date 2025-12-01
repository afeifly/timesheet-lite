from apscheduler.schedulers.background import BackgroundScheduler
from app.database import engine
from sqlmodel import Session
from app.services.email_service import check_timesheet_compliance, check_approval_compliance
import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

def run_timesheet_check():
    with Session(engine) as session:
        print("Running scheduled timesheet compliance check...")
        result = check_timesheet_compliance(session)
        print(f"Timesheet check result: {result}")

def run_approval_check():
    with Session(engine) as session:
        print("Running scheduled approval compliance check...")
        result = check_approval_compliance(session)
        print(f"Approval check result: {result}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # Schedule jobs for Monday at 10:00 AM
    scheduler.add_job(run_timesheet_check, 'cron', day_of_week='mon', hour=10, minute=0)
    scheduler.add_job(run_approval_check, 'cron', day_of_week='mon', hour=10, minute=0)
    
    scheduler.start()
    print("Scheduler started. Jobs scheduled for Monday 10:00 AM.")
