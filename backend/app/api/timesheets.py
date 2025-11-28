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
    
    # Auto-verify for Team Leader's own work
    if current_user.role == Role.TEAM_LEADER and timesheet.user_id == current_user.id:
        timesheet.verify = True
    elif current_user.role == Role.EMPLOYEE:
        timesheet.verify = False
    
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
        
        # Check verification status
        if existing.verify:
            # Team Leader can modify verified work, but Employee cannot
            if current_user.role == Role.EMPLOYEE:
                raise HTTPException(status_code=403, detail="Cannot modify verified timesheet")
            # If TL modifies, does it stay verified? Requirement: "Teamleader can modify any log work. teamleader's log work will always be verified."
            # It doesn't explicitly say TL modification of EMPLOYEE work re-verifies it, but usually yes.
            # However, if TL is modifying to FIX it, maybe they want to verify it too.
            # Let's assume TL modification keeps it verified or sets it to verified if they are the ones doing it.
            # For now, let's keep the existing verify status unless explicitly changed, OR if TL is editing own work (handled above).
            # Actually, if TL edits employee work, it's likely "approved" by them.
            # But let's stick to: If it was verified, it stays verified. If it wasn't, it stays unverified unless verified via endpoint?
            # Wait, "teamleader's log work will always be verified" applies to THEIR work.
            # "teamleader can modify any log work" -> Permission.
            # "wait teamleader to verify" -> Action.
            # So editing doesn't necessarily mean verifying.
            pass

        existing.hours = timesheet.hours
        # If TL is editing own work, ensure verify is True
        if current_user.role == Role.TEAM_LEADER and timesheet.user_id == current_user.id:
            existing.verify = True
             
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

