import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy.orm import Session
from sqlalchemy import func

from chronos.db import get_session, ensure_default_user
from chronos.models.models import Task, ProductivityGoal, FocusSession, BrowserActivity, AppSession, App
from chronos.analytics.analytics import AnalyticsEngine
from chronos.tasks.task_manager import TaskManager
from chronos.notifications.notifier import NotificationService

logger = logging.getLogger(__name__)


def create_app(db_session: Session = None):
    app = Flask(__name__)
    CORS(app)

    if db_session is None:
        db_session = get_session()

    user = ensure_default_user(db_session)
    analytics = AnalyticsEngine(db_session)
    task_manager = TaskManager(db_session, NotificationService)

    @app.route('/api/dashboard/today', methods=['GET'])
    def get_today_dashboard():
        user_id = request.args.get('user_id', user.id)

        stats = analytics.get_daily_stats(user_id)
        app_breakdown = analytics.get_app_breakdown(user_id)
        incomplete_tasks = task_manager.get_daily_summary(user_id)

        return jsonify({
            'stats': {
                'total_screen_time_minutes': (stats.total_screen_time_seconds or 0) / 60,
                'focus_time_minutes': (stats.focus_time_seconds or 0) / 60,
                'tasks_completed': stats.tasks_completed or 0,
                'productivity_score': stats.productivity_score or 0
            },
            'app_breakdown': app_breakdown,
            'incomplete_tasks': [
                {'id': t.id, 'title': t.title, 'due': t.due_date.isoformat() if t.due_date else None}
                for t in incomplete_tasks
            ]
        })

    @app.route('/api/dashboard/week', methods=['GET'])
    def get_week_dashboard():
        user_id = request.args.get('user_id', user.id)
        report = analytics.get_weekly_report(user_id)
        return jsonify(report)

    @app.route('/api/tasks', methods=['GET'])
    def get_tasks():
        user_id = request.args.get('user_id', user.id)
        tasks = task_manager.get_all_tasks(user_id)
        return jsonify([
            {
                'id': t.id,
                'title': t.title,
                'status': t.status,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'priority': t.priority
            }
            for t in tasks
        ])

    @app.route('/api/tasks', methods=['POST'])
    def create_task():
        data = request.json
        due_date = None
        if data.get('due_date'):
            due_date = datetime.fromisoformat(data['due_date'])

        task = task_manager.add_task(
            user_id=data.get('user_id', user.id),
            title=data['title'],
            due_date=due_date,
            estimated_minutes=data.get('estimated_minutes'),
            recurring=data.get('recurring'),
            description=data.get('description'),
            priority=data.get('priority', 'medium')
        )
        return jsonify({'id': task.id, 'title': task.title}), 201

    @app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
    def complete_task(task_id):
        task = task_manager.complete_task(task_id)
        if task:
            return jsonify({'status': 'completed'})
        return jsonify({'error': 'Task not found'}), 404

    @app.route('/api/goals', methods=['GET'])
    def get_goals():
        user_id = request.args.get('user_id', user.id)
        goals = db_session.query(ProductivityGoal).filter_by(user_id=user_id).all()
        return jsonify([
            {
                'id': g.id,
                'app_name': g.app_name,
                'daily_limit_minutes': g.daily_limit_minutes,
                'alert_threshold': g.alert_threshold_percent
            }
            for g in goals
        ])

    @app.route('/api/goals', methods=['POST'])
    def set_goal():
        data = request.json
        goal = ProductivityGoal(
            user_id=data.get('user_id', user.id),
            app_name=data['app_name'],
            daily_limit_minutes=data['daily_limit_minutes'],
            alert_threshold_percent=data.get('alert_threshold', 80)
        )
        db_session.add(goal)
        db_session.commit()
        return jsonify({'id': goal.id}), 201

    @app.route('/api/focus/start', methods=['POST'])
    def start_focus():
        data = request.json
        task_name = data.get('task_name', '')
        planned_duration = data.get('planned_duration', 25)
        blocked_apps = data.get('blocked_apps', '')
        blocked_urls = data.get('blocked_urls', '')

        focus_session = FocusSession(
            start_time=datetime.now(),
            duration_minutes=planned_duration,
            focus_task=task_name,
            blocked_apps=blocked_apps,
            blocked_urls=blocked_urls,
            status='active'
        )
        db_session.add(focus_session)
        db_session.commit()

        return jsonify({
            'session_id': focus_session.id,
            'message': 'Focus session started'
        }), 201

    @app.route('/api/focus/stop/<int:session_id>', methods=['POST'])
    def stop_focus(session_id):
        focus_session = db_session.query(FocusSession).filter_by(id=session_id).first()
        if not focus_session:
            return jsonify({'error': 'Focus session not found'}), 404

        now = datetime.now()
        focus_session.end_time = now
        focus_session.status = 'completed'

        actual_duration_seconds = int((now - focus_session.start_time).total_seconds())
        focus_session.actual_duration = actual_duration_seconds

        planned_minutes = focus_session.duration_minutes or 1

        if focus_session.start_time:
            app_sessions = db_session.query(AppSession).filter(
                AppSession.start_time >= focus_session.start_time,
                AppSession.start_time <= now
            ).all()

            app_names = []
            seen_apps = set()
            for s in app_sessions:
                if s.app_id and s.app_id not in seen_apps:
                    seen_apps.add(s.app_id)
                    if s.app and s.app.display_name:
                        app_names.append(s.app.display_name)

            interruptions = max(0, len(seen_apps) - 1)
            focus_session.interruptions_count = interruptions
            focus_session.app_switches = list(seen_apps) if seen_apps else []

        blocked_urls_list = []
        if focus_session.blocked_urls:
            blocked_urls_list = [u.strip() for u in focus_session.blocked_urls.split(',') if u.strip()]

        distractions = 0
        urls_hit = []
        if blocked_urls_list:
            browser_activities = db_session.query(BrowserActivity).filter(
                BrowserActivity.focus_session_id == session_id
            ).all()
            blocked_domains = set()
            for ba in browser_activities:
                for blocked in blocked_urls_list:
                    if blocked in ba.domain:
                        blocked_domains.add(ba.domain)
            distractions = len(blocked_domains)
            urls_hit = list(blocked_domains)

        focus_session.distractions_caught = distractions

        actual_minutes = actual_duration_seconds / 60
        time_ratio = min(1.0, actual_minutes / planned_minutes) if planned_minutes > 0 else 1
        base_score = int(time_ratio * 100)
        # Ensure minimum base of 50 if no distractions or interruptions
        if interruptions == 0 and distractions == 0:
            base_score = max(base_score, 50)
        score = max(0, min(100, base_score - (interruptions * 5) - (distractions * 3)))
        focus_session.focus_score = score

        db_session.commit()

        browser_data = db_session.query(BrowserActivity).filter(
            BrowserActivity.focus_session_id == session_id
        ).all()

        domain_stats = {}
        for bd in browser_data:
            if bd.domain not in domain_stats:
                domain_stats[bd.domain] = {'duration': 0, 'visits': 0}
            domain_stats[bd.domain]['duration'] += bd.duration or 0
            domain_stats[bd.domain]['visits'] += 1

        browser_activity = []
        for domain, stats in sorted(domain_stats.items(), key=lambda x: x[1]['duration'], reverse=True):
            d = stats['duration']
            browser_activity.append({
                'domain': domain,
                'duration_seconds': d,
                'duration_formatted': format_duration(d),
                'visits': stats['visits']
            })

        return jsonify({
            'message': 'Focus session ended',
            'analytics': {
                'task_name': focus_session.focus_task or '',
                'planned_duration': focus_session.duration_minutes or 0,
                'actual_duration_seconds': actual_duration_seconds,
                'actual_duration_formatted': format_duration(actual_duration_seconds),
                'focus_score': score,
                'interruptions': interruptions,
                'interruption_apps': list(seen_apps) if app_sessions else [],
                'distractions_caught': distractions,
                'blocked_urls_hit': urls_hit,
                'browser_activity': browser_activity
            }
        })

    @app.route('/api/browser/activity', methods=['POST'])
    def create_browser_activity():
        data = request.json
        url = data.get('url', '')
        title = data.get('title', '')
        domain = data.get('domain', '')
        timestamp_str = data.get('timestamp')

        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()

        active_focus = db_session.query(FocusSession).filter(
            FocusSession.status == 'active'
        ).first()
        focus_session_id = active_focus.id if active_focus else None

        # Look for an existing record for the same domain within the last 10 seconds
        recent = db_session.query(BrowserActivity).filter(
            BrowserActivity.user_id == user.id,
            BrowserActivity.domain == domain,
            BrowserActivity.url == url,
            BrowserActivity.timestamp >= timestamp - timedelta(seconds=10)
        ).order_by(BrowserActivity.timestamp.desc()).first()

        if recent:
            recent.duration = (recent.duration or 0) + 5
            recent.timestamp = timestamp
            recent.focus_session_id = focus_session_id or recent.focus_session_id
            db_session.commit()
            return jsonify({'id': recent.id, 'message': 'Activity updated'}), 200
        else:
            activity = BrowserActivity(
                user_id=user.id,
                domain=domain,
                url=url,
                title=title,
                duration=5,
                timestamp=timestamp,
                focus_session_id=focus_session_id
            )
            db_session.add(activity)
            db_session.commit()
            return jsonify({'id': activity.id, 'message': 'Activity recorded'}), 201

    return app


def format_duration(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"
    return f"{minutes}m {secs}s"
