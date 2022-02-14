import pytest
from dotenv import load_dotenv
from commons import get_env_var
from exceptions import MissingEnvironmentError

load_dotenv()

try:
    MOCKING = get_env_var("TESTS_MOCKING") == "true"
except MissingEnvironmentError:
    MOCKING = False

""" Mocking should always be enabled on the environment. """
@pytest.fixture
def mock_env(monkeypatch):
    def _mocker(name, val):
        monkeypatch.setenv(name, val)
    return _mocker

# @pytest.fixture
# def mock_env(monkeypatch):
#     def _mocker(name, val):
#         if MOCKING:
#             monkeypatch.setenv(name, val)
#         else: pass
#     return _mocker