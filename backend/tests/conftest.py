import os
import tempfile

os.environ.setdefault("DB_TYPE", "sqlite")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="tenet-test-"), "test.db")
os.environ.setdefault("FLASK_DEBUG", "0")

import pytest

from database.config import Base, engine, SessionLocal
from database import models  # noqa: F401 - registers all SQLAlchemy models


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
