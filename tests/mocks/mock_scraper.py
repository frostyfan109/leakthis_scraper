import pytest
import yaml
import os
from .mock_requests import mock_requests, load_mock_request, MockRequest
from .mock_filesystem import file_mocker
from .mock_env import mock_env, MOCKING
from .mock_drive import mock_drive
from .mock_db import mock_db
from scraper import DEFAULT_CONFIG, Scraper
from commons import get_env_var

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
def mock_scraper(mock_requests, file_mocker, mock_scraper_env, mock_db, mock_drive, mock_env):
    file_mocker.mock_file(CONFIG_PATH, yaml.dump(DEFAULT_CONFIG))    
    file_mocker.mock_file(STATUS_PATH, "{}")
    file_mocker.mock_file(CREDENTIALS_PATH, yaml.dump(FAKE_CREDENTIALS))

    file_mocker.whitelist_file(NETRC_PATH)

    file_mocker.whitelist_directory(os.path.join(os.path.dirname(__file__), "requests", "mock_requests"), recursive=True)

    load_mock_request(mock_requests, MockRequest.Base.GET)
    load_mock_request(mock_requests, MockRequest.Login.POST)

    credentials = None
    if not MOCKING:
        credentials = {
            "username": get_env_var("TESTS_SCRAPER_USERNAME"),
            "password": get_env_var("TESTS_SCRAPER_PASSWORD")
        }
    scraper = Scraper(credentials)

    static_urls = scraper.resolve_static_asset_urls()
    load_mock_request(mock_requests, MockRequest.Static.Logo.GET(static_urls["logo_url"]))
    load_mock_request(mock_requests, MockRequest.Static.Favicon.GET(static_urls["favicon_url"]))

    file_mocker.mock_file(os.path.join(scraper.static_dir, "logo.png"))
    file_mocker.mock_file(os.path.join(scraper.static_dir, "favicon.ico"))

    load_mock_request(mock_requests, MockRequest.Section.HipHopLeaks.GET(
        scraper.resolve_section_url("hip-hop-leaks")
    ))
    for mock in MockRequest.SectionPosts.HipHopLeaks:
        load_mock_request(mock_requests, mock)
    
    for mock in MockRequest.Static.Stylesheets:
        load_mock_request(mock_requests, mock)

    return scraper
