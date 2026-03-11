from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas

router = APIRouter(prefix="/epics", tags=["epics"])


@router.get("/", response_model=List[schemas.Epic])
def list_epics(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Epic)
    if project_id:
        query = query.filter(models.Epic.project_id == project_id)
    return query.order_by(models.Epic.created_at.desc()).all()


@router.post("/", response_model=schemas.Epic)
def create_epic(epic: schemas.EpicCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == epic.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_epic = models.Epic(**epic.model_dump())
    db.add(db_epic)
    db.commit()
    db.refresh(db_epic)
    return db_epic


@router.get("/{epic_id}", response_model=schemas.Epic)
def get_epic(epic_id: int, db: Session = Depends(get_db)):
    epic = db.query(models.Epic).filter(models.Epic.id == epic_id).first()
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")
    return epic


@router.put("/{epic_id}", response_model=schemas.Epic)
def update_epic(epic_id: int, update: schemas.EpicUpdate, db: Session = Depends(get_db)):
    epic = db.query(models.Epic).filter(models.Epic.id == epic_id).first()
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(epic, key, value)

    db.commit()
    db.refresh(epic)
    return epic


@router.delete("/{epic_id}")
def delete_epic(epic_id: int, db: Session = Depends(get_db)):
    epic = db.query(models.Epic).filter(models.Epic.id == epic_id).first()
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")

    db.delete(epic)
    db.commit()
    return {"message": "Epic deleted"}
