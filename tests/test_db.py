from pathlib import Path
from chronos.db import init_db, get_session, ensure_default_user, DB_PATH, CONFIG_PATH


class TestDatabase:
    def test_db_path(self):
        assert DB_PATH == Path.home() / ".chronos" / "chronos.db"
        assert CONFIG_PATH == Path.home() / ".chronos" / "config.yml"

    def test_init_db(self):
        engine = init_db()
        assert engine is not None

    def test_get_session(self):
        session = get_session()
        assert session is not None
        session.close()

    def test_ensure_default_user(self, db_session):
        user = ensure_default_user(db_session)
        assert user.name == "default"
        assert user.id is not None
