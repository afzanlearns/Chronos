import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy.orm import Session

from chronos.db import get_session, ensure_default_user
from chronos.models.models import Task, ProductivityGoal
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

    return app
