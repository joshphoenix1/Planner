from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(prefix="/projects", tags=["projects"])


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
