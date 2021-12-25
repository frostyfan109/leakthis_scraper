import requests
import logging
import re
import traceback
import json
import inspect
from functools import wraps
from time import time
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from abc import ABC, abstractmethod
from exceptions import FileNotFoundError, UnknownHostingServiceError, AuthenticationError
from commons import assert_is_ok, get_mimetype
from webdriver import create_chrome_driver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__file__)
session = requests.Session()

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

    def upload_files(self, files):
        return []

    def parse_url(self, url):
        file_name = self.parse_file_name(url)
        download_url = self.parse_download_url(url)
        return (
            file_name,
            download_url
        )

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

def api_request(method):
    def _impl(self, *args, **kwargs):
        if self.api_token is None:
            self.login()
        def call_with_auth(attempt=1):
            try:
                return method(self, *args, **kwargs)
            except AuthenticationError as e:
                logger.warning(e)
                logger.error(f"GoFile API credentials invalidated (attempt {attempt}). Retrying...")
                if attempt > 5:
                    raise e
                return call_with_auth(attempt + 1)
        return call_with_auth()

    return _impl
        
        
class GoFile(HostingService):
    name = "GoFile"
    base_url = "https://gofile.io/"
    api_url = "https://api.gofile.io/"

    def __init__(self):
        self.api_state = {
            "api_token": None,
            "root_folder": None
        }

    @property
    def api_token(self):
        return self.api_state["api_token"]

    @api_token.setter
    def api_token(self, value):
        self.api_state["api_token"] = value

    @property
    def root_folder(self):
        return self.api_state["root_folder"]
    
    @root_folder.setter
    def root_folder(self, value):
        self.api_state["root_folder"] = value

    @staticmethod
    def get_server_url(server):
        return f"https://{server}.gofile.io/"

    def assert_ok(self, data):
        if data["status"] != "ok":
            curframe = inspect.currentframe()
            frames = inspect.getouterframes(curframe, 2)
            method_name = frames[1][3]
            raise AuthenticationError(f"Authenciation failed with GoFile. Response: '{json.dumps(data)}'. Method: '{method_name}'")

    def make_api_request(self, *args, **kwargs):
        res = session.request(*args, **kwargs)
        data = res.json()
        self.assert_ok(data)
        return data

    def login(self):
        data = self.make_api_request("get", self.api_url + "createAccount")

        self.api_token = data["data"]["token"]

        session.cookies.set("accountToken", self.api_token)

        data = self.make_api_request("get", self.api_url + "getAccountDetails?token=" + self.api_token)

        self.root_folder = data["data"]["rootFolder"]

    @api_request
    def get_download_data(self, url):
        content_id = urlsplit(url).path.split("/")[-1]
        data = self.make_api_request("get", self.api_url + f"getContent?contentId={content_id}&token={self.api_token}&websiteToken=websiteToken")
        return data["data"]

    def parse_download_url(self, url):
        data = self.get_download_data(url)
        return [file["link"] for file in data["contents"].values()]

    def parse_file_name(self, url):
        data = self.get_download_data(url)
        return [file["name"] for file in data["contents"].values()]


    @api_request
    def get_server(self):
        data = self.make_api_request("get", self.api_url + "getServer")
        return data["data"]["server"]
        

    @api_request
    def create_folder(self):
        data = {
            "token": self.api_token,
            "parentFolderId": self.root_folder
        }
        data = self.make_api_request("put", self.api_url + "createFolder", data=data)

        folder_id =  data["data"]["id"]

        return folder_id
        

    @api_request
    def set_folder_option(self, folder_id, option, value):
        data = {
            "token": self.api_token,
            "folderId": folder_id,
            "option": option,
            "value": value
        }
        self.make_api_request("put", self.api_url + "setFolderOption", data=data)

    @api_request
    def share_folder(self, folder_id):
        self.make_api_request("get", self.api_url + f"shareFolder?token={self.api_token}&folderId={folder_id}")

    def create_public_folder(self):
        folder_id = self.create_folder()
        self.set_folder_option(folder_id, "public", "true")
        self.share_folder(folder_id)
        return folder_id

    @api_request
    def upload_files(self, files):        
        server = self.get_server()
        uploaded_files = []
        for file in files:
            file_name = file["file_name"]
            file_data = file["file_data"]

            folder_id = self.create_public_folder()
            data = {
                "folderId": folder_id,
                "token": self.api_token
            }
            files = [
                ('file', (file_name, file_data, get_mimetype(file_name)))
            ]
            data = self.make_api_request("post", self.get_server_url(server) + "uploadFile", data=data, files=files)
            uploaded_files.append(data["data"]["downloadPage"])
        return uploaded_files

    # @api_request
    # def download(self, download_url):
    #     return super().download(download_url)

