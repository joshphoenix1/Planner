from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Association tables
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE")),
    Column("label_id", Integer, ForeignKey("labels.id", ondelete="CASCADE")),
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    github_url = Column(String(500))
    github_repo = Column(String(255))  # owner/repo format
    color = Column(String(7), default="#6366f1")  # hex color
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    epics = relationship("Epic", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")


class Epic(Base):
    __tablename__ = "epics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#8b5cf6")
    status = Column(String(50), default="open")  # open, in_progress, done
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="epics")
    tasks = relationship("Task", back_populates="epic")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    goal = Column(Text)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    status = Column(String(50), default="planned")  # planned, active, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="sprints")
    tasks = relationship("Task", back_populates="sprint")


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), default="#6b7280")

    tasks = relationship("Task", secondary=task_labels, back_populates="labels")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    epic_id = Column(Integer, ForeignKey("epics.id", ondelete="SET NULL"), nullable=True)
    sprint_id = Column(Integer, ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="todo")  # todo, in_progress, in_review, done
    priority = Column(String(20), default="medium")  # low, medium, high, urgent

    due_date = Column(DateTime(timezone=True))
    estimated_hours = Column(Float)
    logged_hours = Column(Float, default=0)

    order = Column(Integer, default=0)  # for drag-drop ordering

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    epic = relationship("Epic", back_populates="tasks")
    sprint = relationship("Sprint", back_populates="tasks")
    labels = relationship("Label", secondary=task_labels, back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    task = relationship("Task", back_populates="comments")


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    hours = Column(Float, nullable=False)
    description = Column(Text)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="time_entries")


class EmailFilter(Base):
    __tablename__ = "email_filters"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)  # null = all projects
    name = Column(String(255), nullable=False)
    keywords = Column(Text)  # comma-separated keywords
    from_addresses = Column(Text)  # comma-separated email addresses
    blocked_addresses = Column(Text)  # comma-separated blocked email addresses
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    gmail_id = Column(String(255), unique=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    thread_id = Column(String(255))
    subject = Column(String(500))
    sender = Column(String(255))
    snippet = Column(Text)
    body = Column(Text)
    received_at = Column(DateTime(timezone=True))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    google_event_id = Column(String(255), unique=True, nullable=False)
    calendar_id = Column(String(255))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500))
    description = Column(Text)
    location = Column(String(500))
    start_time = Column(String(50))  # ISO format
    end_time = Column(String(50))
    all_day = Column(Boolean, default=False)
    attendees = Column(Text)  # JSON array of emails
    meeting_link = Column(String(500))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")


class WhatsAppGroup(Base):
    __tablename__ = "whatsapp_groups"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(String(255), nullable=False)  # WhatsApp group ID
    group_name = Column(String(255), nullable=False)
    keywords = Column(Text)  # comma-separated keywords to filter
    auto_create_tasks = Column(Boolean, default=True)  # auto-create tasks from TASK: messages
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")
    messages = relationship("WhatsAppMessage", back_populates="group_mapping", cascade="all, delete-orphan")


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, index=True)
    group_mapping_id = Column(Integer, ForeignKey("whatsapp_groups.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(255))
    content = Column(Text)
    message_type = Column(String(50), default="text")  # text, note, task, image, etc.
    wa_message_id = Column(String(255))  # Original WhatsApp message ID
    received_at = Column(DateTime(timezone=True))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    group_mapping = relationship("WhatsAppGroup", back_populates="messages")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100))  # gmail, calendar, whatsapp, ai, etc.
    error_type = Column(String(255))
    message = Column(Text)
    stack_trace = Column(Text)
    ai_suggestion = Column(Text)  # AI-generated fix suggestion
    status = Column(String(50), default="new")  # new, reviewing, fixed, ignored
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
