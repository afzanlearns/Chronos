from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from chronos.models.models import Base, User
from chronos.config import settings


DB_PATH = Path.home() / ".chronos" / "chronos.db"
CONFIG_PATH = Path.home() / ".chronos" / "config.yml"


def get_engine(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    return engine


def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)

    # Migration: add created_at to browser_activities if missing
    try:
        engine.execute("ALTER TABLE browser_activities ADD COLUMN created_at TIMESTAMP")
    except Exception:
        pass

    return engine


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def ensure_default_user(db_session: Session):
    user = db_session.query(User).filter_by(name="default").first()
    if not user:
        user = User(name="default", settings={})
        db_session.add(user)
        db_session.commit()
    return user
