from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas

router = APIRouter(prefix="/sprints", tags=["sprints"])


@router.get("/", response_model=List[schemas.Sprint])
def list_sprints(project_id: Optional[int] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Sprint)
    if project_id:
        query = query.filter(models.Sprint.project_id == project_id)
    if status:
        query = query.filter(models.Sprint.status == status)
    return query.order_by(models.Sprint.start_date.desc()).all()


@router.post("/", response_model=schemas.Sprint)
def create_sprint(sprint: schemas.SprintCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == sprint.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_sprint = models.Sprint(**sprint.model_dump())
    db.add(db_sprint)
    db.commit()
    db.refresh(db_sprint)
    return db_sprint


@router.get("/{sprint_id}", response_model=schemas.Sprint)
def get_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint


@router.put("/{sprint_id}", response_model=schemas.Sprint)
def update_sprint(sprint_id: int, update: schemas.SprintUpdate, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(sprint, key, value)

    db.commit()
    db.refresh(sprint)
    return sprint


@router.delete("/{sprint_id}")
def delete_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    db.delete(sprint)
    db.commit()
    return {"message": "Sprint deleted"}


@router.post("/{sprint_id}/start", response_model=schemas.Sprint)
def start_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # Close any active sprints in this project
    db.query(models.Sprint).filter(
        models.Sprint.project_id == sprint.project_id,
        models.Sprint.status == "active"
    ).update({"status": "completed"})

    sprint.status = "active"
    db.commit()
    db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/complete", response_model=schemas.Sprint)
def complete_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    sprint.status = "completed"
    db.commit()
    db.refresh(sprint)
    return sprint
