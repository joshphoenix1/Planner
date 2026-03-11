from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from database import get_db
import models
import schemas

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[schemas.Task])
def list_tasks(
    project_id: Optional[int] = None,
    epic_id: Optional[int] = None,
    sprint_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Task).options(
        joinedload(models.Task.labels),
        joinedload(models.Task.comments)
    )

    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    if epic_id:
        query = query.filter(models.Task.epic_id == epic_id)
    if sprint_id:
        query = query.filter(models.Task.sprint_id == sprint_id)
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)

    return query.order_by(models.Task.order, models.Task.created_at.desc()).all()


@router.post("/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    label_ids = task.label_ids
    task_data = task.model_dump(exclude={"label_ids"})

    db_task = models.Task(**task_data)

    # Add labels
    if label_ids:
        labels = db.query(models.Label).filter(models.Label.id.in_(label_ids)).all()
        db_task.labels = labels

    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/{task_id}", response_model=schemas.Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).options(
        joinedload(models.Task.labels),
        joinedload(models.Task.comments)
    ).filter(models.Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = update.model_dump(exclude_unset=True)
    label_ids = update_data.pop("label_ids", None)

    for key, value in update_data.items():
        setattr(task, key, value)

    if label_ids is not None:
        labels = db.query(models.Label).filter(models.Label.id.in_(label_ids)).all()
        task.labels = labels

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


# Bulk update for drag-drop reordering
@router.post("/reorder")
def reorder_tasks(task_orders: List[dict], db: Session = Depends(get_db)):
    """Update order of multiple tasks at once. Expects [{id, order, status?}]"""
    for item in task_orders:
        task = db.query(models.Task).filter(models.Task.id == item["id"]).first()
        if task:
            task.order = item.get("order", task.order)
            if "status" in item:
                task.status = item["status"]
    db.commit()
    return {"message": "Tasks reordered"}


# Comments
@router.post("/{task_id}/comments", response_model=schemas.Comment)
def add_comment(task_id: int, comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_comment = models.Comment(task_id=task_id, **comment.model_dump())
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.delete("/{task_id}/comments/{comment_id}")
def delete_comment(task_id: int, comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id,
        models.Comment.task_id == task_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


# Time tracking
@router.post("/{task_id}/time", response_model=schemas.TimeEntry)
def log_time(task_id: int, entry: schemas.TimeEntryCreate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_entry = models.TimeEntry(task_id=task_id, **entry.model_dump())
    db.add(db_entry)

    # Update logged hours on task
    task.logged_hours = (task.logged_hours or 0) + entry.hours

    db.commit()
    db.refresh(db_entry)
    return db_entry


@router.get("/{task_id}/time", response_model=List[schemas.TimeEntry])
def get_time_entries(task_id: int, db: Session = Depends(get_db)):
    return db.query(models.TimeEntry).filter(models.TimeEntry.task_id == task_id).all()
