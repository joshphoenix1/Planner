from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import json
import re
import httpx

from database import get_db
import models
import schemas

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

def call_claude_cli(prompt: str):
    """Call Claude using the claude CLI"""
    import subprocess
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


def extract_tasks_from_whatsapp(messages: list, project_id: int, db: Session) -> int:
    """Use AI to extract actionable tasks from WhatsApp messages"""
    if not project_id or not messages:
        return 0

    # Combine recent messages for context
    message_text = "\n".join([f"{m.sender}: {m.content}" for m in messages[:20]])

    prompt = f"""Analyze these WhatsApp messages and extract any actionable tasks or action items.

Messages:
{message_text[:3000]}

Extract ONLY clear, actionable tasks that someone needs to do. Ignore:
- General chat/greetings
- Questions without action items
- Already completed items

Return a JSON array of tasks, each with "title" and "priority" (low/medium/high/urgent).
If no actionable tasks, return empty array [].

Example: [{{"title": "Send proposal to client", "priority": "high"}}, {{"title": "Book meeting room", "priority": "low"}}]

Return ONLY the JSON array, no other text."""

    try:
        text = call_claude_cli(prompt)
        if not text:
            return 0

        # Handle potential markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        tasks = json.loads(text.strip())

        created = 0
        for task_data in tasks[:5]:  # Max 5 tasks
            if task_data.get("title"):
                # Check for duplicate task titles
                existing = db.query(models.Task).filter(
                    models.Task.project_id == project_id,
                    models.Task.title.contains(task_data['title'][:50])
                ).first()
                if not existing:
                    db_task = models.Task(
                        project_id=project_id,
                        title=f"[WhatsApp] {task_data['title'][:200]}",
                        description="Auto-created from WhatsApp messages",
                        priority=task_data.get("priority", "medium"),
                        status="todo"
                    )
                    db.add(db_task)
                    created += 1

        if created:
            db.commit()
        return created
    except:
        pass

    return 0

# WhatsApp Business API config (or use a service like Twilio)
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")


@router.get("/status")
def whatsapp_status():
    """Check WhatsApp integration status"""
    configured = bool(WHATSAPP_TOKEN)
    return {
        "configured": configured,
        "message": "WhatsApp configured" if configured else "Set WHATSAPP_TOKEN environment variable"
    }


# WhatsApp Group Mappings (which groups map to which projects)
@router.get("/groups", response_model=List[schemas.WhatsAppGroup])
def list_groups(db: Session = Depends(get_db)):
    return db.query(models.WhatsAppGroup).all()


