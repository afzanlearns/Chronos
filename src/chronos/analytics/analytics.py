import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from chronos.models.models import AppSession, Task, DailyStat, App, BrowserActivity

logger = logging.getLogger(__name__)


def format_duration(seconds):
    if not seconds:
        return "0m"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        if secs > 0:
            return f"{hours}h {mins}m {secs}s"
        return f"{hours}h {mins}m"
    if secs > 0:
        return f"{minutes}m {secs}s"
    return f"{minutes}m"


class AnalyticsEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_daily_stats(self, user_id, date=None):
        if not date:
            date = datetime.now().date()

        cached = self.db.query(DailyStat).filter_by(
            user_id=user_id, date=date
        ).first()
        if cached:
            return cached

        sessions = self.db.query(AppSession).filter(
            func.date(AppSession.start_time) == date
        ).all()

        total_screen_time = sum(s.duration_seconds or 0 for s in sessions)

        focus_apps = ['VSCode', 'PyCharm', 'Sublime', 'IntelliJ']
        focus_time = sum(
            s.duration_seconds for s in sessions
            if s.app and any(app in (s.app.display_name or '') for app in focus_apps)
        ) if sessions else 0

        tasks_completed = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.status == 'completed',
            func.date(Task.completed_at) == date
        ).count()

        score = self._calculate_productivity_score(
            total_screen_time, focus_time, tasks_completed, sessions
        )

        stat = DailyStat(
            user_id=user_id,
            date=date,
            total_screen_time_seconds=int(total_screen_time),
            focus_time_seconds=int(focus_time),
            tasks_completed=tasks_completed,
            productivity_score=score
        )
        self.db.add(stat)
        self.db.commit()

        return stat

    def _calculate_productivity_score(self, screen_time, focus_time, tasks, sessions):
        focus_ratio = focus_time / screen_time if screen_time > 0 else 0

        app_count = len(set(s.app_id for s in sessions))
        diversity_score = min(1.0, app_count / 8)

        daily_balance = 1.0 if screen_time < 28800 else 0.7

        score = (
            (focus_ratio * 0.4) +
            (min(1.0, tasks / 8) * 0.3) +
            (diversity_score * 0.2) +
            (daily_balance * 0.1)
        ) * 100

        return min(100, max(0, score))

    def get_weekly_report(self, user_id):
        week_start = datetime.now() - timedelta(days=7)

        daily_stats = self.db.query(DailyStat).filter(
            DailyStat.user_id == user_id,
            DailyStat.date >= week_start.date()
        ).all()

        if not daily_stats:
            return {
                'total_screen_time': 0,
                'focus_time': 0,
                'tasks_completed': 0,
                'avg_daily_score': 0,
                'best_day': None,
                'worst_day': None,
            }

        return {
            'total_screen_time': sum(s.total_screen_time_seconds for s in daily_stats),
            'focus_time': sum(s.focus_time_seconds for s in daily_stats),
            'tasks_completed': sum(s.tasks_completed for s in daily_stats),
            'avg_daily_score': sum(s.productivity_score for s in daily_stats) / len(daily_stats),
            'best_day': max(daily_stats, key=lambda x: x.productivity_score).date.isoformat() if daily_stats else None,
            'worst_day': min(daily_stats, key=lambda x: x.productivity_score).date.isoformat() if daily_stats else None,
        }

    def get_app_breakdown(self, user_id, date=None):
        if not date:
            date = datetime.now().date()

        results = self.db.query(
            App.display_name,
            func.sum(AppSession.duration_seconds).label('total_seconds'),
            func.count(AppSession.id).label('session_count')
        ).join(AppSession, App.id == AppSession.app_id).filter(
            func.date(AppSession.start_time) == date
        ).group_by(App.id).order_by(
            func.sum(AppSession.duration_seconds).desc()
        ).all()

        return [
            {
                'app': r[0],
                'time_seconds': r[1] or 0,
                'time_minutes': (r[1] or 0) / 60,
                'sessions': r[2]
            }
            for r in results
        ]

    def get_daily_report_with_browser_data(self, user_id, date=None):
        if not date:
            date = datetime.now().date()

        app_usage = self.get_app_breakdown(user_id, date)

        start_dt = datetime.combine(date, datetime.min.time())
        end_dt = datetime.combine(date, datetime.max.time())

        browser_activities = self.db.query(BrowserActivity).filter(
            BrowserActivity.user_id == user_id,
            BrowserActivity.timestamp >= start_dt,
            BrowserActivity.timestamp <= end_dt
        ).all()

        domain_stats = {}
        total_browser_time = 0
        for ba in browser_activities:
            if ba.domain not in domain_stats:
                domain_stats[ba.domain] = {'duration': 0, 'visits': 0}
            domain_stats[ba.domain]['duration'] += ba.duration or 0
            domain_stats[ba.domain]['visits'] += 1
            total_browser_time += ba.duration or 0

        browser_breakdown = []
        for domain, stats in sorted(domain_stats.items(), key=lambda x: x[1]['duration'], reverse=True):
            pct = (stats['duration'] / total_browser_time * 100) if total_browser_time > 0 else 0
            browser_breakdown.append({
                'domain': domain,
                'duration_seconds': stats['duration'],
                'duration_formatted': format_duration(stats['duration']),
                'visits': stats['visits'],
                'percentage': round(pct, 1)
            })

        return {
            'app_usage': app_usage,
            'browser_breakdown': browser_breakdown,
            'total_browser_time_seconds': total_browser_time,
            'total_browser_time_formatted': format_duration(total_browser_time)
        }
