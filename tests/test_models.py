from datetime import datetime
from chronos.models.models import User, App, AppSession, BrowserTab, Task, TaskReminder, FocusSession, ProductivityGoal, DailyStat


class TestModels:
    def test_create_user(self, db_session):
        user = User(name="test_user", settings={"theme": "dark"})
        db_session.add(user)
        db_session.commit()
        assert user.id is not None
        assert user.name == "test_user"

    def test_create_app(self, db_session):
        app = App(app_name="vscode.exe", display_name="VSCode", category="development")
        db_session.add(app)
        db_session.commit()
        assert app.id is not None
        assert app.app_name == "vscode.exe"

    def test_create_app_session(self, db_session):
        app = App(app_name="test_app", display_name="Test App")
        db_session.add(app)
        db_session.commit()

        session = AppSession(
            app_id=app.id,
            start_time=datetime.now(),
            duration_seconds=300,
            is_active=False
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.app_id == app.id

    def test_create_browser_tab(self, db_session):
        app = App(app_name="chrome.exe", display_name="Chrome")
        db_session.add(app)
        db_session.commit()

        app_session = AppSession(
            app_id=app.id,
            start_time=datetime.now(),
            duration_seconds=120,
            is_active=True
        )
        db_session.add(app_session)
        db_session.commit()

        tab = BrowserTab(
            session_id=app_session.id,
            browser_name="chrome",
            tab_title="Test Page",
            tab_url="https://example.com",
            domain="example.com"
        )
        db_session.add(tab)
        db_session.commit()

        assert tab.id is not None
        assert tab.domain == "example.com"

    def test_create_task(self, db_session, user):
        task = Task(
            user_id=user.id,
            title="Test task",
            status="pending",
            priority="high"
        )
        db_session.add(task)
        db_session.commit()

        assert task.id is not None
        assert task.title == "Test task"
        assert task.user_id == user.id

    def test_create_task_reminder(self, db_session, user):
        task = Task(user_id=user.id, title="Reminder task")
        db_session.add(task)
        db_session.commit()

        reminder = TaskReminder(
            task_id=task.id,
            reminder_time=datetime.now()
        )
        db_session.add(reminder)
        db_session.commit()

        assert reminder.id is not None
        assert reminder.task_id == task.id

    def test_create_focus_session(self, db_session):
        fs = FocusSession(
            start_time=datetime.now(),
            duration_minutes=90,
            focus_task="Deep work",
            blocked_apps='["slack","discord"]',
            interruptions_count=2
        )
        db_session.add(fs)
        db_session.commit()

        assert fs.id is not None
        assert fs.duration_minutes == 90

    def test_create_productivity_goal(self, db_session, user):
        goal = ProductivityGoal(
            user_id=user.id,
            app_name="chrome",
            daily_limit_minutes=120,
            alert_threshold_percent=80
        )
        db_session.add(goal)
        db_session.commit()

        assert goal.id is not None
        assert goal.daily_limit_minutes == 120

    def test_create_daily_stat(self, db_session, user):
        from datetime import date
        stat = DailyStat(
            user_id=user.id,
            date=date.today(),
            total_screen_time_seconds=28800,
            focus_time_seconds=14400,
            tasks_completed=5,
            productivity_score=75.0
        )
        db_session.add(stat)
        db_session.commit()

        assert stat.id is not None
        assert stat.productivity_score == 75.0
