import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chronos.models.models import Base
from chronos.db import ensure_default_user


@pytest.fixture
def db_session():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    ensure_default_user(session)
    yield session
    session.close()
    engine.dispose()
    try:
        os.unlink(db_path)
    except PermissionError:
        pass


@pytest.fixture
def user(db_session):
    from chronos.models.models import User
    return db_session.query(User).filter_by(name="default").first()
