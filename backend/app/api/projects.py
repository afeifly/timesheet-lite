from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col
from app.database import get_session
from app.models import Project, User, ActivityLog, Role
from app.api.deps import get_current_user, get_current_admin_user

router = APIRouter()

@router.get("/", response_model=List[Project])
def read_projects(
    skip: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    query = select(Project).where(Project.is_deleted == False)
    
    # Allow all users to see all projects (read-only for non-admins handled in frontend/backend write ops)
    # if current_user.role != Role.ADMIN:
    #     # Filter: Default projects OR Assigned projects
    #     # We need to join with UserProjectLink or check ID in list
    #     # Easiest way with SQLModel/SQLAlchemy:
    #     # WHERE is_default = True OR id IN (select project_id from userprojectlink where user_id = current_user.id)
        
    #     # Since SQLModel relationships load objects, we can also use python filtering if list is small, 
    #     # but better to do in DB.
    #     # Let's use the relationship.
        
    #     # Actually, simpler query:
    #     # Select projects where is_default is True
    #     # UNION
    #     # Select projects joined with current_user
        
    #     # Let's try to construct a single query if possible, or just fetch both and merge in python (easier for now given complexity)
    #     # But for pagination, DB query is better.
        
    #     # Using `user.projects` relationship from the model
    #     # But we need to combine with default projects.
        
    #     # Let's do it via IDs
    #     assigned_project_ids = [p.id for p in current_user.projects]
        
    #     query = query.where(
    #         (Project.is_default == True) | 
    #         (col(Project.id).in_(assigned_project_ids))
    #     )
        
    return session.exec(query.offset(skip).limit(limit)).all()

@router.post("/", response_model=Project)
def create_project(
    project: Project, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user)
):
    db_project = session.exec(select(Project).where(Project.name == project.name)).first()
    if db_project:
        raise HTTPException(status_code=400, detail="Project already exists")
    
    # Manually convert date strings to date objects if needed
    # This is needed because SQLite driver is strict and Pydantic/SQLModel might pass strings if not validated strictly enough or if using mixed types
    from datetime import datetime
    
    if isinstance(project.start_date, str):
        project.start_date = datetime.strptime(project.start_date, "%Y-%m-%d").date()
    if isinstance(project.plan_closed_date, str):
        project.plan_closed_date = datetime.strptime(project.plan_closed_date, "%Y-%m-%d").date()
    if isinstance(project.actual_closed_date, str):
        project.actual_closed_date = datetime.strptime(project.actual_closed_date, "%Y-%m-%d").date()
        
    session.add(project)
    session.commit()
    session.refresh(project)
    
    # Log activity
    log = ActivityLog(user_id=current_user.id, action="CREATE_PROJECT", details=f"Created project {project.name}")
    session.add(log)
    session.commit()
    
    return project

@router.delete("/{project_id}")
def delete_project(
    project_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default projects")
        
    project.is_deleted = True
    session.add(project)
    session.commit()
    
    # Log activity
    log = ActivityLog(user_id=current_user.id, action="DELETE_PROJECT", details=f"Soft deleted project {project.name}")
    session.add(log)
    session.commit()
    
    return {"ok": True}

@router.put("/{project_id}", response_model=Project)
def update_project(
    project_id: int,
    project_update: Project,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin_user)
):
    db_project = session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project_data = project_update.dict(exclude_unset=True)
    
    # Handle date conversion for updates too
    from datetime import datetime
    for date_field in ['start_date', 'plan_closed_date', 'actual_closed_date']:
        if date_field in project_data and isinstance(project_data[date_field], str):
             project_data[date_field] = datetime.strptime(project_data[date_field], "%Y-%m-%d").date()

    for key, value in project_data.items():
        setattr(db_project, key, value)
        
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    
    log = ActivityLog(user_id=current_user.id, action="UPDATE_PROJECT", details=f"Updated project {db_project.name}")
    session.add(log)
    session.commit()
    
    return db_project
