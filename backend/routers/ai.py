from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import os
import json
import subprocess
import asyncio
import httpx

from database import get_db
import models
import schemas

router = APIRouter(prefix="/ai", tags=["ai"])

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


async def call_claude_api(prompt: str, system: str = None, max_tokens: int = 1024) -> str:
    """Fallback: Call Claude via direct API"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="No API key configured")

    messages = [{"role": "user", "content": prompt}]
    body = {"model": "claude-sonnet-4-20250514", "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=body,
            timeout=60.0
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"API error: {resp.text}")
        return resp.json()["content"][0]["text"]


def call_claude_sync(prompt: str, system: str = None) -> str:
    """Call Claude CLI synchronously"""
    full_prompt = prompt
    if system:
        full_prompt = f"System: {system}\n\nUser: {prompt}"

    # Use minimal clean environment
    env = {
        "HOME": "/home/ubuntu",
        "PATH": "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin",
        "USER": "ubuntu",
    }

    result = subprocess.run(
        ["/home/ubuntu/.local/bin/claude", "-p", full_prompt, "--output-format", "text"],
        capture_output=True,
        timeout=90,
        text=True,
        env=env
    )

    if result.returncode == 0:
        return result.stdout.strip()

    # Include both stderr and stdout in error for debugging
    error_info = f"stderr={result.stderr!r}, stdout={result.stdout!r}, code={result.returncode}"
    raise Exception(f"CLI error: {error_info}")


async def call_claude(prompt: str, system: str = None, max_tokens: int = 1024) -> str:
    """Call Claude - runs CLI in thread pool"""
    import concurrent.futures

    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await asyncio.wait_for(
                loop.run_in_executor(pool, lambda: call_claude_sync(prompt, system)),
                timeout=120.0
            )
            return result

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        error_msg = str(e)
        # Try API fallback if CLI fails
        if ANTHROPIC_API_KEY and ("nested" in error_msg.lower() or "CLI" in error_msg):
            try:
                return await call_claude_api(prompt, system, max_tokens)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error: {error_msg}")


def check_claude_cli() -> bool:
    """Check if claude CLI is available"""
    try:
        result = subprocess.run(["which", "claude"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


@router.get("/status")
def ai_status():
    """Check AI integration status"""
    cli_available = check_claude_cli()
    return {
        "configured": cli_available,
        "model": "claude-code",
        "method": "claude CLI"
    }


# 1. Summarize emails
@router.post("/summarize-email/{email_id}")
async def summarize_email(email_id: int, db: Session = Depends(get_db)):
    """Generate a summary and extract action items from an email"""
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    prompt = f"""Analyze this email and provide:
1. A brief summary (2-3 sentences)
2. Key action items or tasks mentioned
3. Any deadlines or dates mentioned
4. Priority level (low/medium/high/urgent)

Email Subject: {email.subject}
From: {email.sender}
Content:
{email.body or email.snippet}
"""

    system = "You are a productivity assistant that extracts actionable insights from emails. Be concise and focus on what needs to be done."

    result = await call_claude(prompt, system)

    return {
        "email_id": email_id,
        "summary": result
    }


# 2. Parse WhatsApp messages intelligently
@router.post("/parse-whatsapp")
async def parse_whatsapp_message(content: str, db: Session = Depends(get_db)):
    """Intelligently parse a WhatsApp message for tasks, notes, and context"""

    prompt = f"""Analyze this WhatsApp message and extract:
1. Is this a task/action item? If yes, what's the task?
2. Is this a note worth saving? If yes, summarize it.
3. Any deadlines or dates mentioned?
4. Priority (if it seems urgent)
5. Category: task, note, question, update, or casual

Message: {content}

Respond in JSON format:
{{"is_task": bool, "task_title": str or null, "is_note": bool, "note_summary": str or null, "deadline": str or null, "priority": "low"|"medium"|"high"|"urgent", "category": str}}
"""

    system = "You are a message parser. Extract structured data from informal messages. Respond only with valid JSON."

    result = await call_claude(prompt, system)

    try:
        return json.loads(result)
    except:
        return {"raw_response": result}


# 3. Sprint planning - break down epics into tasks
@router.post("/plan-sprint/{epic_id}")
async def plan_sprint(epic_id: int, num_tasks: int = 5, db: Session = Depends(get_db)):
    """Generate task suggestions for an epic"""
    epic = db.query(models.Epic).filter(models.Epic.id == epic_id).first()
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")

    # Get existing tasks for context
    existing_tasks = db.query(models.Task).filter(models.Task.epic_id == epic_id).all()
    existing_titles = [t.title for t in existing_tasks]

    prompt = f"""You're helping plan a software development sprint.

