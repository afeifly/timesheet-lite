from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import SMTPSettings, User, Role
from app.api.deps import get_current_user
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
from sqlalchemy import func, and_
from app.models import Timesheet

router = APIRouter()

class EmailTestRequest(BaseModel):
    recipient: str

@router.get("/email", response_model=SMTPSettings)
def get_email_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    settings = session.exec(select(SMTPSettings)).first()
    if not settings:
        # Return empty settings if not configured
        return SMTPSettings(
            smtp_server="",
            smtp_port=587,
            smtp_username="",
            smtp_password="",
            sender_email=""
        )
    return settings

@router.put("/email", response_model=SMTPSettings)
def update_email_settings(
    settings: SMTPSettings,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    existing_settings = session.exec(select(SMTPSettings)).first()
    
    if existing_settings:
        existing_settings.smtp_server = settings.smtp_server
        existing_settings.smtp_port = settings.smtp_port
        existing_settings.smtp_username = settings.smtp_username
        existing_settings.smtp_password = settings.smtp_password
        existing_settings.sender_email = settings.sender_email
        session.add(existing_settings)
        session.commit()
        session.refresh(existing_settings)
        return existing_settings
    else:
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings

@router.post("/email/test")
def send_test_email(
    request: EmailTestRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    settings = session.exec(select(SMTPSettings)).first()
    if not settings:
        raise HTTPException(status_code=400, detail="SMTP settings not configured")
        
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.sender_email
        msg['To'] = request.recipient
        msg['Subject'] = "Test Email from Timesheet System"
        
        body = "This is a test email to verify your SMTP settings."
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        text = msg.as_string()
        server.sendmail(settings.sender_email, request.recipient, text)
        server.quit()
        
        return {"message": "Test email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/email/test-no-finish-timesheet")
def check_timesheet_compliance(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    settings = session.exec(select(SMTPSettings)).first()
    if not settings:
        raise HTTPException(status_code=400, detail="SMTP settings not configured")

    # Calculate date range (last 2 full weeks)
    today = date.today()
    start_of_current_week = today - timedelta(days=today.weekday())
    start_date = start_of_current_week - timedelta(days=14)
    end_date = start_of_current_week - timedelta(days=3) # Friday of last week
    
    # Get all non-admin users
    users = session.exec(select(User).where(User.role != Role.ADMIN, User.is_deleted == False)).all()
    
    incomplete_users = []
    
    for user in users:
        if not user.email:
            continue
            
        has_incomplete_day = False
        current_check_date = start_date
        while current_check_date <= end_date:
            # Check only weekdays (Mon-Fri)
            if current_check_date.weekday() < 5:
                # Check total hours for this day
                total_hours = session.exec(
                    select(func.sum(Timesheet.hours))
                    .where(Timesheet.user_id == user.id)
                    .where(Timesheet.date == current_check_date)
                ).one()
                
                if total_hours is None:
                    total_hours = 0
                
                if total_hours < 8:
                    has_incomplete_day = True
                    break
            
            current_check_date += timedelta(days=1)
            
        if has_incomplete_day:
            incomplete_users.append(user.email)
            
    if not incomplete_users:
        return {"message": "All users have completed their timesheets."}
        
    # Send email
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.sender_email
        # We send to the sender (admin) or one of the users? 
        # User said "send a notify email to them (one mail with all employee is ok)"
        # Using BCC to protect privacy if they are just employees, but "one mail with all employee" 
        # might imply they want to see who else is on the list? 
        # Safest is BCC.
        msg['To'] = settings.sender_email # Send to admin/sender
        msg['Bcc'] = ", ".join(incomplete_users)
        msg['Subject'] = "Timesheet Reminder: Incomplete Timesheets"
        
        body = (
            "Dear friend,\n\n"
            "You have not completed your timesheet within the past two weeks. "
            "Please log in to https://timesheet.suto-portal.com to complete your timesheet.\n\n"
            "This is an automated reminder."
        )
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        text = msg.as_string()
        # sendmail takes a list of recipients. We need to include both To and Bcc in the list.
        recipients = [settings.sender_email] + incomplete_users
        server.sendmail(settings.sender_email, recipients, text)
        server.quit()
        
        return {"message": f"Reminder sent to {len(incomplete_users)} employees."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
