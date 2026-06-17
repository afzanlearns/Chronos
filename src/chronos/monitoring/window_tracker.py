import time
import platform
import logging
from threading import Thread
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from chronos.models.models import App, AppSession, ProductivityGoal
from chronos.notifications.notifier import NotificationService

logger = logging.getLogger(__name__)


class WindowTracker:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.current_app = None
        self.session_start = None
        self.is_running = False
        self.os_type = platform.system()

    def start_tracking(self):
        self.is_running = True
        track_thread = Thread(target=self._track_loop, daemon=True)
        track_thread.start()
        logger.info("Window tracking started")

    def stop_tracking(self):
        self.is_running = False
        logger.info("Window tracking stopped")

    def _track_loop(self):
        while self.is_running:
            try:
                active_window = self._get_active_window()
                if active_window:
                    app_name = active_window
                    if app_name != self.current_app:
                        self._handle_app_switch(self.current_app, app_name)
                        self.current_app = app_name
                        self.session_start = datetime.now()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Tracking error: {e}")

    def _get_active_window(self):
        if self.os_type == "Windows":
            try:
                import pygetwindow as gw
                active = gw.getActiveWindow()
                return active.title if active else None
            except Exception:
                return None
        elif self.os_type == "Darwin":
            try:
                from PyObjCTools.AppHelper import runConsoleEventLoop
                from Cocoa import NSWorkspace
                workspace = NSWorkspace.sharedWorkspace()
                return workspace.activeApplication().get('NSApplicationName')
            except Exception:
                return None
        else:
            try:
                import pygetwindow as gw
                active = gw.getActiveWindow()
                return active.title if active else None
            except Exception:
                return None

    def _handle_app_switch(self, old_app, new_app):
        if old_app and self.session_start:
            duration = (datetime.now() - self.session_start).total_seconds()
            self._save_session(old_app, duration)
        self._ensure_app_exists(new_app)

    def _save_session(self, app_name, duration_seconds):
        app = self.db.query(App).filter_by(app_name=app_name).first()
        if app:
            session = AppSession(
                app_id=app.id,
                start_time=self.session_start,
                end_time=datetime.now(),
                duration_seconds=int(duration_seconds),
                is_active=False
            )
            self.db.add(session)
            self.db.commit()
            self._check_limits(app.id)

    def _ensure_app_exists(self, app_name):
        app = self.db.query(App).filter_by(app_name=app_name).first()
        if not app:
            app = App(app_name=app_name, display_name=app_name)
            self.db.add(app)
            self.db.commit()

    def _check_limits(self, app_id):
        goal = self.db.query(ProductivityGoal).filter_by(app_name=app_id).first()
        if goal:
            today = datetime.now().date()
            total_today = self.db.query(func.sum(AppSession.duration_seconds))\
                .filter(AppSession.app_id == app_id)\
                .filter(func.date(AppSession.start_time) == today)\
                .scalar() or 0

            if total_today > goal.daily_limit_minutes * 60:
                threshold = (goal.daily_limit_minutes * 60) * (goal.alert_threshold_percent / 100)
                if total_today >= threshold:
                    NotificationService.notify(
                        f"You've spent {int(total_today/60)} min on this app",
                        "Chronos"
                    )
