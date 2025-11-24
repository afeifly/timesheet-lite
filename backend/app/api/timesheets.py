from typing import List, Optional
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Timesheet, User, ActivityLog, Role, Project
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Timesheet])
def read_timesheets(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    query = select(Timesheet)
    
    # If employee, can only see own. If admin, can see specified user_id or all.
    if current_user.role == Role.EMPLOYEE:
        query = query.where(Timesheet.user_id == current_user.id)
    elif user_id:
        query = query.where(Timesheet.user_id == user_id)
        
    if start_date:
        query = query.where(Timesheet.date >= start_date)
    if end_date:
        query = query.where(Timesheet.date <= end_date)
        
    return session.exec(query).all()

@router.post("/", response_model=Timesheet)
def create_timesheet(
    timesheet: Timesheet,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Validate user permissions
    if current_user.role == Role.EMPLOYEE and timesheet.user_id != current_user.id:
         raise HTTPException(status_code=403, detail="Cannot log time for others")
    
    # 1. Check Weekly Limit (40 hours)
    # Calculate start of week (Monday)
    if isinstance(timesheet.date, str):
        timesheet.date = datetime.strptime(timesheet.date, "%Y-%m-%d").date()
        
    start_of_week = timesheet.date - timedelta(days=timesheet.date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    weekly_hours = session.exec(
        select(func.sum(Timesheet.hours))
        .where(Timesheet.user_id == timesheet.user_id)
        .where(Timesheet.date >= start_of_week)
        .where(Timesheet.date <= end_of_week)
        # Exclude current timesheet if it's an update (but this is create, so no ID yet)
    ).one() or 0
    
    if weekly_hours + timesheet.hours > 40:
        raise HTTPException(status_code=400, detail=f"Weekly limit exceeded. Current: {weekly_hours}, Requested: {timesheet.hours}")

    # 2. Check Daily Warning (Frontend handles warning, backend just accepts, but maybe we should return a warning flag? 
    # The requirement says 'Show warning', usually implies frontend. Backend enforces hard rules.)
    
    # 3. Pre-planning check
    # "Edit past weeks only if admin permissions allow" -> Now "past two weeks can be modify again"
    today = date.today()
    start_of_current_week = today - timedelta(days=today.weekday())
    # Allow editing for current week AND previous 2 weeks.
    # So cutoff is start_of_current_week - 14 days.
    cutoff_date = start_of_current_week - timedelta(weeks=2)
    
    if timesheet.date < cutoff_date and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Cannot modify timesheets older than 2 weeks")

    # Check if entry exists for this project/date/user -> Update instead of Create?
    # Usually timesheets are unique per user/project/date or just a list of entries.
    # Let's assume unique per user/project/date for simplicity, or allow multiple entries?
    # "Allocate 8 hours per day across assigned projects" -> implies summing up.
    # Let's check if an entry exists and update it, or just add new one. 
    # Simplest is: One entry per project per day.
    
    existing = session.exec(
        select(Timesheet)
        .where(Timesheet.user_id == timesheet.user_id)
        .where(Timesheet.project_id == timesheet.project_id)
        .where(Timesheet.date == timesheet.date)
    ).first()
    
    # Fetch project name for logging
    project = session.get(Project, timesheet.project_id)
    project_name = project.name if project else "Unknown"

    if existing:
        # Update existing
        # We need to subtract the old value from weekly check and add new value
        # But we already did the check with `weekly_hours` which INCLUDES the old value if it's in DB.
        # So: (weekly_hours - existing.hours + new.hours) > 40
        if (weekly_hours - existing.hours + timesheet.hours) > 40:
             raise HTTPException(status_code=400, detail="Weekly limit exceeded")
             
        existing.hours = timesheet.hours
        existing.updated_at = datetime.utcnow() # Need datetime import
        session.add(existing)
        session.commit()
        session.refresh(existing)
        
        log = ActivityLog(user_id=current_user.id, action="UPDATE_TIMESHEET", details=f"Updated {timesheet.hours}h for project '{project_name}' (ID: {timesheet.project_id}) on {timesheet.date}")
        session.add(log)
        session.commit()
        return existing
    else:
        session.add(timesheet)
        session.commit()
        session.refresh(timesheet)
        
        log = ActivityLog(user_id=current_user.id, action="CREATE_TIMESHEET", details=f"Logged {timesheet.hours}h for project '{project_name}' (ID: {timesheet.project_id}) on {timesheet.date}")
        session.add(log)
        session.commit()
        return timesheet

# Need to import datetime for updated_at
from datetime import datetime
