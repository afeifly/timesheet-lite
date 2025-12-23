from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import WorkDay, WorkDayType, Role, User
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[WorkDay])
def read_workdays(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    query = select(WorkDay)
    if start_date:
        query = query.where(WorkDay.date >= start_date)
    if end_date:
        query = query.where(WorkDay.date <= end_date)
    return session.exec(query).all()

@router.post("/", response_model=WorkDay)
def update_workday(
    workday: WorkDay,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admins can manage work days")
    
    existing = session.get(WorkDay, workday.date)
    if existing:
        existing.day_type = workday.day_type
        existing.remark = workday.remark
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        session.add(workday)
        session.commit()
        session.refresh(workday)
        return workday
