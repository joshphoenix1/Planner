from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import subprocess

from database import get_db
import models
import schemas

router = APIRouter(prefix="/projects", tags=["projects"])


def call_claude_cli(prompt: str) -> str:
    """Call Claude CLI"""
    try:
        env = {
            "HOME": "/home/ubuntu",
            "PATH": "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "USER": "ubuntu",
        }
        result = subprocess.run(
            ["/home/ubuntu/.local/bin/claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            timeout=120,
            text=True,
            env=env
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return ""


@router.get("/", response_model=List[schemas.ProjectWithStats])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.updated_at.desc()).all()
    result = []
    for p in projects:
        task_count = db.query(models.Task).filter(models.Task.project_id == p.id).count()
        completed_count = db.query(models.Task).filter(
            models.Task.project_id == p.id,
            models.Task.status == "done"
        ).count()
        epic_count = db.query(models.Epic).filter(models.Epic.project_id == p.id).count()
        sprint_count = db.query(models.Sprint).filter(models.Sprint.project_id == p.id).count()

        result.append(schemas.ProjectWithStats(
            **schemas.Project.model_validate(p).model_dump(),
            task_count=task_count,
            completed_count=completed_count,
            epic_count=epic_count,
            sprint_count=sprint_count
        ))
    return result


@router.post("/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/{project_id}", response_model=schemas.ProjectWithStats)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_count = db.query(models.Task).filter(models.Task.project_id == project_id).count()
    completed_count = db.query(models.Task).filter(
        models.Task.project_id == project_id,
        models.Task.status == "done"
    ).count()
    epic_count = db.query(models.Epic).filter(models.Epic.project_id == project_id).count()
    sprint_count = db.query(models.Sprint).filter(models.Sprint.project_id == project_id).count()

    return schemas.ProjectWithStats(
        **schemas.Project.model_validate(project).model_dump(),
        task_count=task_count,
        completed_count=completed_count,
        epic_count=epic_count,
        sprint_count=sprint_count
    )


@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/generate-notes")
def generate_project_notes(project_id: int, db: Session = Depends(get_db)):
    """Generate/refresh project notes from all project emails using AI"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all emails for this project
    emails = db.query(models.Email).filter(
        models.Email.project_id == project_id
    ).order_by(models.Email.received_at.desc()).limit(20).all()

    if not emails:
        return {"message": "No emails found for this project", "notes": None}

    # Build email summary for AI
    email_summaries = []
    for e in emails:
        email_summaries.append(f"""
--- Email ---
Subject: {e.subject}
From: {e.sender}
Date: {e.received_at}
Content: {e.body[:1500] if e.body else e.snippet[:500]}
""")

    emails_text = "\n".join(email_summaries[:10])  # Limit to 10 most recent

    prompt = f"""Analyze these project emails and create a comprehensive project summary.

PROJECT: {project.name}
{project.description or ''}

EMAILS:
{emails_text}

Create a project summary that includes:
1. **Project Overview** - What is this project about? (2-3 sentences)
2. **Key Contacts** - Who are the main stakeholders/contacts?
3. **Current Status** - What's the current state based on recent emails?
4. **Action Items** - What needs to be done?
5. **Important Dates** - Any deadlines or milestones mentioned?
6. **Notes** - Any other important information

Write in markdown format. Be concise but comprehensive."""

    notes = call_claude_cli(prompt)

    if notes:
        project.notes = notes
        db.commit()
        return {"message": "Notes generated successfully", "notes": notes}
    else:
        return {"message": "Failed to generate notes", "notes": None}
