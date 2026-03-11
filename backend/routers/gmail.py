from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import imaplib
import email
from email.header import decode_header
import json
import httpx

from database import get_db
import models
import schemas

# NZT timezone
NZT = ZoneInfo("Pacific/Auckland")

router = APIRouter(prefix="/gmail", tags=["gmail"])

GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def get_imap_connection():
    """Connect to Gmail via IMAP"""
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        raise HTTPException(status_code=400, detail="Gmail credentials not configured")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD.replace(" ", ""))
    return mail


def decode_mime_header(header):
    """Decode email header"""
    if not header:
        return ""
    decoded = decode_header(header)
    result = []
    for part, charset in decoded:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='ignore'))
        else:
            result.append(part)
    return ''.join(result)


def get_email_body(msg):
    """Extract plain text body from email"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    return body[:10000]


def call_claude_cli(prompt: str) -> Optional[str]:
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


def extract_tasks_from_email(subject: str, body: str, sender: str, project_id: int, db: Session) -> int:
    """Use AI to extract actionable tasks from email content"""
    if not project_id:
        return 0

    prompt = f"""Analyze this email and extract any actionable tasks or action items.

Email Subject: {subject}
From: {sender}
Body: {body[:2000]}

Extract ONLY clear, actionable tasks that need to be done. Ignore general information.
Return a JSON array of tasks, each with "title" and "priority" (low/medium/high/urgent).
If no actionable tasks, return empty array [].

