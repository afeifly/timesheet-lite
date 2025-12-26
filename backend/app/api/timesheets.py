from typing import List, Optional
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Timesheet, User, ActivityLog, Role, Project, WorkDay, WorkDayType
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
    else:
        # Default to current user's timesheets if no user_id specified (even for Admin/TL)
        # Unless we want a specific "get all" endpoint, but usually /timesheets/ is for the current context.
        # If Admin wants to see all, they should probably use a specific filter or we assume they want their own.
        # Given the bug report "login as TL, see employee work", this is the fix.
        query = query.where(Timesheet.user_id == current_user.id)
        
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
    if current_user.role == Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admins cannot log work")

    if current_user.role == Role.EMPLOYEE and timesheet.user_id != current_user.id:
         raise HTTPException(status_code=403, detail="Cannot log time for others")
    
    # Auto-verify logic: Employee always False. TL/Admin can set it (default from input).
    if current_user.role == Role.EMPLOYEE:
        timesheet.verify = False
    
    # 1. Check if entry exists for this project/date/user -> Update instead of Create?
    # We need to check this FIRST before calculating weekly limits
    # Calculate start of week (Monday)
    if isinstance(timesheet.date, str):
        timesheet.date = datetime.strptime(timesheet.date, "%Y-%m-%d").date()
        
    existing_entries = session.exec(
        select(Timesheet)
        .where(Timesheet.user_id == timesheet.user_id)
        .where(Timesheet.project_id == timesheet.project_id)
        .where(Timesheet.date == timesheet.date)
    ).all()
    
    # 2. Check Weekly Limit (40 hours)
    start_of_week = timesheet.date - timedelta(days=timesheet.date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    weekly_hours = session.exec(
        select(func.sum(Timesheet.hours))
        .where(Timesheet.user_id == timesheet.user_id)
        .where(Timesheet.date >= start_of_week)
        .where(Timesheet.date <= end_of_week)
    ).one() or 0

    # Check for OFF day
    current_workday = session.get(WorkDay, timesheet.date)
    if current_workday and current_workday.day_type == WorkDayType.OFF:
        raise HTTPException(status_code=400, detail="Cannot log work on an off day")
    
    # Calculate Dynamic Weekly Limit
    limit = 40.0
    week_exceptions = session.exec(
        select(WorkDay)
        .where(WorkDay.date >= start_of_week)
        .where(WorkDay.date <= end_of_week)
    ).all()

    for exception in week_exceptions:
        # Only reduce limit if the off day is a weekday (Mon-Fri)
        if exception.date.weekday() < 5:
            if exception.day_type == WorkDayType.OFF:
                limit -= 8.0
            elif exception.day_type == WorkDayType.HALF_OFF:
                limit -= 4.0
            
    # If updating existing entry, subtract its current hours from weekly total
    # If updating existing entry(ies), subtract ALL their current hours from weekly total
    if existing_entries:
        for entry in existing_entries:
            weekly_hours -= entry.hours
    
    if weekly_hours + timesheet.hours > limit:
        raise HTTPException(status_code=400, detail=f"Weekly limit exceeded. Limit: {limit}h, Current: {weekly_hours}h, Requested: {timesheet.hours}h")

    # 3. Pre-planning check
    # "Edit past weeks only if admin permissions allow" -> Now "past two weeks can be modify again"
    today = date.today()
    start_of_current_week = today - timedelta(days=today.weekday())
    # Allow editing for current week AND previous 2 weeks.
    # So cutoff is start_of_current_week - 14 days.
    cutoff_date = start_of_current_week - timedelta(weeks=2)
    
    if timesheet.date < cutoff_date and current_user.role not in [Role.ADMIN, Role.TEAM_LEADER]:
        raise HTTPException(status_code=403, detail="Cannot modify timesheets older than 2 weeks")
    
    # Fetch project name for logging
    project = session.get(Project, timesheet.project_id)
    project_name = project.name if project else "Unknown"

    if existing_entries:
        # Update existing
        # Weekly limit already checked above
        
        # Consolidate: Use the first one, delete others
        target_entry = existing_entries[0]
        duplicates = existing_entries[1:]
        
        for dup in duplicates:
             session.delete(dup)
        
        # Check verification status
        if target_entry.verify:
            # Team Leader can modify verified work, but Employee cannot
            if current_user.role == Role.EMPLOYEE:
                raise HTTPException(status_code=403, detail="Cannot modify verified timesheet")
            
        target_entry.hours = timesheet.hours
        # Update verify status if provided (and allowed)
        if current_user.role in [Role.TEAM_LEADER, Role.ADMIN]:
             target_entry.verify = timesheet.verify
             
        target_entry.updated_at = datetime.utcnow() # Need datetime import
        session.add(target_entry)
        session.commit()
        session.refresh(target_entry)
        
        log = ActivityLog(user_id=current_user.id, action="UPDATE_TIMESHEET", details=f"Updated {timesheet.hours}h for project '{project_name}' (ID: {timesheet.project_id}) on {timesheet.date}")
        session.add(log)
        session.commit()
        return target_entry
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

from pydantic import BaseModel

class VerifyRequest(BaseModel):
    user_id: int
    date: date

@router.post("/verify")
def verify_day(
    request: VerifyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEAM_LEADER:
        raise HTTPException(status_code=403, detail="Only Team Leaders can verify")
    
    # Check if user is assigned to this TL
    target_user = session.get(User, request.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if target_user.team_leader_id != current_user.id:
        raise HTTPException(status_code=403, detail="User is not assigned to you")
        
    # Calculate total hours for that day
    if isinstance(request.date, str):
        request.date = datetime.strptime(request.date, "%Y-%m-%d").date()
        
    daily_hours = session.exec(
        select(func.sum(Timesheet.hours))
        .where(Timesheet.user_id == request.user_id)
        .where(Timesheet.date == request.date)
    ).one() or 0
    
    if daily_hours > 8:
        raise HTTPException(status_code=400, detail=f"Cannot verify > 8 hours (Current: {daily_hours}h)")
        
    # Update all entries to verify=True
    timesheets = session.exec(
        select(Timesheet)
        .where(Timesheet.user_id == request.user_id)
        .where(Timesheet.date == request.date)
    ).all()
    
    for t in timesheets:
        t.verify = True
        session.add(t)
        
    session.commit()
    return {"message": "Verified successfully"}

