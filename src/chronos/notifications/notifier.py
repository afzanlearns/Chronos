import threading
import logging

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def notify(title, message, timeout=5, urgency='normal'):
        try:
            from plyer import notification as plyer_notification
            notification_thread = threading.Thread(
                target=plyer_notification.notify,
                args=(title, message),
                kwargs={'timeout': timeout}
            )
            notification_thread.daemon = True
            notification_thread.start()
        except Exception as e:
            logger.warning(f"Notification failed: {e}")

    @staticmethod
    def notify_task_due(task_title):
        NotificationService.notify(
            "Task Reminder",
            f"{task_title}",
            timeout=10
        )

    @staticmethod
    def notify_limit_exceeded(app_name, minutes):
        NotificationService.notify(
            "App Limit Alert",
            f"You've spent {minutes} min on {app_name}",
            timeout=10,
            urgency='critical'
        )
