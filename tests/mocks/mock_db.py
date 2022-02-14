import pytest
import os
from .mock_filesystem import file_mocker

os.environ["MOCKING"]

DB_PATH = "app.db"

""" Mocking should always be enabled on the database. """
@pytest.fixture
def mock_db(file_mocker):
    file_mocker.mock_file(DB_PATH)