from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # Load .env file

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base
from routers import projects, tasks, epics, sprints, labels, github, gmail, whatsapp, ai, logs

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Planner API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(epics.router, prefix="/api")
app.include_router(sprints.router, prefix="/api")
app.include_router(labels.router, prefix="/api")
app.include_router(github.router, prefix="/api")
app.include_router(gmail.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard_stats():
    """Get comprehensive dashboard statistics"""
    from sqlalchemy.orm import Session
    from database import SessionLocal
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    import os
    import models

    NZT = ZoneInfo("Pacific/Auckland")
    now = datetime.now(NZT)

    db = SessionLocal()
    try:
        # Task stats
        total_tasks = db.query(models.Task).count()
        tasks_todo = db.query(models.Task).filter(models.Task.status == "todo").count()
        tasks_in_progress = db.query(models.Task).filter(models.Task.status == "in_progress").count()
        tasks_done = db.query(models.Task).filter(models.Task.status == "done").count()

        # Overdue tasks
        overdue = db.query(models.Task).filter(
            models.Task.due_date < now,
            models.Task.status != "done"
        ).count()

        # Due this week
        week_end = now + timedelta(days=7)
        due_this_week = db.query(models.Task).filter(
            models.Task.due_date >= now,
            models.Task.due_date <= week_end,
            models.Task.status != "done"
        ).count()

        # Project stats
        total_projects = db.query(models.Project).count()

        # Epic stats
        total_epics = db.query(models.Epic).count()

        # Sprint stats
        active_sprints = db.query(models.Sprint).filter(models.Sprint.status == "active").count()

        # Email stats
        total_emails = db.query(models.Email).count()
        emails_today = db.query(models.Email).filter(
            models.Email.received_at >= now.replace(hour=0, minute=0, second=0)
        ).count()

        # Calendar events
        upcoming_events = db.query(models.CalendarEvent).filter(
            models.CalendarEvent.start_time >= now
        ).count()

        # Error logs
        total_errors = db.query(models.ErrorLog).count()
        new_errors = db.query(models.ErrorLog).filter(models.ErrorLog.status == "new").count()

        # Integration status
        gmail_configured = bool(os.environ.get("GMAIL_EMAIL") and os.environ.get("GMAIL_APP_PASSWORD"))
        github_configured = bool(os.environ.get("GITHUB_TOKEN"))
        ai_configured = True  # Using Claude CLI

        # Test Gmail connection
        gmail_connected = False
        if gmail_configured:
            try:
                import imaplib
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(
                    os.environ.get("GMAIL_EMAIL"),
                    os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
                )
                mail.logout()
                gmail_connected = True
            except:
                pass

        return {
            "timestamp": now.isoformat(),
            "tasks": {
                "total": total_tasks,
                "todo": tasks_todo,
                "in_progress": tasks_in_progress,
                "done": tasks_done,
                "overdue": overdue,
                "due_this_week": due_this_week
            },
            "projects": total_projects,
            "epics": total_epics,
            "sprints": {
                "active": active_sprints
            },
            "emails": {
                "total": total_emails,
                "today": emails_today
            },
            "calendar": {
                "upcoming": upcoming_events
            },
            "errors": {
                "total": total_errors,
                "new": new_errors
            },
            "integrations": {
                "gmail": {"configured": gmail_configured, "connected": gmail_connected},
                "github": {"configured": github_configured},
                "ai": {"configured": ai_configured}
            }
        }
    finally:
        db.close()


# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Serve index.html for all non-API routes (SPA routing)
        return FileResponse(FRONTEND_DIR / "index.html")
