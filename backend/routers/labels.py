from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(prefix="/labels", tags=["labels"])


@router.get("/", response_model=List[schemas.Label])
def list_labels(db: Session = Depends(get_db)):
    return db.query(models.Label).order_by(models.Label.name).all()


@router.post("/", response_model=schemas.Label)
def create_label(label: schemas.LabelCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Label).filter(models.Label.name == label.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Label already exists")

    db_label = models.Label(**label.model_dump())
    db.add(db_label)
    db.commit()
    db.refresh(db_label)
    return db_label


@router.delete("/{label_id}")
def delete_label(label_id: int, db: Session = Depends(get_db)):
    label = db.query(models.Label).filter(models.Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    db.delete(label)
    db.commit()
    return {"message": "Label deleted"}
