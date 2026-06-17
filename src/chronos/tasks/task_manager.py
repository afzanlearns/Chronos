import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from chronos.models.models import Task, TaskReminder
from chronos.notifications.notifier import NotificationService

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, db_session: Session, notifier=None):
        self.db = db_session
        self.notifier = notifier or NotificationService
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def add_task(self, user_id, title, due_date=None, estimated_minutes=None, recurring=None, description=None, priority='medium'):
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date,
            estimated_duration_minutes=estimated_minutes,
            recurring=recurring,
            priority=priority,
            status='pending'
        )
        self.db.add(task)
        self.db.commit()

        if due_date:
            reminder_time = due_date - timedelta(minutes=10)
            self.schedule_reminder(task.id, reminder_time)

        return task

    def schedule_reminder(self, task_id, reminder_time):
        reminder = TaskReminder(task_id=task_id, reminder_time=reminder_time)
        self.db.add(reminder)
        self.db.commit()

        self.scheduler.add_job(
            self._send_reminder,
            'date',
            run_date=reminder_time,
            args=[task_id],
            id=f"task_reminder_{task_id}"
        )

    def _send_reminder(self, task_id):
        task = self.db.get(Task, task_id)
        if task:
            self.notifier.notify(
                f"Reminder: {task.title}",
                "Chronos Tasks"
            )

    def complete_task(self, task_id):
        task = self.db.get(Task, task_id)
        if task:
            task.status = 'completed'
            task.completed_at = datetime.now()
            self.db.commit()
        return task

    def get_daily_summary(self, user_id, date=None):
        if not date:
            date = datetime.now().date()

        return self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.status != 'completed',
            Task.due_date <= date
        ).all()

    def get_all_tasks(self, user_id):
        return self.db.query(Task).filter_by(user_id=user_id).all()
