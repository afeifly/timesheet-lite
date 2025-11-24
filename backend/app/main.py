from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_db_and_tables, get_session, engine
from app.api import auth, projects, timesheets, reports, activity_logs, users
from app.models import Project, User, Role
from app.core.security import get_password_hash
from sqlmodel import Session, select

app = FastAPI(title="Timesheet System")

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(timesheets.router, prefix="/timesheets", tags=["timesheets"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(activity_logs.router, prefix="/activity_logs", tags=["activity_logs"])
app.include_router(users.router, prefix="/users", tags=["users"])

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    
    # Initialize default projects and admin user
    with Session(engine) as session:
        # Default Projects
        default_projects = ["Research", "Maintenance", "Others"]
        for p_name in default_projects:
            project = session.exec(select(Project).where(Project.name == p_name)).first()
            if not project:
                session.add(Project(name=p_name, description=f"Default {p_name} project", is_default=True))
        
        # Default Admin
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            session.add(User(
                username="admin", 
                password_hash=get_password_hash("admin123"), 
                role=Role.ADMIN
            ))
        
        session.commit()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Timesheet System API"}
