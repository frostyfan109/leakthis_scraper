import pytest
import os
from .mock_filesystem import file_mocker

DB_PATH = "app.db"

""" Mocking should always be enabled on the database. """
@pytest.fixture
def mock_db(file_mocker):
    import db
    if getattr(db, "_MOCK_INJECTED", False): return
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    # The sqlite engine does not directly connect to the DB via `open` on the same thread.
    # Not sure exactly how it works, but it can't be mocked directly.
    db._MOCK_INJECTED = True
    (_, tmp_path) = file_mocker.create_tmp_file(DB_PATH)
    db.DB_URI = db.DB_URI.replace(DB_PATH, str(tmp_path))
    # print("b", db.DB_URI)
    db.engine = create_engine(db.DB_URI)
    db._SessionFactory = sessionmaker(bind=db.engine)
    db.persistent_session = db.session_factory()