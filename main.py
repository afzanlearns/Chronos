"""Chronos - Main entry point for the application"""
import sys
import logging
from pathlib import Path

from chronos.db import init_db, get_session, ensure_default_user
from chronos.monitoring.window_tracker import WindowTracker
from chronos.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Chronos...")

    engine = init_db()
    session = get_session(engine)
    user = ensure_default_user(session)

    logger.info(f"User: {user.name} (ID: {user.id})")

    tracker = WindowTracker(session)
    tracker.start_tracking()

    try:
        from chronos.api.routes import create_app
        app = create_app(session)
        logger.info(f"Chronos API running on port {settings.FLASK_PORT}")
        app.run(host='0.0.0.0', port=settings.FLASK_PORT, debug=settings.FLASK_DEBUG)
    except KeyboardInterrupt:
        logger.info("Shutting down Chronos...")
        tracker.stop_tracking()
    finally:
        session.close()


if __name__ == '__main__':
    main()
