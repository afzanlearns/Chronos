from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, JSON,
    ForeignKey, TIMESTAMP, Date, create_engine
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now)
    settings = Column(JSON, nullable=True)

    tasks = relationship("Task", back_populates="user")
    daily_stats = relationship("DailyStat", back_populates="user")
    goals = relationship("ProductivityGoal", back_populates="user")


class App(Base):
    __tablename__ = 'apps'

    id = Column(Integer, primary_key=True)
    app_name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    icon_path = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)

    sessions = relationship("AppSession", back_populates="app")


class AppSession(Base):
    __tablename__ = 'app_sessions'

    id = Column(Integer, primary_key=True)
    app_id = Column(Integer, ForeignKey('apps.id'), nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.now)

    app = relationship("App", back_populates="sessions")
    browser_tabs = relationship("BrowserTab", back_populates="session")


class BrowserTab(Base):
    __tablename__ = 'browser_tabs'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('app_sessions.id'), nullable=False)
    browser_name = Column(String, nullable=True)
    tab_title = Column(String, nullable=True)
    tab_url = Column(String, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    domain = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)

    session = relationship("AppSession", back_populates="browser_tabs")


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default='pending')
    scheduled_time = Column(TIMESTAMP, nullable=True)
    due_date = Column(TIMESTAMP, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_duration_seconds = Column(Integer, nullable=True)
    priority = Column(String, default='medium')
    recurring = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)
    completed_at = Column(TIMESTAMP, nullable=True)

    user = relationship("User", back_populates="tasks")
    reminders = relationship("TaskReminder", back_populates="task")


class TaskReminder(Base):
    __tablename__ = 'task_reminders'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    reminder_time = Column(TIMESTAMP, nullable=True)
    reminder_sent = Column(Boolean, default=False)

    task = relationship("Task", back_populates="reminders")


class FocusSession(Base):
    __tablename__ = 'focus_sessions'

    id = Column(Integer, primary_key=True)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    focus_task = Column(String, nullable=True)
    blocked_apps = Column(Text, nullable=True)
    blocked_urls = Column(Text, nullable=True)
    interruptions_count = Column(Integer, default=0)
    focus_score = Column(Integer, nullable=True)
    distractions_caught = Column(Integer, default=0)
    app_switches = Column(JSON, nullable=True)
    actual_duration = Column(Integer, nullable=True)
    status = Column(String, default='active')
    created_at = Column(TIMESTAMP, default=datetime.now)

    browser_activities = relationship("BrowserActivity", back_populates="focus_session")


class BrowserActivity(Base):
    __tablename__ = 'browser_activities'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    domain = Column(String, nullable=False)
    url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    duration = Column(Integer, default=0)
    timestamp = Column(TIMESTAMP, default=datetime.now)
    focus_session_id = Column(Integer, ForeignKey('focus_sessions.id'), nullable=True)

    user = relationship("User")
    focus_session = relationship("FocusSession", back_populates="browser_activities")


class ProductivityGoal(Base):
    __tablename__ = 'productivity_goals'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    app_name = Column(String, nullable=True)
    daily_limit_minutes = Column(Integer, nullable=True)
    alert_threshold_percent = Column(Integer, default=80)
    created_at = Column(TIMESTAMP, default=datetime.now)

    user = relationship("User", back_populates="goals")


class DailyStat(Base):
    __tablename__ = 'daily_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(Date, unique=True)
    total_screen_time_seconds = Column(Integer, nullable=True)
    focus_time_seconds = Column(Integer, nullable=True)
    interruptions_count = Column(Integer, nullable=True)
    tasks_completed = Column(Integer, nullable=True)
    productivity_score = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)

    user = relationship("User", back_populates="daily_stats")
