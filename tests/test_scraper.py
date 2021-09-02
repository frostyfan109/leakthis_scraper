from main import Scraper
import requests
from bs4 import BeautifulSoup

def test_parse_prefix():
    scraper = Scraper()
    # res = requests.get("https://leakth.is/forums/hip-hop-discussion.46/")
    # soup = BeautifulSoup(res.content, "html.parser")
    # prefix_tag = soup.select_one(".structItem--thread").select_one(".structItem-title").find("a", class_="labelLink")
    # scraper.parse_prefix(soup, prefix_tag)
