from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.database import get_session
from app.models import User, Role, Project, UserProjectLink, ActivityLog
from app.api.deps import get_current_admin_user, get_current_user
from app.core.security import get_password_hash
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=16)

@router.get("/", response_model=list[User])
def read_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    users = session.exec(select(User).where(User.is_deleted == False)).all()
    return users

@router.post("/", response_model=User)
def create_user(
    user: User,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Parse date strings if needed
    if isinstance(user.start_date, str):
        user.start_date = datetime.strptime(user.start_date, "%Y-%m-%d").date()
    if isinstance(user.end_date, str):
        user.end_date = datetime.strptime(user.end_date, "%Y-%m-%d").date()
    
    user.password_hash = get_password_hash(user.password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Log activity
    log = ActivityLog(user_id=current_user.id, action="CREATE_USER", details=f"Created user {user.username}")
    session.add(log)
    session.commit()
    
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user.is_deleted = True
    session.add(user)
    session.commit()
    
    # Log activity
    log = ActivityLog(user_id=current_user.id, action="DELETE_USER", details=f"Soft deleted user {user.username}")
    session.add(log)
    session.commit()
    
    return {"ok": True}

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_update: User,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_data = user_update.dict(exclude_unset=True, exclude={'id', 'password_hash'})
    
    # Handle date conversion for updates
    for date_field in ['start_date', 'end_date']:
        if date_field in user_data and isinstance(user_data[date_field], str):
            user_data[date_field] = datetime.strptime(user_data[date_field], "%Y-%m-%d").date()

    for key, value in user_data.items():
        setattr(db_user, key, value)
        
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    log = ActivityLog(user_id=current_user.id, action="UPDATE_USER", details=f"Updated user {db_user.username}")
    session.add(log)
    session.commit()
    
    return db_user

@router.put("/me/password")
def change_password(
    password_data: PasswordChange,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.core.security import verify_password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()
    return {"ok": True}

@router.post("/{user_id}/projects/{project_id}")
def assign_project(
    user_id: int,
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    user = session.get(User, user_id)
    project = session.get(Project, project_id)
    if not user or not project:
        raise HTTPException(status_code=404, detail="User or Project not found")
    
    # Check if already assigned
    link = session.exec(select(UserProjectLink).where(
        UserProjectLink.user_id == user_id,
        UserProjectLink.project_id == project_id
    )).first()
    
    if link:
        return {"ok": True, "message": "Already assigned"}
        
    link = UserProjectLink(user_id=user_id, project_id=project_id)
    session.add(link)
    session.commit()
    
    # Log activity
    log = ActivityLog(user_id=current_user.id, action="ASSIGN_PROJECT", details=f"Assigned project {project.name} to {user.username}")
    session.add(log)
    session.commit()
    
    return {"ok": True}

@router.delete("/{user_id}/projects/{project_id}")
def unassign_project(
    user_id: int,
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    link = session.exec(select(UserProjectLink).where(
        UserProjectLink.user_id == user_id,
        UserProjectLink.project_id == project_id
    )).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    # Get names for logging before delete
    user = session.get(User, user_id)
    project = session.get(Project, project_id)
        
    session.delete(link)
    session.commit()
    
    # Log activity
    if user and project:
        log = ActivityLog(user_id=current_user.id, action="UNASSIGN_PROJECT", details=f"Unassigned project {project.name} from {user.username}")
        session.add(log)
        session.commit()
        
    return {"ok": True}

@router.get("/{user_id}/projects", response_model=list[Project])
def get_user_projects(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.projects
