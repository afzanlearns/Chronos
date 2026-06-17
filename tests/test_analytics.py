from datetime import datetime, date
from chronos.analytics.analytics import AnalyticsEngine
from chronos.models.models import App, AppSession, Task, DailyStat


class TestAnalytics:
    def test_get_daily_stats_new(self, db_session, user):
        engine = AnalyticsEngine(db_session)
        stats = engine.get_daily_stats(user.id)
        assert stats is not None
        assert stats.user_id == user.id
        assert stats.productivity_score is not None

    def test_get_daily_stats_cached(self, db_session, user):
        from datetime import date
        stat = DailyStat(
            user_id=user.id,
            date=date.today(),
            total_screen_time_seconds=1000,
            focus_time_seconds=500,
            tasks_completed=3,
            productivity_score=60.0
        )
        db_session.add(stat)
        db_session.commit()

        engine = AnalyticsEngine(db_session)
        cached = engine.get_daily_stats(user.id)
        assert cached.id == stat.id
        assert cached.productivity_score == 60.0

    def test_get_weekly_report_empty(self, db_session, user):
        engine = AnalyticsEngine(db_session)
        report = engine.get_weekly_report(user.id)
        assert report['total_screen_time'] == 0
        assert report['avg_daily_score'] == 0

    def test_get_app_breakdown_empty(self, db_session, user):
        engine = AnalyticsEngine(db_session)
        breakdown = engine.get_app_breakdown(user.id)
        assert breakdown == []

    def test_productivity_score_calculation(self, db_session, user):
        app = App(app_name="vscode.exe", display_name="VSCode")
        db_session.add(app)
        db_session.commit()

        for _ in range(20):
            session = AppSession(
                app_id=app.id,
                start_time=datetime.now(),
                duration_seconds=300,
                is_active=False
            )
            db_session.add(session)
        db_session.commit()

        task = Task(user_id=user.id, title="Done task", status="completed")
        db_session.add(task)
        db_session.commit()

        engine = AnalyticsEngine(db_session)
        stats = engine.get_daily_stats(user.id)
        assert 0 <= stats.productivity_score <= 100
