import requests
import os
from bs4 import BeautifulSoup
from main import Scraper
from .mocks import *

def test_scrape_static_assets(mock_scraper):
    mock_scraper.scrape_static_assets()
    with open(os.path.join(mock_scraper.static_dir, "logo.png"), "rb") as f:
        assert len(f.read()) > 0
    with open(os.path.join(mock_scraper.static_dir, "favicon.ico"), "rb") as f:
        assert len(f.read()) > 0

def test_parse_prefix(mock_scraper):
    pass