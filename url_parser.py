import requests
import logging
import re
from time import time
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from abc import ABC, abstractmethod
from commons import assert_is_ok

logger = logging.getLogger(__file__)
session = requests.Session()


class FileNotFoundError(Exception):
    def __init__(self, url):
        super().__init__(f"File not found at '{url}'.")
        self.url = url

class Netloc:
    def __init__(self, url):
        self.url = url
        self.netloc = urlsplit(url).netloc
        self.parse_netloc()

    def parse_netloc(self):
        split_netloc = self.netloc.split(".")
        subdomains = split_netloc[:-2]
        host_name = split_netloc[-2]
        domain_name = split_netloc[-1]

        self.subdomains = subdomains
        self.host_name = host_name
        self.domain_name = domain_name

class HostingService(ABC):
    @property
    @abstractmethod
    def base_url(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    @abstractmethod
    def parse_download_url(self, url):
        raise NotImplementedError

    @abstractmethod
    def parse_file_name(self, url):
        raise NotImplementedError

    def download(self, download_url):
        # Can override if necessary (i.e. requires setting headers/credentials to download)
        logger.info(f"Downloading '{download_url}'")
        t = time()
        res = session.get(download_url)
        assert_is_ok(res)
        # logger.info("Download took " + str(time() - t) + "s to complete.")
        return res.content

    def is_host_url(self, url):
        # Can override if necessary.
        # Netloc can contain subdomains (most prominently www) and many services may support urls that omit www.
        # So, the netloc should be cleaned of the subdomain so that it's just the host name.
        netloc = Netloc(url)
        host_netloc = Netloc(self.base_url)
        # Make sure that the host names and domain names are the same. The subdomains don't have to match.
        return (
            netloc.host_name == host_netloc.host_name and
            netloc.domain_name == host_netloc.domain_name
        )

class OnlyFilesBiz(HostingService):
    name = "OnlyFiles (Biz)"
    base_url = "https://www.onlyfiles.biz/"

    def parse_download_url(self, url):
        # It seems like onlyfiles simply appends the "type" query parameter to the end of the file id, but it's unclear.
        # To be safe, just scrape the download url.
        res = session.get(url)
        # assert_is_ok(res)
        soup = BeautifulSoup(res.content, "html.parser")

        # Same method used by OnlyFiles to check if file exists
        empt = soup.select_one("#name")
        if empt == None or empt.text == "":
            raise FileNotFoundError(url)

        return self.base_url + soup.select_one(".player").find("source")["src"]

    def parse_file_name(self, url):
        res = session.get(url)
        # assert_is_ok(res)
        # Same method used by OnlyFiles to check if file exists
        soup = BeautifulSoup(res.content, "html.parser")

        empt = soup.select_one("#name")
        if empt == None or empt.text == "":
            raise FileNotFoundError(url)
        return soup.find("meta", attrs={"name": "title"})["content"]

class OnlyFilesCC(HostingService):
    name = "OnlyFiles (CC)"
    base_url = "https://onlyfiles.cc/"

    def assert_exists(self, url, res):
        if res.status_code == 404:
            raise FileNotFoundError(url)

    def parse_download_url(self, url):
        res = session.get(url)
        self.assert_exists(url, res)
        soup = BeautifulSoup(res.content, "html.parser")
        # This doesn't need to be scraped, but due to the volatile nature of the site, this is most safe.
        return url + "/../" + soup.find("audio")["src"]

    def parse_file_name(self, url):
        res = session.get(url)
        self.assert_exists(url, res)
        soup = BeautifulSoup(res.content, "html.parser")
        return soup.select_one("#title").text


class DBREE(HostingService):
    name = "DBREE"
    base_url = "https://dbree.org/"

    def assert_exists(self, url, res):
        if urlsplit(res.url).path == "/index.html":
            raise FileNotFoundError(url)

    def parse_download_url(self, url):
        # DBREE download urls aren't static and the way they're generated is unclear.
        # Unless the way they're generated is discovered, scraping is necessary.
        res = session.get(url)
        assert_is_ok(res)
        self.assert_exists(url, res)
        soup = BeautifulSoup(res.content, "html.parser")
        # DBREE uses protocol=relative download urls
        return "https:" + soup.find("a", text="Download")["href"]

    def parse_file_name(self, url):
        res = session.get(url)
        assert_is_ok(res)
        self.assert_exists(url, res)
        soup = BeautifulSoup(res.content, "html.parser")
        # return soup.select_one("#detailsModalLabel").text
        pattern = r"Name: (.*)"
        return re.match(pattern, soup.find("li", text=re.compile(pattern)).text).group(1)

class AnonFiles(HostingService):
    name = "AnonFiles"
    base_url = "https://anonfiles.com/"

    def assert_exists(self, url, res):
        if res.status_code == 404:
            raise FileNotFoundError(url)

    def parse_download_url(self, url):
        # Unclear how AnonFiles generates cdn urls, so have to scrape it.
        res = session.get(url)
        self.assert_exists(url, res)
        soup = BeautifulSoup(res.content, "html.parser")
        return soup.select_one("#download-url")["href"]

    def parse_file_name(self, url):
        res = session.get(url)
        self.assert_exists(url, res)
        soup = BeautifulSoup(res.content, "html.parser")
        return soup.select_one(".top-wrapper").select_one("h1").text

Hosts = [OnlyFilesBiz(), OnlyFilesCC(), DBREE(), AnonFiles()]

class URLParser:
    def __init__(self):
        pass

    def get_hosting_service(self, url):
        for Host in Hosts:
            try:
                if Host.is_host_url(url):
                    return Host
            except:
                # Invalid URL. Skip parsing because nothing should match it.
                break
        # logger.debug(f"No service implementation is associated with '{url}'.")

    def parse_download_url(self, url):
        hosting_service = self.get_hosting_service(url)
        if hosting_service is not None:
            return hosting_service.parse_download_url(url)

    def download(self, url):
        hosting_service = self.get_hosting_service(url)
        if hosting_service is not None:
            try:
                file_name = hosting_service.parse_file_name(url)
                download_url = hosting_service.parse_download_url(url)
                stream = hosting_service.download(download_url)
                return {
                    "file_name": file_name,
                    "download_url": download_url,
                    "stream": stream
                }
            except FileNotFoundError as e:
                # File probably doesn't exist
                return {
                    "unknown": True
                }
            except Exception as e:
                raise e