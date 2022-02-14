import pytest
import yaml
import os
from .mock_requests import mock_requests, load_mock_request, MockRequest
from .mock_filesystem import file_mocker
from .mock_env import mock_env
from .mock_drive import mock_drive
from scraper import DEFAULT_CONFIG, Scraper

NETRC_PATH = os.path.join(os.path.expanduser("~"), "_netrc")


# Env-determined names
CONFIG_PATH = "config_tmp.yaml"
STATUS_PATH = "status_tmp.json"
CREDENTIALS_PATH = "credentials_tmp.yaml"

FAKE_CREDENTIALS = {
        "username": "test",
        "password": "test"
}

base_url = Scraper.base_url

""" Fixtures used in the `mock_scraper` fixture """
@pytest.fixture
def mock_scraper_env(mock_env):
    mock_env("CONFIG_PATH", CONFIG_PATH)
    mock_env("STATUS_PATH", STATUS_PATH)
    mock_env("LEAKTHIS_CREDENTIALS_FILE", CREDENTIALS_PATH)
    mock_env("STATIC_DIRECTORY", "static_tmp")

"""
Setup mocking for all necessary components of the Scraper, i.e. mock:
- Scraper-related files
- Scraper-related requests
- Database
Notes:
- Fixtures used should already account for env-enabled mocking.
"""
@pytest.fixture
def mock_scraper(mock_requests, file_mocker, mock_scraper_env, mock_drive, mock_env):
    file_mocker.mock_file(CONFIG_PATH, yaml.dump(DEFAULT_CONFIG))    
    file_mocker.mock_file(STATUS_PATH, "{}")
    file_mocker.mock_file(CREDENTIALS_PATH, yaml.dump(FAKE_CREDENTIALS))

    file_mocker.whitelist_file(NETRC_PATH)

    mock_response_path = os.path.join(os.path.dirname(__file__), "requests", "mock_requests")
    for f_name in os.listdir(mock_response_path):
        file_mocker.whitelist_file(os.path.join(mock_response_path, f_name))

    load_mock_request(mock_requests, MockRequest.Base.GET)
    load_mock_request(mock_requests, MockRequest.Login.POST)

    scraper = Scraper()

    static_urls = scraper.resolve_static_asset_urls()
    load_mock_request(mock_requests, MockRequest.Static.Logo.GET(static_urls["logo_url"]))
    load_mock_request(mock_requests, MockRequest.Static.Favicon.GET(static_urls["favicon_url"]))

    file_mocker.mock_file(os.path.join(scraper.static_dir, "logo.png"))
    file_mocker.mock_file(os.path.join(scraper.static_dir, "favicon.ico"))

    return scraper