class OnlyFilesIo(HostingService):
    name = "OnlyFiles (Io)"
    base_url = "https://onlyfiles.io/"

    def upload_files(self, files):
        uploaded_files = []
        for file in files:
            file_name = file["file_name"]
            file_data = file["file_data"]
            data = {
                "name": file_name,
                "chunk": "0",
                "chunks": "1"
            }
            files = [
                ("file", ("blob", file_data, get_mimetype(file_name)))
            ]
            res = session.post(self.base_url + "upload", data=data, files=files)
            data = res.json()
            if data.get("ok") != True:
                raise Exception(f"Failed to upload file '{file_name}' to service '{self.name}'. Data: {json.dumps(data)}.")
            uploaded_files.append(self.base_url + data["info"])
        return uploaded_files

    def parse_download_url(self, url):
        # It seems that this service places audio pages under the /f/{ID} route, and audio files under
        # the /get/{ID}/{FILE_NAME} route, but it's more consistent to just read the <audio> src attr
        # instead of implicitly constructing it. 
        res = session.get(url)
        soup = BeautifulSoup(res.content, "html.parser")
        audio = soup.select_one("audio")
        if audio is None:
            raise FileNotFoundError(url)
        return self.base_url + audio["src"]
    
    def parse_file_name(self, url):
        res = session.get(url)
        soup = BeautifulSoup(res.content, "html.parser")
        file_name = soup.select_one(".songtitle").text
        return file_name
        

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
    base_timeout = 15 # seconds

    def __init__(self):
        self.bypass_ddos_protection(self.base_timeout)

    def bypass_ddos_protection(self, max_timeout, retry_count=0):
        # If it has failed 4 times ()
        if max_timeout > self.base_timeout * 4:
            logger.critical(f"Could not bypass DDOS protection on DBREE after {retry_count + 1} attempts. Giving up.")
            return
        chromedriver = None
        try:
            chromedriver = create_chrome_driver()
            chromedriver.get(self.base_url)
            wait = WebDriverWait(chromedriver, max_timeout, poll_frequency=1)
            wait.until(lambda x: "DBREE" in chromedriver.title)
            for cookie in chromedriver.get_cookies():
                session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"])
        except:
            # Not actual backoff, immediately retry for twice the interval, i.e. base_timeout * 2^retry_count
            new_timeout = max_timeout * 2
            logger.critical(f"Failed to bypass DDOS protection on DBREE. Retrying for {new_timeout} seconds (attempt {retry_count + 1}).")
            return self.bypass_ddos_protection(new_timeout, retry_count + 1)
        finally:
            if chromedriver is not None: chromedriver.close()

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

Hosts = [
    OnlyFilesIo(),
    OnlyFilesBiz(),
    OnlyFilesCC(),
    # DBREE(),
    AnonFiles(),
    GoFile()
]

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

    """
    def parse_download_url(self, url):
        hosting_service = self.get_hosting_service(url)
        if hosting_service is not None:
            return hosting_service.parse_download_url(url)
    """

    def download(self, url):
        hosting_service = self.get_hosting_service(url)
        try:
            if hosting_service is None:
                raise UnknownHostingServiceError(url)

            files = []

            (file_names, download_urls) = hosting_service.parse_url(url)
            if not isinstance(file_names, list):
                file_names = [file_names]
                download_urls = [download_urls]
            for (file_name, download_url) in zip(file_names, download_urls):
                stream = hosting_service.download(download_url)
                files.append({
                    "file_name": file_name,
                    "download_url": download_url,
                    "hosting_service": hosting_service,
                    "stream": stream
                })
            return files
        except Exception as e:
            # Either file doesn't exist (FileNotFoundError) or something went wrong (e.g. connection was refused).
            # logger.error(e)
            return [{
                "unknown": True,
                "exception": e,
                "traceback": traceback.format_exc()
            }]
