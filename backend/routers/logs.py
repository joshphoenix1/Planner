from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import subprocess
import json

from database import get_db
import models
import schemas

router = APIRouter(prefix="/logs", tags=["logs"])


def call_claude_cli(prompt: str) -> Optional[str]:
    """Call Claude using the claude CLI"""
    try:
        # Use minimal clean environment
        env = {
            "HOME": "/home/ubuntu",
            "PATH": "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "USER": "ubuntu",
        }

        result = subprocess.run(
            ["/home/ubuntu/.local/bin/claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            timeout=90,
            text=True,
            env=env
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


def get_ai_suggestion(error: models.ErrorLog) -> Optional[str]:
    """Use Claude to analyze error and suggest a fix"""
    prompt = f"""Analyze this error and provide a concise fix suggestion.

Source: {error.source}
Error Type: {error.error_type}
Message: {error.message}
Stack Trace: {error.stack_trace[:2000] if error.stack_trace else 'N/A'}

Provide a brief, actionable fix in 2-3 sentences. Focus on the most likely cause and solution."""

    return call_claude_cli(prompt)


@router.get("/", response_model=List[schemas.ErrorLog])
def list_errors(
    source: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(models.ErrorLog)
    if source:
        query = query.filter(models.ErrorLog.source == source)
    if status:
        query = query.filter(models.ErrorLog.status == status)
    return query.order_by(models.ErrorLog.created_at.desc()).limit(limit).all()


@router.post("/", response_model=schemas.ErrorLog)
def log_error(error: schemas.ErrorLogCreate, db: Session = Depends(get_db)):
    db_error = models.ErrorLog(**error.model_dump())
    db.add(db_error)
    db.commit()
    db.refresh(db_error)

    # Get AI suggestion asynchronously would be better, but for simplicity:
    suggestion = get_ai_suggestion(db_error)
    if suggestion:
        db_error.ai_suggestion = suggestion
        db.commit()
        db.refresh(db_error)

    return db_error


@router.post("/{error_id}/analyze")
def analyze_error(error_id: int, db: Session = Depends(get_db)):
    """Re-analyze an error with AI"""
    error = db.query(models.ErrorLog).filter(models.ErrorLog.id == error_id).first()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    suggestion = get_ai_suggestion(error)
    if suggestion:
        error.ai_suggestion = suggestion
        error.status = "reviewing"
        db.commit()
        db.refresh(error)

    return {"suggestion": suggestion}


@router.put("/{error_id}/status")
def update_error_status(error_id: int, status: str, db: Session = Depends(get_db)):
    error = db.query(models.ErrorLog).filter(models.ErrorLog.id == error_id).first()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    error.status = status
    if status == "fixed":
        error.resolved_at = datetime.now()
    db.commit()

    return {"message": "Status updated", "status": status}


@router.delete("/{error_id}")
def delete_error(error_id: int, db: Session = Depends(get_db)):
    error = db.query(models.ErrorLog).filter(models.ErrorLog.id == error_id).first()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")
    db.delete(error)
    db.commit()
    return {"message": "Error deleted"}


@router.delete("/clear-all")
def clear_all_errors(db: Session = Depends(get_db)):
    count = db.query(models.ErrorLog).delete()
    db.commit()
    return {"message": f"Cleared {count} errors"}
