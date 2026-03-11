from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Labels
class LabelBase(BaseModel):
    name: str
    color: str = "#6b7280"

class LabelCreate(LabelBase):
    pass

class Label(LabelBase):
    id: int
    class Config:
        from_attributes = True


# Comments
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    task_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# Time Entries
class TimeEntryBase(BaseModel):
    hours: float
    description: Optional[str] = None

class TimeEntryCreate(TimeEntryBase):
    pass

class TimeEntry(TimeEntryBase):
    id: int
    task_id: int
    logged_at: datetime
    class Config:
        from_attributes = True


# Tasks
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    epic_id: Optional[int] = None
    sprint_id: Optional[int] = None
    order: int = 0

class TaskCreate(TaskBase):
    project_id: int
    label_ids: list[int] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    epic_id: Optional[int] = None
    sprint_id: Optional[int] = None
    order: Optional[int] = None
    label_ids: Optional[list[int]] = None

class Task(TaskBase):
    id: int
    project_id: int
    logged_hours: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    labels: list[Label] = []
    comments: list[Comment] = []
    class Config:
        from_attributes = True


# Epics
class EpicBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#8b5cf6"
    status: str = "open"

class EpicCreate(EpicBase):
    project_id: int

class EpicUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None

class Epic(EpicBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# Sprints
class SprintBase(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "planned"

class SprintCreate(SprintBase):
    project_id: int

class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None

class Sprint(SprintBase):
    id: int
    project_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# Projects
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    github_url: Optional[str] = None
    github_repo: Optional[str] = None
    color: str = "#6366f1"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    github_url: Optional[str] = None
    github_repo: Optional[str] = None
    color: Optional[str] = None

class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ProjectWithStats(Project):
    task_count: int = 0
    completed_count: int = 0
    epic_count: int = 0
    sprint_count: int = 0


# GitHub
class GitHubRepo(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    updated_at: Optional[datetime] = None


# Email Filters
class EmailFilterBase(BaseModel):
    name: str
    keywords: Optional[str] = None  # comma-separated
    from_addresses: Optional[str] = None  # comma-separated
    blocked_addresses: Optional[str] = None  # comma-separated blocked senders
    is_active: bool = True

class EmailFilterCreate(EmailFilterBase):
    project_id: Optional[int] = None  # null = all projects (AI assigns)

class EmailFilter(EmailFilterBase):
    id: int
    project_id: Optional[int] = None
    created_at: datetime
    class Config:
        from_attributes = True


# Emails
class EmailBase(BaseModel):
    subject: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None

class Email(EmailBase):
    id: int
    gmail_id: str
    project_id: Optional[int] = None
    thread_id: Optional[str] = None
    body: Optional[str] = None
    received_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# Calendar Events
class CalendarEventBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: bool = False

class CalendarEvent(CalendarEventBase):
    id: int
    google_event_id: str
    calendar_id: Optional[str] = None
    project_id: Optional[int] = None
    attendees: Optional[str] = None  # JSON string
    meeting_link: Optional[str] = None
    synced_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# WhatsApp Groups
class WhatsAppGroupBase(BaseModel):
    group_id: str
    group_name: str
    keywords: Optional[str] = None
    auto_create_tasks: bool = True
    is_active: bool = True

class WhatsAppGroupCreate(WhatsAppGroupBase):
    project_id: int

class WhatsAppGroupUpdate(BaseModel):
    group_name: Optional[str] = None
    keywords: Optional[str] = None
    auto_create_tasks: Optional[bool] = None
    is_active: Optional[bool] = None

class WhatsAppGroup(WhatsAppGroupBase):
    id: int
    project_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# WhatsApp Messages
class WhatsAppMessageBase(BaseModel):
    sender: Optional[str] = None
    content: Optional[str] = None
    message_type: str = "text"

class WhatsAppMessageCreate(WhatsAppMessageBase):
    group_mapping_id: int

class WhatsAppMessage(WhatsAppMessageBase):
    id: int
    group_mapping_id: int
    wa_message_id: Optional[str] = None
    received_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# Error Logs
class ErrorLogBase(BaseModel):
    source: str
    error_type: Optional[str] = None
    message: str
    stack_trace: Optional[str] = None

class ErrorLogCreate(ErrorLogBase):
    pass

class ErrorLog(ErrorLogBase):
    id: int
    ai_suggestion: Optional[str] = None
    status: str = "new"
    created_at: datetime
    resolved_at: Optional[datetime] = None
    class Config:
        from_attributes = True