Epic: {epic.name}
Description: {epic.description or 'No description provided'}

Existing tasks already created:
{chr(10).join(f'- {t}' for t in existing_titles) if existing_titles else 'None yet'}

Suggest {num_tasks} new tasks to complete this epic. For each task provide:
- title: Clear, actionable task title
- description: Brief description of what needs to be done
- priority: low/medium/high
- estimated_hours: Rough estimate

Respond in JSON format as an array of task objects.
"""

    system = "You are a technical project manager. Suggest practical, well-scoped tasks that a developer can complete. Focus on implementation tasks, not planning tasks."

    result = await call_claude(prompt, system, max_tokens=2000)

    try:
        tasks = json.loads(result)
        return {"epic_id": epic_id, "suggested_tasks": tasks}
    except:
        return {"raw_response": result}


# 4. Daily digest
@router.get("/daily-digest")
async def daily_digest(db: Session = Depends(get_db)):
    """Generate a daily digest of all project activity"""

    # Get recent activity
    yesterday = datetime.now() - timedelta(days=1)

    # Recent tasks
    recent_tasks = db.query(models.Task).filter(
        models.Task.created_at >= yesterday
    ).all()

    # Tasks due soon
    upcoming = datetime.now() + timedelta(days=3)
    due_soon = db.query(models.Task).filter(
        models.Task.due_date <= upcoming,
        models.Task.due_date >= datetime.now(),
        models.Task.status != "done"
    ).all()

    # In progress tasks
    in_progress = db.query(models.Task).filter(
        models.Task.status == "in_progress"
    ).all()

    # Active sprints
    active_sprints = db.query(models.Sprint).filter(
        models.Sprint.status == "active"
    ).all()

    # Recent emails
    recent_emails = db.query(models.Email).filter(
        models.Email.synced_at >= yesterday
    ).limit(10).all()

    prompt = f"""Generate a daily digest summary for a project manager.

New Tasks Created (last 24h): {len(recent_tasks)}
{chr(10).join(f'- {t.title} ({t.priority})' for t in recent_tasks[:10])}

Tasks Due in Next 3 Days: {len(due_soon)}
{chr(10).join(f'- {t.title} (due: {t.due_date})' for t in due_soon[:10])}

Currently In Progress: {len(in_progress)}
{chr(10).join(f'- {t.title}' for t in in_progress[:10])}

Active Sprints: {len(active_sprints)}
{chr(10).join(f'- {s.name}: {s.goal or "No goal set"}' for s in active_sprints)}

Recent Emails Synced: {len(recent_emails)}
{chr(10).join(f'- {e.subject} (from: {e.sender})' for e in recent_emails[:5])}

Provide:
1. A brief executive summary (2-3 sentences)
2. Top 3 priorities for today
3. Any risks or blockers to flag
4. Quick wins that could be completed today
"""

    system = "You are a helpful project assistant generating a morning briefing. Be concise and actionable."

    result = await call_claude(prompt, system, max_tokens=1500)

    return {
        "date": datetime.now().isoformat(),
        "stats": {
            "new_tasks": len(recent_tasks),
            "due_soon": len(due_soon),
            "in_progress": len(in_progress),
            "active_sprints": len(active_sprints),
            "recent_emails": len(recent_emails)
        },
        "digest": result
    }


# 5. Smart categorization
@router.post("/categorize-task/{task_id}")
async def categorize_task(task_id: int, db: Session = Depends(get_db)):
    """Auto-suggest epic and sprint for a task based on content"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get available epics and sprints for this project
    epics = db.query(models.Epic).filter(
        models.Epic.project_id == task.project_id,
        models.Epic.status != "done"
    ).all()

    sprints = db.query(models.Sprint).filter(
        models.Sprint.project_id == task.project_id,
        models.Sprint.status.in_(["planned", "active"])
    ).all()

    if not epics and not sprints:
        return {"message": "No epics or sprints available to categorize into"}

    prompt = f"""Analyze this task and suggest the best epic and sprint for it.

Task: {task.title}
Description: {task.description or 'No description'}
Priority: {task.priority}

Available Epics:
{chr(10).join(f'- ID {e.id}: {e.name} - {e.description or "No description"}' for e in epics) or 'None'}

Available Sprints:
{chr(10).join(f'- ID {s.id}: {s.name} ({s.status}) - {s.goal or "No goal"}' for s in sprints) or 'None'}

Respond in JSON format:
{{"suggested_epic_id": int or null, "epic_reason": str, "suggested_sprint_id": int or null, "sprint_reason": str}}
"""

    system = "You are a project organizer. Match tasks to the most relevant epic and sprint based on their descriptions and goals."

    result = await call_claude(prompt, system)

    try:
        suggestions = json.loads(result)
        return {"task_id": task_id, **suggestions}
    except:
        return {"raw_response": result}