Example: [{{"title": "Review proposal by Friday", "priority": "high"}}, {{"title": "Schedule follow-up call", "priority": "medium"}}]

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
        for task_data in tasks[:5]:  # Max 5 tasks per email
            if task_data.get("title"):
                db_task = models.Task(
                    project_id=project_id,
                    title=f"[Email] {task_data['title'][:200]}",
                    description=f"Auto-created from email: {subject}\nFrom: {sender}",
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


def assign_project_with_ai(subject: str, body: str, sender: str, projects: list) -> Optional[int]:
    """Use Claude to determine which project an email belongs to"""
    if not projects:
        return None

    project_list = "\n".join([f"- ID {p.id}: {p.name} - {p.description or 'No description'}" for p in projects])

    prompt = f"""Analyze this email and determine which project it belongs to.

Email Subject: {subject}
From: {sender}
Body (first 1000 chars): {body[:1000]}

Available Projects:
{project_list}

Which project does this email most likely relate to? If none seem relevant, respond with null.
Respond with ONLY a JSON object: {{"project_id": <number or null>, "reason": "<brief reason>"}}"""

    try:
        text = call_claude_cli(prompt)
        if text:
            result = json.loads(text)
            return result.get("project_id")
    except:
        pass

    return None


@router.get("/status")
def gmail_status():
    """Check Gmail integration status"""
    configured = bool(GMAIL_EMAIL and GMAIL_APP_PASSWORD)

    if configured:
        try:
            mail = get_imap_connection()
            mail.logout()
            return {"configured": True, "authenticated": True, "email": GMAIL_EMAIL}
        except Exception as e:
            return {"configured": True, "authenticated": False, "error": str(e)}

    return {
        "configured": False,
        "authenticated": False,
        "message": "Set GMAIL_EMAIL and GMAIL_APP_PASSWORD in .env"
    }


# Email Filters
@router.get("/filters", response_model=List[schemas.EmailFilter])
def list_filters(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.EmailFilter)
    if project_id:
        query = query.filter(models.EmailFilter.project_id == project_id)
    return query.all()


@router.post("/filters", response_model=schemas.EmailFilter)
def create_filter(filter: schemas.EmailFilterCreate, db: Session = Depends(get_db)):
    db_filter = models.EmailFilter(**filter.model_dump())
    db.add(db_filter)
    db.commit()
    db.refresh(db_filter)
    return db_filter


@router.delete("/filters/{filter_id}")
def delete_filter(filter_id: int, db: Session = Depends(get_db)):
    filter = db.query(models.EmailFilter).filter(models.EmailFilter.id == filter_id).first()
    if not filter:
        raise HTTPException(status_code=404, detail="Filter not found")
    db.delete(filter)
    db.commit()
    return {"message": "Filter deleted"}


def matches_filter(f, subject: str, body: str, sender: str) -> bool:
    """Check if an email matches a filter's criteria"""
    import fnmatch

    # Extract sender email
    sender_lower = sender.lower()
    sender_email = sender_lower
    if "<" in sender_lower and ">" in sender_lower:
        sender_email = sender_lower.split("<")[1].split(">")[0]

    # Check keywords (must match if specified)
    keyword_match = True
    if f.keywords and f.keywords.strip():
        keywords = [k.strip().lower() for k in f.keywords.split(",") if k.strip()]
        if keywords:
            keyword_match = any(k in subject.lower() or k in body.lower() for k in keywords)

    # Check from addresses (must match if specified)
    address_match = True
    if f.from_addresses and f.from_addresses.strip():
        addrs = [a.strip().lower() for a in f.from_addresses.split(",") if a.strip()]
        if addrs:
            address_match = False
            for a in addrs:
                if "*" in a or "?" in a:
                    if fnmatch.fnmatch(sender_email, a):
                        address_match = True
                        break
                elif a in sender_lower:
                    address_match = True
                    break

    # Both must match (if specified)
    has_keywords = f.keywords and f.keywords.strip()
    has_addresses = f.from_addresses and f.from_addresses.strip()

    if has_keywords and has_addresses:
        return keyword_match and address_match
    elif has_keywords:
        return keyword_match
    elif has_addresses:
        return address_match
    else:
        return False  # No criteria = no match


@router.post("/sync")
def sync_emails(project_id: Optional[int] = None, max_emails: int = 50, db: Session = Depends(get_db)):
    """Sync emails - each filter is processed separately."""

    # Get filters
    query = db.query(models.EmailFilter).filter(models.EmailFilter.is_active == True)
    if project_id:
        query = query.filter(models.EmailFilter.project_id == project_id)
    filters = query.all()

    if not filters:
        return {"message": "No active filters", "synced": 0}

    # Get all projects for AI assignment
    all_projects = db.query(models.Project).all()

    try:
        mail = get_imap_connection()
        mail.select("INBOX")

        synced = 0
        ai_assigned = 0
        tasks_created = 0
        since_date = "01-Feb-2026"
        processed_msg_ids = set()
        filter_results = []

        # Process each filter separately
        for f in filters:
            filter_synced = 0
            filter_tasks = 0

            # Build search terms for this filter only
            search_terms = []
            if f.keywords:
                for kw in f.keywords.split(","):
                    kw = kw.strip()
                    if kw:
                        search_terms.append(("SUBJECT", kw))
                        search_terms.append(("BODY", kw))
            if f.from_addresses:
                for addr in f.from_addresses.split(","):
                    addr = addr.strip()
                    if addr:
                        if addr.startswith("*@"):
                            search_terms.append(("FROM", addr[2:]))
                        elif "*" not in addr:
                            search_terms.append(("FROM", addr))

            # Search for emails matching this filter
            email_ids = set()
            for search_type, term in search_terms[:5]:
                try:
                    if search_type == "FROM":
                        _, data = mail.search(None, f'(FROM "{term}" SINCE {since_date})')
                    elif search_type == "BODY":
                        _, data = mail.search(None, f'(BODY "{term}" SINCE {since_date})')
                    else:
                        _, data = mail.search(None, f'(SUBJECT "{term}" SINCE {since_date})')
                    ids = data[0].split()
                    email_ids.update(ids[-max_emails:])
                except:
                    continue

            # Fetch and process emails for this filter
            for email_id in list(email_ids)[:max_emails]:
                try:
                    _, data = mail.fetch(email_id, "(RFC822)")
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    msg_id = msg.get("Message-ID", str(email_id))

                    # Skip if already processed by another filter or already in DB
                    if msg_id in processed_msg_ids:
                        continue
                    existing = db.query(models.Email).filter(models.Email.gmail_id == msg_id).first()
                    if existing:
                        processed_msg_ids.add(msg_id)
                        continue

                    subject = decode_mime_header(msg.get("Subject", ""))
                    sender = decode_mime_header(msg.get("From", ""))
                    body = get_email_body(msg)

                    # Check if sender is blocked
                    sender_email = sender.lower()
                    if "<" in sender and ">" in sender:
                        sender_email = sender.split("<")[1].split(">")[0].strip().lower()

                    if f.blocked_addresses:
                        blocked_list = [a.strip().lower() for a in f.blocked_addresses.split(",") if a.strip()]
                        if sender_email in blocked_list:
                            continue

                    # Verify this email actually matches the filter criteria
                    if not matches_filter(f, subject, body, sender):
                        continue

                    # Determine project
                    target_project_id = f.project_id
                    if not target_project_id:
                        # AI assigns project
                        target_project_id = assign_project_with_ai(subject, body, sender, all_projects)
                        if target_project_id:
                            ai_assigned += 1

                    # Check if email already exists before inserting
                    existing_check = db.query(models.Email.id).filter(
                        models.Email.gmail_id == msg_id
                    ).first()
                    if existing_check:
                        processed_msg_ids.add(msg_id)
                        continue

                    # Save email
                    db_email = models.Email(
                        gmail_id=msg_id,
                        project_id=target_project_id,
                        subject=subject[:500],
                        sender=sender[:255],
                        snippet=body[:500],
                        body=body,
                        received_at=datetime.now(NZT)
                    )
                    db.add(db_email)
                    db.commit()  # Commit each email immediately
                    processed_msg_ids.add(msg_id)
                    synced += 1
                    filter_synced += 1

                    # Extract tasks from email using AI
                    if target_project_id:
                        new_tasks = extract_tasks_from_email(subject, body, sender, target_project_id, db)
                        tasks_created += new_tasks
                        filter_tasks += new_tasks

                except Exception as e:
                    continue

            # Track results per filter
            if filter_synced > 0:
                filter_results.append({
                    "filter": f.name,
                    "emails": filter_synced,
                    "tasks": filter_tasks
                })

        mail.logout()

        msg = f"Synced {synced} emails"
        if ai_assigned:
            msg += f" ({ai_assigned} assigned by AI)"
        if tasks_created:
            msg += f", created {tasks_created} tasks"

        return {
            "message": msg,
            "synced": synced,
            "ai_assigned": ai_assigned,
            "tasks_created": tasks_created,
            "filters": filter_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emails/cleanup-old")
def cleanup_old_emails(db: Session = Depends(get_db)):
    """Delete emails older than Feb 2026"""
    cutoff = datetime(2026, 2, 1)
    old_emails = db.query(models.Email).filter(models.Email.received_at < cutoff).all()
    count = len(old_emails)
    for email in old_emails:
        db.delete(email)
    db.commit()
    return {"message": f"Deleted {count} emails older than Feb 2026"}


@router.get("/emails", response_model=List[schemas.Email])
def list_emails(project_id: Optional[int] = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(models.Email)
    if project_id:
        query = query.filter(models.Email.project_id == project_id)
    return query.order_by(models.Email.received_at.desc()).limit(limit).all()


@router.delete("/emails/{email_id}")
def delete_email(email_id: int, block_sender: bool = False, db: Session = Depends(get_db)):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email_obj:
        raise HTTPException(status_code=404, detail="Email not found")

    blocked_address = None
    if block_sender and email_obj.sender:
        # Extract email address from sender string like "Name <email@example.com>"
        sender = email_obj.sender
        if "<" in sender and ">" in sender:
            blocked_address = sender.split("<")[1].split(">")[0].strip().lower()
        else:
            blocked_address = sender.strip().lower()

        # Add to blocked list on all filters
        filters = db.query(models.EmailFilter).filter(models.EmailFilter.is_active == True).all()
        for f in filters:
            existing = f.blocked_addresses or ""
            blocked_list = [a.strip().lower() for a in existing.split(",") if a.strip()]
            if blocked_address not in blocked_list:
                blocked_list.append(blocked_address)
                f.blocked_addresses = ", ".join(blocked_list)

    db.delete(email_obj)
    db.commit()
    return {"message": "Email deleted", "blocked": blocked_address}


# Calendar - extract from email invites
@router.post("/sync-calendar")
def sync_calendar(db: Session = Depends(get_db)):
    """Sync calendar events from email invites (.ics attachments)"""
    try:
        mail = get_imap_connection()
        mail.select("INBOX")

        # Search for calendar invites from last 3 weeks
        from datetime import timedelta
        three_weeks_ago = datetime.now() - timedelta(weeks=3)
        since_date = three_weeks_ago.strftime("%d-%b-%Y")
        # Search all emails from last 3 weeks - we'll filter for calendar content
        _, data = mail.search(None, f'SINCE {since_date}')

        synced = 0
        email_ids = data[0].split()  # All emails in range

        for email_id in email_ids:
            try:
                _, data = mail.fetch(email_id, "(RFC822)")
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Look for .ics attachments or text/calendar parts
                for part in msg.walk():
                    content_type = part.get_content_type()

                    if content_type == "text/calendar" or (part.get_filename() and part.get_filename().endswith(".ics")):
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                ics_content = payload.decode('utf-8', errors='ignore')
                                event = parse_ics_event(ics_content)

                                if event and event.get("uid"):
                                    # Check if already exists
                                    existing = db.query(models.CalendarEvent).filter(
                                        models.CalendarEvent.google_event_id == event["uid"]
                                    ).first()

                                    if not existing:
                                        try:
                                            db_event = models.CalendarEvent(
                                                google_event_id=event["uid"],
                                                title=event.get("summary", "No Title"),
                                                description=event.get("description"),
                                                location=event.get("location"),
                                                start_time=event.get("dtstart"),
                                                end_time=event.get("dtend"),
                                                attendees=json.dumps(event.get("attendees", [])),
                                                meeting_link=event.get("url")
                                            )
                                            db.add(db_event)
                                            db.flush()  # Flush to catch duplicates early
                                            synced += 1
                                        except:
                                            db.rollback()  # Rollback on duplicate
                                            continue
                        except:
                            continue
            except:
                continue

        db.commit()
        mail.logout()
        return {"message": f"Synced {synced} calendar events from email invites", "synced": synced}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_ics_datetime(value: str, tzid: str = None) -> datetime:
    """Parse ICS datetime and convert to NZT"""
    try:
        # Remove any extra characters
        value = value.strip()

        # Handle UTC time (ends with Z)
        if value.endswith("Z"):
            value = value[:-1]
            if "T" in value:
                dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
            else:
                dt = datetime.strptime(value, "%Y%m%d")
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(NZT)

        # Parse the datetime
        if "T" in value:
            dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
        else:
            dt = datetime.strptime(value, "%Y%m%d")

        # If timezone specified, convert from that
        if tzid:
            try:
                tz = ZoneInfo(tzid)
                dt = dt.replace(tzinfo=tz)
                return dt.astimezone(NZT)
            except:
                pass

        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(NZT)
    except:
        return None


def parse_ics_event(ics_content: str) -> dict:
    """Parse a simple ICS file and extract event details"""
    event = {}
    lines = ics_content.replace("\r\n ", "").replace("\r\n\t", "").split("\n")

    in_event = False
    for line in lines:
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
        elif line == "END:VEVENT":
            break
        elif in_event and ":" in line:
            full_key, _, value = line.partition(":")
            # Handle properties with parameters like DTSTART;TZID=America/New_York:value
            parts = full_key.split(";")
            key = parts[0]
            tzid = None
            for p in parts[1:]:
                if p.startswith("TZID="):
                    tzid = p[5:]

            if key == "UID":
                event["uid"] = value
            elif key == "SUMMARY":
                event["summary"] = value
            elif key == "DESCRIPTION":
                event["description"] = value[:1000]
            elif key == "LOCATION":
                event["location"] = value
            elif key == "DTSTART":
                dt = parse_ics_datetime(value, tzid)
                if dt:
                    event["dtstart"] = dt
            elif key == "DTEND":
                dt = parse_ics_datetime(value, tzid)
                if dt:
                    event["dtend"] = dt
            elif key == "URL":
                event["url"] = value
            elif key == "ATTENDEE":
                if "attendees" not in event:
                    event["attendees"] = []
                # Extract email from mailto:email or CN=name
                if "mailto:" in value.lower():
                    email_addr = value.lower().split("mailto:")[-1].split(";")[0]
                    event["attendees"].append(email_addr)

    return event


@router.get("/calendar", response_model=List[schemas.CalendarEvent])
def list_calendar_events(db: Session = Depends(get_db)):
    return db.query(models.CalendarEvent).order_by(models.CalendarEvent.start_time).all()
