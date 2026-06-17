from datetime import datetime, timedelta
from chronos.tasks.task_manager import TaskManager
from chronos.models.models import Task


class TestTaskManager:
    def test_add_task(self, db_session, user):
        manager = TaskManager(db_session)
        task = manager.add_task(
            user_id=user.id,
            title="Test task",
            priority="high"
        )
        assert task.id is not None
        assert task.title == "Test task"
        assert task.status == "pending"

    def test_complete_task(self, db_session, user):
        manager = TaskManager(db_session)
        task = manager.add_task(user_id=user.id, title="Complete me")
        completed = manager.complete_task(task.id)
        assert completed.status == "completed"
        assert completed.completed_at is not None

    def test_get_daily_summary(self, db_session, user):
        manager = TaskManager(db_session)
        manager.add_task(
            user_id=user.id,
            title="Overdue task",
            due_date=datetime.now() - timedelta(days=1)
        )
        manager.add_task(
            user_id=user.id,
            title="Future task",
            due_date=datetime.now() + timedelta(days=1)
        )

        summary = manager.get_daily_summary(user.id)
        titles = [t.title for t in summary]
        assert "Overdue task" in titles
        assert "Future task" not in titles

    def test_get_all_tasks(self, db_session, user):
        manager = TaskManager(db_session)
        manager.add_task(user_id=user.id, title="Task 1")
        manager.add_task(user_id=user.id, title="Task 2")

        tasks = manager.get_all_tasks(user.id)
        assert len(tasks) == 2