# Batch process - auto-categorize all uncategorized tasks
@router.post("/auto-categorize-all")
async def auto_categorize_all(project_id: int, db: Session = Depends(get_db)):
    """Auto-categorize all tasks without an epic or sprint"""
    tasks = db.query(models.Task).filter(
        models.Task.project_id == project_id,
        models.Task.epic_id == None
    ).all()

    results = []
    for task in tasks[:10]:  # Limit to 10 to avoid rate limits
        try:
            result = await categorize_task(task.id, db)
            results.append(result)
        except:
            continue

    return {"processed": len(results), "results": results}


from pydantic import BaseModel
import httpx as httpx_sync

class TaskFromTextRequest(BaseModel):
    text: str
    project_id: int


class TasksFromUrlRequest(BaseModel):
    url: str
    project_id: int


@router.post("/tasks-from-url")
async def create_tasks_from_url(request: TasksFromUrlRequest, db: Session = Depends(get_db)):
    """Fetch a URL (proposal, doc, etc) and extract tasks from it using AI"""
    url = request.url
    project_id = request.project_id

    # Fetch the URL content
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30.0, follow_redirects=True)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Could not fetch URL: {resp.status_code}")
            content = resp.text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")

    # Extract text from HTML if needed
    if "<html" in content.lower() or "<body" in content.lower():
        import re
        # Remove scripts and styles
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()

    # Truncate if too long
    content = content[:8000]

    prompt = f"""Analyze this document/proposal and extract actionable tasks.

Document content:
{content}

Extract ALL actionable tasks, deliverables, milestones, and action items from this document.
For each task, provide:
- title: Clear, actionable task title
- description: Brief description of what needs to be done
- priority: low/medium/high/urgent
- estimated_hours: Rough estimate if possible

Return a JSON array of tasks. If no tasks found, return empty array [].

Example:
[
  {{"title": "Set up development environment", "description": "Install required tools and configure project", "priority": "high", "estimated_hours": 4}},
  {{"title": "Design database schema", "description": "Create ERD and define tables", "priority": "high", "estimated_hours": 8}}
]

Return ONLY the JSON array, no other text."""

    system = "You are a project manager extracting tasks from proposals and documents. Be thorough and extract all actionable items."

    result = await call_claude(prompt, system, max_tokens=2000)

    try:
        # Strip markdown code blocks if present
        json_str = result.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1] if "\n" in json_str else json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str.rsplit("```", 1)[0]
        json_str = json_str.strip()

        tasks_data = json.loads(json_str)

        # Create tasks in database
        created_tasks = []
        for task_data in tasks_data:
            if task_data.get("title"):
                new_task = models.Task(
                    project_id=project_id,
                    title=task_data.get("title", "")[:200],
                    description=task_data.get("description"),
                    priority=task_data.get("priority", "medium"),
                    estimated_hours=task_data.get("estimated_hours"),
                    status="todo"
                )
                db.add(new_task)
                created_tasks.append(task_data)

        db.commit()

        return {
            "url": url,
            "tasks_created": len(created_tasks),
            "tasks": created_tasks
        }

    except Exception as e:
        return {"error": str(e), "raw_response": result}


