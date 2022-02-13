import requests
import logging
import traceback
import time
import re
import json
import os
import pickle
import portalocker
import math
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from tinycss2 import parse_stylesheet, parse_declaration_list
from urllib.parse import urlparse, parse_qsl
from PIL import Image
from io import BytesIO
from exceptions import AuthenticationError, MissingEnvironmentError, ConfigError
from db import session_factory, Post, File, Prefix
from drive import upload_file, get_direct_url, get_drive_breakdown
from config import load_config, load_credentials
from url_parser import URLParser
from event_api_adapter import EventAPIAdapter
from commons import assert_is_ok, unabbr_number, get_cover, get_env_var

load_dotenv()

DEFAULT_CONFIG = {
    "timeout_interval": 30000,
    "update_posts": True,
    "max_retries": 3,
    "disable_db": False,
    "account_credentials": None,
    "print_posts_scraped": True,
    "log_level": "ERROR",
    "initial_pages_scraped": 2,
    "subsequent_pages_scraped": 1
}

static_dir = get_env_var("STATIC_DIRECTORY")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__file__)
logger.setLevel(logging.getLevelName(DEFAULT_CONFIG["log_level"]))

def update_session(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.pickle_session()
    return wrapper

def disableable_session_factory(disabled):
    session = session_factory()
    if disabled:
        def add_no_op(*args, **kwargs): pass
        session.add = add_no_op
    return session

class Scraper:
    """ To be incremented in the case that the site's database is wiped (resetting native_id and disassociating already scraped posts). """
    LT_DB_VERSION = 2
    SECTIONS = {
        "hip-hop-leaks": {
            "path": "/hiphopleaks",
            "id": 10,
            "name": "Hip-Hop Leaks",
            "description": "Hip Hop leaks only. Any threads that aren't a direct song leak should go in hip-hop discussion or another relevant section."
        },
        "other-genre-leaks": {
            "path": "/othermedialeaks",
            "id": 1,
            "name": "Other Media Leaks",
            "description": "For other forms of media or higher quality leaks."
        },
        "edits": {
            "path": "/edits",
            "id": 2,
            "name": "Edits",
            "description": ""
        },
        "hip-hop-discussion": {
            "path": "/hiphopdiscussion",
            "id": 43,
            "name": "Hip-Hop Discussion",
            "description": "A place to discuss hip-hop, both commercial releases and leaks."
        }
    }
    def __init__(self, credentials=None):
        self.base_url = "https://leaked.cx"
        self.token_expires = None
        # `configure_config` is designed such that self.config is initially None,
        # but it is set to DEFAULT_CONFIG for now in case the config file is invalid.
        self.config = DEFAULT_CONFIG
        self.update_config()
        self.login(credentials)
        self.event_api_adapter = EventAPIAdapter(authorization=get_env_var("INTERNAL_API_KEY"))
        # self.config = DEFAULT_CONFIG
        # self.configure_config(config)

        logger.info(get_drive_breakdown())

    def update_config(self):
        self.configure_config(load_config())

    def configure_config(self, new_config):
        old_config = self.config
        self.config = new_config

        # self.interval = self.options.get("timeout_interval", 30000) # in ms
        # self.update_posts = self.options.get("update_posts", True) # when enabled, scraped posts will be updated each time they are scraped.
        # self.disable_db = self.options.get("disable_db", False) # when enabled, the scraper will not write to the database (for debugging purposes)
        
        # Set defaults if values omitted
        for key in DEFAULT_CONFIG:
            if self.config.get(key) is None: self.config[key] = DEFAULT_CONFIG[key]


        """ Update global application/scraper state based on config changes """
        # Login to website with new credentials
        # This exposes credentials so it has been removed. And it was not really necessary.
        # if old_config is None or self.config["account_credentials"] != old_config["account_credentials"]:
        #     self.login(self.config["account_credentials"])

        # Update the global log level of application as well as the scraper's log level
        int_log_level = logging.getLevelName(self.config["log_level"])
        if logger.getEffectiveLevel() != int_log_level:
            logger.info(f"Setting log level to '{self.config['log_level']}'")
        # logging.root.setLevel(int_log_level)
        logger.setLevel(int_log_level)

            

    # @update_session
    def login(self, credentials=None):
        if credentials is None:
            credentials = load_credentials()

        self.update_status(leakthis_username=credentials["username"])
        # Store as asterisks of same length
        self.update_status(leakthis_password="*"*len(credentials["password"]))
        self.update_status(leakthis_user_agent=credentials.get("user-agent", "None"))

        self.session = requests.Session()
        self.session.headers.update({"User-Agent" : credentials.get("user-agent")})
        # Make sure to logout so that a new session is established
        # self.logout()

        data = {
            "login": credentials["username"],
            "password": credentials["password"],
            "remember": 1,
            "_xfRedirect": "",
            "_xfToken": self.get_csrf()
        }
        res = self.session.post(self.base_url + "/login/login", data=data)
        assert_is_ok(res)
        for cookie in self.session.cookies:
            if cookie.name == "xf_user":
                self.token_expires = cookie.expires
        if self.token_expires is None:
            # Login failed
            raise AuthenticationError(f"Failed to authenticate with service '{self.base_url}' using username '{credentials['username']}'.")
        # self.session.cookies.set_cookie(requests.cookies.create_cookie(domain="https://leakth.is", name="xf_notice_dismiss", value="-1"))
        # print(self.session.cookies)

        logger.info(f"Logged into Leakthis as user '{credentials['username']}'")


    def pickle_session(self):
        with open(os.path.join(os.path.dirname(__file__), "session_cookies"), "wb+") as f:
            pickle.dump(self.session.cookies, f)

    def logout(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), "session_cookies"), "rb") as f:
                self.session.cookies.update(pickle.load(f))
        except FileNotFoundError:
            # No session has been created before
            return
        res = self.session.get(self.base_url + "/logout/?t=" + self.get_csrf())
        assert_is_ok(res)

    def get_csrf(self):
        res = self.session.get(self.base_url)
        assert_is_ok(res)
        soup = BeautifulSoup(res.content, "html.parser")
        return soup.find("html")["data-csrf"]

    def create_db_session(self):
        return disableable_session_factory(self.config["disable_db"])

    """ Should only be used on a post with 0 existing files
        (e.g., if a post was catalogued before the Scraper
        was updated to support "unknown" files). """
    def retry_post(self, post_id):
        session = self.create_db_session()
        post = session.query(Post).filter_by(id=post_id).first()
        post_content = self.parse_post_content(post.url)
        files = self.download_all_files(post_content["urls"])
        for file_data in files:
            session.add(self.create_file(post_id, file_data))
        session.commit()
        session.close()

    def retry_file(self, file):
        downloaded_files = self.download_files(file.url)
        """ Only retry URLs for single files. The data gets messy for URLs that point to multiple files. """
        """ Note that download_files should never return an empty list. It should either return files or a list of one unknown file. """
        if len(downloaded_files) == 1:
            downloaded_file = downloaded_files[0]
            if downloaded_file.get("unknown"):
                # Still unknown
                file.retries += 1
            else:
                file.unknown = False
                file.file_name = downloaded_file["file_name"]
                file.download_url = downloaded_file["download_url"]
                file.drive_id = downloaded_file["drive_id"]
                file.drive_project_id = downloaded_file["drive_project_id"]
                file.cover = downloaded_file["cover"]
                file.file_size = downloaded_file["file_size"]
                file.hosting_service = downloaded_file["hosting_service"]
                logger.info(f"Successfully retrieved file with URL '{file.url}' for post '{file.get_post().title}'.")
            file.last_updated = datetime.now()

    def retry_unknown_files(self):
        session = self.create_db_session()
        unknown_files = session.query(File).filter_by(unknown=True).filter(File.retries < self.config["max_retries"])
        logger.info(f"Retrying {unknown_files.count()} unknown files.")
        for file in unknown_files:
            self.retry_file(file)
        session.commit()
        session.close()

    def check_deleted_posts(self):
        logger.info("Checking for deleted posts.")
        num_posts = self.config["check_deleted_depth"]
        session = self.create_db_session()
        posts = session.query(Post).order_by(Post.created.desc())[0:num_posts]
        for post in posts:
            # Don't bother checking again.
            if post.deleted: continue
            # These requests are being made synchronously, so it would be problematic for the requests to hang.
            # This could pretty easily be made async with aiohttp, but that should be ideally be done with a complete
            # async rewrite of the scraper.
            res = self.session.get(post.url, timeout=3)
            if res.status_code == 404:
                logger.info(f"Marking post \"{post.title}\" as deleted.")
                post.deleted = True
        session.commit()
        session.close()

    def download_files(self, url):
        downloads = URLParser().download(url)
        files = []
        for download in downloads:
            # Make sure the URL is associated with a supported hosting service
            if download.get("unknown") == True:
                files.append({
                    "unknown": True,
                    "url": url,
                    "exception": download["exception"],
                    "traceback": download["traceback"]
                })
            else:
                download_url = download["download_url"]
                stream = download["stream"]
                file_name = download["file_name"]
                hosting_service = download["hosting_service"].name
                (drive_project_id, drive_id) = upload_file(file_name, stream)
                files.append({
                    "url": url,
                    "download_url": download_url,
                    "file_name": file_name,
                    "file_size": len(stream),
                    "hosting_service": hosting_service,
                    "drive_id": drive_id,
                    "drive_project_id": drive_project_id,
                    "cover": None
                    # "cover": get_cover(stream)
                })
        return files

    def download_all_files(self, urls):
        files = []
        for url in urls:
            files.append(*self.download_files(url))
        return files

    def create_file(self, post_id, file_data):
        if file_data.get("unknown") == True:
            file = File(
                post_id=post_id,
                file_name="",
                url=file_data["url"],
                download_url="",
                file_size=0,
                hosting_service="",
                drive_id="",
                drive_project_id="",
                unknown=True,
                exception=str(file_data["exception"]),
                traceback=file_data["traceback"]
            )
        else:
            file = File(
                post_id=post_id,
                file_name=file_data["file_name"],
                url=file_data["url"],
                download_url=file_data["download_url"],
                file_size=file_data["file_size"],
                hosting_service=file_data["hosting_service"],
                drive_id=file_data["drive_id"],
                drive_project_id=file_data["drive_project_id"],
                cover=file_data["cover"]
            )
        logger.info(f"Creating new file {str(file)}.")
        return file

    def parse_post_content(self, post_url):
        res = self.session.get(post_url)
        assert_is_ok(res)
        soup = BeautifulSoup(res.content, "html.parser")

        el = soup.select_one(".message-threadStarterPost")
        message_content = el.select_one(".message-content").select_one(".bbWrapper")

        text = message_content.text

        urls = [a.get("href") for a in message_content.select("a") if a.get("href") != None and a.get("href") != ""]
        # It seems that the site loads embedded components as template <span> components and then transforms them into iframes
        # with client-side scripts, so this probably won't do anything ever. This seems to be a feature of the phpBB extension s9e/mediaembed.
        urls += [iframe.get("src") for iframe in message_content.select("iframe")]
        # Mark the template <span> components instead
        for iframe_template in message_content.select("*[data-s9e-mediaembed-iframe]"):
            embed_attr_list = json.loads(iframe_template.get("data-s9e-mediaembed-iframe"))
            # For some reason, it stores the iframe template attributes as an array of [key1, value1, key2, value2, key3, value3, etc.].
            # Every even value
            keys = embed_attr_list[::2]
            # Every odd value
            values = embed_attr_list[1::2]
            embed_attr_dict = dict(zip(keys, values))
            urls.append(embed_attr_dict["src"])


        # Strip all ids and classes from the post tree and serialize it to text.
        def clean_tag(tag):
            del tag["class"]
            del tag["id"]
            # Iterate over children
            for child in tag.find_all(recursive=False):
                clean_tag(child)
            return tag

        cleaned_html = str(clean_tag(message_content))

        # download_urls = [download_url for download_url in [URLParser().parse_download_url(url) for url in urls] if download_url != None]

        return {
            "text": text,
            "cleaned_html": cleaned_html,
            "urls": urls
        }

    def parse_prefix(self, soup, prefix_tag):
        name = prefix_tag.find("span").text

        session = self.create_db_session()
        existing_prefix = session.query(Prefix).filter_by(name=name).first()
        if existing_prefix != None:
            return
        logger.info(f"Parsing new prefix '{name}'")
        url = prefix_tag["href"]
        query_args = dict(parse_qsl(urlparse(url).query))
        # For some reason, the ?prefix_id query param is always a list of length 1, i.e. ?prefix_id[0]={}
        # but parse_qsl doesn't properly parse this format of list-valued params, and there are 0 alternatives.
        # So just hard-code to read the value.
        prefix_id = query_args.get("prefix_id[0]")

        prefix_class_names = prefix_tag.find("span")["class"]

        # Scrape CSS for prefix colors
        style_url = soup.find("link", rel="stylesheet", href=re.compile(r"^/css\.php\?css=public%3Anotices\.less"))["href"]
        res = self.session.get(self.base_url + style_url)
        assert_is_ok(res)
        stylesheet = parse_stylesheet(res.content.decode("utf-8"))
        style_rules = {}
        for rule in stylesheet:
            if not hasattr(rule, "prelude"): continue
            selector = "".join([token.serialize() for token in rule.prelude])
            if selector == "." + ".".join(prefix_class_names):
                declarations = parse_declaration_list(rule.content)
                for declaration in declarations:
                    style_rules[declaration.name] = "".join([token.serialize() for token in declaration.value])
                break

        text_color = style_rules.get("color")
        bg_color = style_rules.get("background-color")

        prefix = Prefix(
            prefix_id=prefix_id,
            name=name,
            text_color=text_color,
            bg_color=bg_color
        )
        session.add(prefix)
        session.commit()
        session.close()

    def parse_post_data(self, soup, el):
        native_id = int([match for match in [re.match(r"^js-threadListItem-(\d+)$", class_name) for class_name in el["class"]] if match != None][0].group(1))
        native_id = self.format_native_id(native_id)
        title_el = el.select_one(".structItem-title")
        title = title_el.find("a", class_="")
        logger.debug(f"Parsing post '{title.text}'")

        prefixes = title_el.find_all("a", class_="labelLink")
        for prefix in prefixes:
            if prefix is not None and prefix.find("span") is not None: self.parse_prefix(soup, prefix)

        minor_el = el.select_one(".structItem-minor")
        username = minor_el.select_one(".username")
        created_time = minor_el.select_one(".structItem-startDate").find("time")
        # The created url contains just the post url, as opposed to the title, which contains /unread/.
        # The time element is a child of the created url.
        created_url = created_time.parent["href"]
        post_url = self.base_url + created_url

        pinned_el = el.select_one(".structItem-status--sticky")

        meta_el = el.select_one(".structItem-cell--meta")
        replies = meta_el.find("dt", text="Replies").find_next_sibling("dd")
        views = meta_el.find("dt", text="Views").find_next_sibling("dd")

        return {
            "native_id": native_id,

            "title": title.text,
            "prefixes": [prefix.find("span").text if (prefix is not None and prefix.find("span") is not None) else None for prefix in prefixes],
            "username": username.text,
            "created_time": datetime.fromtimestamp(int(created_time["data-time"])),
            "created_url": created_url,
            "post_url": post_url,
            "is_pinned": pinned_el is not None,
            "reply_count": unabbr_number(replies.text),
            "view_count": unabbr_number(views.text)
        }

    def parse_post(self, soup, el, section, post_callback):
        session = self.create_db_session()

        post_data = self.parse_post_data(soup, el)

        existing_post = session.query(Post).filter_by(native_id=post_data["native_id"]).first()
        if existing_post is not None:
            # Post already indexed
            if not self.config["update_posts"]:
                logger.debug(f"Skipping already indexed post '{existing_post.title}'.")
            else:
                """ Update the basic post data """
                # Has the user modified the title?
                existing_post.title = post_data["title"]
                # Has the user changed the prefixes on the post?
                existing_post.prefixes = post_data["prefixes"]
                # Has the user changed their name?
                # Note: in the future, username changes could potentially be tracked.
                existing_post.created_by = post_data["username"]
                # Update engagement data
                existing_post.reply_count = post_data["reply_count"]
                existing_post.view_count = post_data["view_count"]
                existing_post.pinned = post_data["is_pinned"]
                # Posts can be moved to different sections.
                existing_post.section_id = self.get_section_id(section)
                # The post has been updated.
                existing_post.last_updated = datetime.now() 
                # Note: in the future, post_content could also be updated, e.g. useful if URLs have been updated.
                session.commit()
            session.close()
            return
        

        post_content = self.parse_post_content(post_data["post_url"])

        files = self.download_all_files(post_content["urls"])

        if self.config["print_posts_scraped"] == True:
            print(post_data["title"])

        post = Post(
            title=post_data["title"],
            url=post_data["post_url"],
            # prefix=,
            prefixes=post_data["prefixes"],
            created_by=post_data["username"],
            created=post_data["created_time"],
            reply_count=post_data["reply_count"],
            view_count=post_data["view_count"],
            pinned=post_data["is_pinned"],

            body=post_content["text"],
            html=post_content["cleaned_html"],

            native_id=post_data["native_id"],
            section_id=self.get_section_id(section)
        )
        session.add(post)
        session.commit()

        post_id = post.id

        for file_data in files:
            session.add(self.create_file(post_id, file_data))
        logger.info(f"Parsed new post {str(post)}.")
        session.commit()
        if post_callback is not None: post_callback(post_id)
        session.close()

        self.event_api_adapter.post_created(post_id)

        return post_id

    def parse_posts(self, content, section, post_callback=None):
        post_ids = []
        try:
            soup = BeautifulSoup(content, "html.parser")
            for el in soup.select(".structItem--thread"):
                post_id = self.parse_post(soup, el, section, post_callback)
                post_ids.append(post_id)

        except KeyboardInterrupt: raise e
        except Exception as e:
            """ This is the second critical loop in scraping execution. We don't want to halt scraping just because
            one page failed (e.g. if it is running on the first 10 pages and the 2nd page fails it won't scrape the 3-10).
            Instead, we will skip the page for now and try again next loop.
            """
            traceback.print_exc()
            self.log_critical(e)
        return post_ids

    # @update_session
    def scrape_posts(self, section, pages, callback=None):
        posts = []
        for i in range(pages):
            url = self.base_url + "/forums" + self.get_section_url(section)
            if i > 0:
                url += "/page-" + str(i+1) +"/"
            # Order posts by when they were created, not by most recent activity.
            url += "?order=post_date&direction=desc"
            res = self.session.get(url)
            assert_is_ok(res)
            posts += self.parse_posts(res.content, section, callback)
        return posts
    
    def resolve_static_asset_urls(self):
        """ Resolve static URLs for assets to download. """
        res = requests.get(self.base_url)
        assert_is_ok(res)
        soup = BeautifulSoup(res.content, "html.parser")
        logo_url = soup.select_one(".uix_logo > img")["src"]
        favicon_url = soup.select_one("head link[rel='icon']")["href"]

        return {
            "logo_url": logo_url,
            "favicon_url": favicon_url
        }

    def scrape_static_assets(self):
        logger.info("Scraping static assets.")
        session = self.create_db_session()

        # Make sure the static directory exists.
        try:
            os.mkdir(static_dir)
        except FileExistsError:
            pass

        urls = self.resolve_static_asset_urls()
        
        """ Download static assets. """
        # Download logo
        res = requests.get(self.base_url + urls["logo_url"])
        assert_is_ok(res)
        # Ensure that the logo is saved as a PNG, regardless of the original format.
        logo_img = Image.open(BytesIO(res.content))
        logo_img.save(os.path.join(static_dir, "logo.png")) 
        
        # Download favicon
        # The favicon url isn't relative.
        res = requests.get(urls["favicon_url"])
        assert_is_ok(res)
        favicon_img = Image.open(BytesIO(res.content))
        favicon_img.save(os.path.join(static_dir, "favicon.ico"))

        session.close()
        return {
            "logo_img": logo_img,
            "favicon_img": favicon_img
        }
        

    def scrape(self, sections, callback):
        last_checked_deleted = datetime.now()
        # Scrape `pages` pages initially. Then only check the first page afterwards.
        if len(sections) == 0:
            raise Exception("Scraping sections cannot be empty.")
        self.scrape_static_assets()
        logger.info(f"Beginning scraping on sections: {', '.join(sections)}.")
        pages = self.config["initial_pages_scraped"]
        while True:
            try:
                self.update_config()
                for section in sections:
                    logger.info(f"Scraping first {pages} pages for section '{section}'.")
                    self.scrape_posts(section, pages, callback)
                self.retry_unknown_files()
                minutes_since_last_checked_deleted = math.floor((datetime.now() - last_checked_deleted).seconds / 60)
                if minutes_since_last_checked_deleted >= self.config["check_deleted_interval"]:
                    last_checked_deleted = datetime.now()
                    self.check_deleted_posts()
                # Pages should be >1 on first loop (where you want to scrape extra to catch up with when the scraper wasn't running)
                # Set the pages back to only 1 after first loop to avoid scraping these extra pages again, because it's extremely unlikely
                # that enough posts to overflow the first page will be posted between scraping timeouts after catching up on the first loop.
                pages = self.config["subsequent_pages_scraped"]
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                # This loop contains the critical scraping lifecycle. Errors should ideally *never* occur here, because that implies
                # that a post cannot be properly scraped/parsed. The only anticipated errors here would be request errors, e.g. connection
                # refusals, though still treat these as critical to be transparent.
                traceback.print_exc()
                # Dump the traceback to a log for further reference.
                self.log_critical(e)

            self.update_status(last_scraped=time.time(), sections_scraped=sections)

            logger.info("Sleeping for " + str(self.config["timeout_interval"]/1000) + "s.")
            time.sleep(self.config["timeout_interval"]/1000)

    def scrape_hip_hop_leaks(self, *args, **kwargs):
        return self.scrape(["hip-hop-leaks"], *args, **kwargs)

    def scrape_hip_hop_discussion(self, *args, **kwargs):
        return self.scrape(["hip-hop-discussion"], *args, **kwargs)

    """ Log the error and dump the traceback to a text log for further reference. 
        This method is expected to be called within the exception context
        (s.t. traceback works properly). """
    def log_critical(self, e):
        try:
            with open(os.path.join(os.path.dirname(__file__), "critical_log.txt"), "a+") as f:
                f.write(traceback.format_exc() + "\n")
        except:
            # It seems that UnicodeEncodeErrors can be run into here, and perhaps others.
            # Better to avoid than crash the scraper (since log_critical is often called in exception handlers
            # so it could be called outside a try block).
            pass
        self.update_status(last_error={"error": str(e), "traceback": traceback.format_exc(), "time": time.time()})

    def get_status_data(self):
        try:
            with portalocker.Lock(os.path.join(os.path.dirname(__file__), "status.json"), "r") as fh:
                return json.load(fh)
        except:
            with portalocker.Lock(os.path.join(os.path.dirname(__file__), "status.json"), "w+") as fh:
                data = {}
                fh.write(json.dumps(data))
                return data

    def set_status_data(self, status_data):
        with portalocker.Lock(os.path.join(os.path.dirname(__file__), "status.json"), "w+") as fh:
            json.dump(status_data, fh)

    def update_status(self, **kwargs):
        status_data = self.get_status_data()
        for kwarg in kwargs:
            status_data[kwarg] = kwargs[kwarg]
        self.set_status_data(status_data)

    @classmethod
    def get_section_url(cls, section):
        return cls.SECTIONS[section]["path"]

    @classmethod
    def get_section_id(cls, section):
        return cls.SECTIONS[section]["id"]

    @classmethod
    def format_native_id(cls, native_id):
        return str(cls.LT_DB_VERSION) + "." + str(native_id)
