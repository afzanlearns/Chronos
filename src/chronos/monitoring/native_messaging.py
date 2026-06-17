import json
import sys
import struct
import logging
from urllib.parse import urlparse
from datetime import datetime

from chronos.models.models import BrowserTab, AppSession

logger = logging.getLogger(__name__)


class NativeMessageHandler:

    @staticmethod
    def read_message():
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None
        message_length = struct.unpack('@I', raw_length)[0]
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        return json.loads(message)

    @staticmethod
    def handle_tab_message(data, db_session):
        session = db_session.query(AppSession)\
            .filter_by(is_active=True)\
            .order_by(AppSession.start_time.desc())\
            .first()

        if session:
            tab = BrowserTab(
                session_id=session.id,
                browser_name='chrome',
                tab_title=data.get('title'),
                tab_url=data.get('url'),
                domain=NativeMessageHandler._extract_domain(data.get('url', '')),
            )
            db_session.add(tab)
            db_session.commit()
            logger.debug(f"Tab recorded: {data.get('title')}")

    @staticmethod
    def _extract_domain(url):
        try:
            return urlparse(url).netloc
        except Exception:
            return ''