# Generate task from natural language
@router.post("/create-task-from-text")
async def create_task_from_text(request: TaskFromTextRequest, db: Session = Depends(get_db)):
    """Parse natural language into a structured task"""
    text = request.text
    project_id = request.project_id

    prompt = f"""Parse this text into a task:

"{text}"

Extract:
- title: Clear, actionable task title
- description: Any additional details
- priority: low/medium/high/urgent (based on language like "ASAP", "urgent", "when you get a chance")
- due_date: If a date is mentioned, parse it (return as ISO format or null)
- estimated_hours: If mentioned or can be reasonably estimated

Respond in JSON format.
"""

    system = "You are a task parser. Convert informal requests into structured task data."

    result = await call_claude(prompt, system)

    try:
        # Strip markdown code blocks if present
        json_str = result.strip()
        if json_str.startswith("```"):
            # Remove opening ```json or ```
            json_str = json_str.split("\n", 1)[1] if "\n" in json_str else json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str.rsplit("```", 1)[0]
        json_str = json_str.strip()

        task_data = json.loads(json_str)

        # Create the task
        new_task = models.Task(
            project_id=project_id,
            title=task_data.get("title", text[:100]),
            description=task_data.get("description"),
            priority=task_data.get("priority", "medium"),
            estimated_hours=task_data.get("estimated_hours"),
            status="todo"
        )

        if task_data.get("due_date"):
            try:
                new_task.due_date = datetime.fromisoformat(task_data["due_date"].replace("Z", "+00:00"))
            except:
                pass

        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        return {"task": schemas.Task.model_validate(new_task), "parsed": task_data}

    except Exception as e:
        return {"error": str(e), "raw_response": result}


@router.get("/recommendations")
async def get_recommendations(db: Session = Depends(get_db)):
    """AI assistant that analyzes emails, tasks, and messages to recommend priorities"""
    from zoneinfo import ZoneInfo
    NZT = ZoneInfo("Pacific/Auckland")
    now = datetime.now(NZT)

    # Get recent emails (last 7 days)
    week_ago = now - timedelta(days=7)
    emails = db.query(models.Email).filter(
        models.Email.received_at >= week_ago
    ).order_by(models.Email.received_at.desc()).limit(15).all()

    # Get all active tasks
    tasks = db.query(models.Task).filter(
        models.Task.status.in_(["todo", "in_progress"])
    ).order_by(models.Task.due_date.asc().nullslast()).limit(20).all()

    # Get upcoming calendar events
    calendar = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.start_time >= now.isoformat()
    ).order_by(models.CalendarEvent.start_time.asc()).limit(10).all()

    # Get projects for context
    projects = db.query(models.Project).all()
    project_map = {p.id: p.name for p in projects}

    # Build context for AI
    email_summaries = []
    for e in emails[:10]:
        proj_name = project_map.get(e.project_id, "Unassigned")
        email_summaries.append(f"- [{proj_name}] From: {e.sender} | Subject: {e.subject} | {e.snippet[:100] if e.snippet else ''}")

    task_summaries = []
    for t in tasks:
        proj_name = project_map.get(t.project_id, "Unknown")
        due = f"Due: {t.due_date.strftime('%b %d')}" if t.due_date else "No due date"
        task_summaries.append(f"- [{proj_name}] {t.title} | {t.priority} priority | {due} | Status: {t.status}")

    calendar_summaries = []
    for c in calendar[:5]:
        calendar_summaries.append(f"- {c.title} | {c.start_time}")

    prompt = f"""You are a smart project assistant. Analyze the user's current workload and provide actionable recommendations.

CURRENT DATE/TIME: {now.strftime('%A, %B %d, %Y %I:%M %p')} (NZT)

RECENT EMAILS ({len(emails)} total):
{chr(10).join(email_summaries) if email_summaries else 'No recent emails'}

ACTIVE TASKS ({len(tasks)} total):
{chr(10).join(task_summaries) if task_summaries else 'No active tasks'}

UPCOMING CALENDAR:
{chr(10).join(calendar_summaries) if calendar_summaries else 'No upcoming events'}

Based on this information, provide:

1. **Top 3 Priority Actions** - What should be done RIGHT NOW? Consider due dates, urgency in emails, and upcoming meetings.

2. **Emails Requiring Response** - Any emails that seem to need a reply or action?

3. **Blocked or At-Risk Items** - Tasks that might be delayed or need attention?

4. **Today's Focus** - A simple 2-3 bullet summary of what to focus on today.

Be concise and actionable. Use markdown formatting."""

    try:
        result = await call_claude(prompt)
        return {
            "recommendations": result,
            "generated_at": now.isoformat(),
            "context": {
                "emails_analyzed": len(emails),
                "tasks_analyzed": len(tasks),
                "events_analyzed": len(calendar)
            }
        }
    except Exception as e:
        return {
            "recommendations": None,
            "error": str(e),
            "generated_at": now.isoformat()
        }
