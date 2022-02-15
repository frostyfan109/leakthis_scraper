import requests
import os
import sys
from bs4 import BeautifulSoup
from db import session_factory, Post, Prefix, File
from main import Scraper
from drive import get_file
from .mocks import *

def test_scrape_static_assets(mock_scraper):
    mock_scraper.scrape_static_assets()
    with open(os.path.join(mock_scraper.static_dir, "logo.png"), "rb") as f:
        assert len(f.read()) > 0
    with open(os.path.join(mock_scraper.static_dir, "favicon.ico"), "rb") as f:
        assert len(f.read()) > 0

def test_parse_section(mock_scraper):
    section_name = "hip-hop-leaks"
    posts = mock_scraper.scrape_posts(section_name, pages=1)
    session = session_factory()
    file_count = 0
    real_file_count = 0
    for post_id in posts:
        assert post_id is not None
        record = session.query(Post).filter_by(id=post_id).first()
        assert record is not None
        assert record.native_id.startswith(str(mock_scraper.LT_DB_VERSION))
        assert record.section_id == mock_scraper.get_section_id(section_name)
        files = record.get_files()
        file_count += files.count()
        real_file_count += files.filter((File.unknown == False) | (File.unknown == None)).count()
        for file in files:
            if not file.unknown:
                drive_file = get_file(file.drive_project_id, file.drive_id)
                drive_file.FetchContent()
                assert len(drive_file.content.read()) > 0

    # Could theoretically false positive during a live test if no posts on the first page have a prefix,
    # although this is very unlikely and a cause for concern in and of itself.
    assert session.query(Prefix).count() > 0
    assert file_count > 0
    assert real_file_count > 0

    if MOCKING:
        post = session.query(Post).filter_by(title="x1 NBA YoungBoy").first()
        assert post is not None
        assert post.native_id == mock_scraper.format_native_id(63087)
        assert post.url == scraper.base_url + "/threads/x1-nba-youngboy.63087/"
        assert post.prefixes == ["SNIPPET"]
        assert post.created_by == "HunchoSwipin"
        assert post.view_count == 324
        assert post.reply_count == 11
        assert "Year : 2019" in post.body
        assert "Year : 2019" in post.html
        assert post.pinned == False
        assert post.deleted == False

    session.close()

def test_parse_prefix(mock_scraper):
    pass