@router.post("/groups", response_model=schemas.WhatsAppGroup)
def create_group(group: schemas.WhatsAppGroupCreate, db: Session = Depends(get_db)):
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == group.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_group = models.WhatsAppGroup(**group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@router.put("/groups/{group_id}", response_model=schemas.WhatsAppGroup)
def update_group(group_id: int, update: schemas.WhatsAppGroupUpdate, db: Session = Depends(get_db)):
    group = db.query(models.WhatsAppGroup).filter(models.WhatsAppGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(group, key, value)

    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(models.WhatsAppGroup).filter(models.WhatsAppGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(group)
    db.commit()
    return {"message": "Group deleted"}


# Webhook for receiving WhatsApp messages
@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive incoming WhatsApp messages via webhook"""
    try:
        data = await request.json()
    except:
        return {"status": "ok"}

    # Handle WhatsApp Cloud API webhook format
    if "entry" in data:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    # Extract message details
                    from_number = msg.get("from", "")
                    msg_type = msg.get("type", "")
                    timestamp = msg.get("timestamp", "")

                    # Get text content
                    text = ""
                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "")

                    # Check if this is from a tracked group
                    # Note: Group messages have a different structure
                    group_id = value.get("metadata", {}).get("phone_number_id", "")

                    # Find matching group
                    group = db.query(models.WhatsAppGroup).filter(
                        models.WhatsAppGroup.group_id == group_id
                    ).first()

                    if group and text:
                        # Parse for tasks (messages starting with "TASK:" or "TODO:")
                        task_match = re.match(r'^(TASK|TODO|ACTION):\s*(.+)', text, re.IGNORECASE)
                        if task_match:
                            task_title = task_match.group(2)
                            # Create task
                            task = models.Task(
                                project_id=group.project_id,
                                title=task_title,
                                description=f"From WhatsApp ({from_number}): {text}",
                                status="todo",
                                priority="medium"
                            )
                            db.add(task)

                        # Parse for notes (messages starting with "NOTE:")
                        note_match = re.match(r'^NOTE:\s*(.+)', text, re.IGNORECASE)
                        if note_match:
                            # Store as WhatsApp message
                            wa_msg = models.WhatsAppMessage(
                                group_mapping_id=group.id,
                                sender=from_number,
                                content=text,
                                message_type="note",
                                received_at=datetime.fromtimestamp(int(timestamp)) if timestamp else datetime.now()
                            )
                            db.add(wa_msg)

                        # Store all messages for context
                        wa_msg = models.WhatsAppMessage(
                            group_mapping_id=group.id,
                            sender=from_number,
                            content=text,
                            message_type=msg_type,
                            received_at=datetime.fromtimestamp(int(timestamp)) if timestamp else datetime.now()
                        )
                        db.add(wa_msg)

                        db.commit()

    return {"status": "ok"}


# Webhook verification for WhatsApp Cloud API
@router.get("/webhook")
async def verify_webhook(request: Request):
    """Verify webhook for WhatsApp Cloud API"""
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "planner_verify")

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


# Get messages
@router.get("/messages", response_model=List[schemas.WhatsAppMessage])
def list_messages(
    group_id: Optional[int] = None,
    project_id: Optional[int] = None,
    message_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(models.WhatsAppMessage)

    if group_id:
        query = query.filter(models.WhatsAppMessage.group_mapping_id == group_id)
    if project_id:
        query = query.join(models.WhatsAppGroup).filter(models.WhatsAppGroup.project_id == project_id)
    if message_type:
        query = query.filter(models.WhatsAppMessage.message_type == message_type)

    return query.order_by(models.WhatsAppMessage.received_at.desc()).limit(limit).all()


# Manual message entry (for testing or manual import)
@router.post("/messages", response_model=schemas.WhatsAppMessage)
def create_message(message: schemas.WhatsAppMessageCreate, db: Session = Depends(get_db)):
    db_msg = models.WhatsAppMessage(**message.model_dump())
    db.add(db_msg)

    # Auto-create task if it's a task message
    if message.content:
        task_match = re.match(r'^(TASK|TODO|ACTION):\s*(.+)', message.content, re.IGNORECASE)
        if task_match:
            group = db.query(models.WhatsAppGroup).filter(
                models.WhatsAppGroup.id == message.group_mapping_id
            ).first()
            if group:
                task = models.Task(
                    project_id=group.project_id,
                    title=task_match.group(2),
                    description=f"From WhatsApp: {message.content}",
                    status="todo",
                    priority="medium"
                )
                db.add(task)

    db.commit()
    db.refresh(db_msg)
    return db_msg


@router.delete("/messages/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(models.WhatsAppMessage).filter(models.WhatsAppMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
    return {"message": "Message deleted"}


@router.post("/sync")
def sync_whatsapp_tasks(db: Session = Depends(get_db)):
    """Analyze WhatsApp messages and auto-create tasks using AI"""
    groups = db.query(models.WhatsAppGroup).filter(
        models.WhatsAppGroup.is_active == True,
        models.WhatsAppGroup.auto_create_tasks == True
    ).all()

    total_tasks = 0
    for group in groups:
        # Get recent messages for this group
        messages = db.query(models.WhatsAppMessage).filter(
            models.WhatsAppMessage.group_mapping_id == group.id
        ).order_by(models.WhatsAppMessage.received_at.desc()).limit(50).all()

        if messages:
            tasks_created = extract_tasks_from_whatsapp(messages, group.project_id, db)
            total_tasks += tasks_created

    return {"message": f"Created {total_tasks} tasks from WhatsApp messages", "tasks_created": total_tasks}
