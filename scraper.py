import requests
import logging
import traceback
import time
import re
import json
import yaml
import os
import pickle
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from tinycss2 import parse_stylesheet, parse_declaration_list
from urllib.parse import urlparse, parse_qsl
from exceptions import AuthenticationError, MissingEnvironmentError, ConfigError
from db import session_factory, Post, File, Prefix
from drive import upload_file, get_direct_url
from url_parser import URLParser
from commons import assert_is_ok, unabbr_number, get_cover

load_dotenv()

DEFAULT_CONFIG = {
    "timeout_interval": 30000,
    "update_posts": True,
    "disable_db": False,
    "account_credentials": None,
    "print_posts_scraped": True,
    "log_level": "ERROR"
}

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
    SECTIONS = {
        "hip-hop-leaks": {
            "path": "/hiphopleaks",
            "id": 10,
            "name": "Hip-Hop Leaks",
            "description": "Hip Hop leaks only. Any threads that aren't a direct song leak should go in hip-hop discussion or another relevant section."
        },
        "hip-hop-discussion": {
            "path": "/hiphopdiscussion",
            "id": 46,
            "name": "Hip-Hop Discussion",
            "description": "A place to discuss hip-hop, both commercial releases and leaks."
        }
    }
    def __init__(self, config_path=None, credentials=None):
        self.base_url = "https://leaked.cx"
        self.token_expires = None
        self.logged_in_as = None
        if config_path is not None:
            self.config_path = config_path
        elif os.environ.get("CONFIG_PATH") is not None:
            self.config_path = os.environ.get("CONFIG_PATH")
        else:
            raise ConfigError("Could not locate path to config file. Try setting CONFIG_PATH in your environment or passing it to main.py.")
        # `configure_config` is designed such that self.config is initially None,
        # but it is set to DEFAULT_CONFIG for now in case the config file is invalid.
        self.config = DEFAULT_CONFIG
        self.update_config()
        self.login(credentials)
        # self.config = DEFAULT_CONFIG
        # self.configure_config(config)

    def update_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.configure_config(yaml.safe_load(f))
        except FileNotFoundError:
            raise ConfigError(f"Could not locate config file '${self.config_path}'.")
        except yaml.YAMLError:
            raise ConfigError(f"Could not parse YAML config file '${self.config_path}.")

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
        logging.root.setLevel(int_log_level)
        logger.setLevel(int_log_level)

            

    # @update_session
    def login(self, credentials=None):
        credentials_path = None
        if credentials is None:
            credentials_path = os.environ.get("LEAKTHIS_CREDENTIALS_FILE", "")
            if credentials_path == "":
                raise MissingEnvironmentError("LEAKTHIS_CREDENTIALS_FILE")
        if isinstance(credentials, str):
            # credentials is a file path
            credentials_path = credentials
        if credentials_path is not None:
            with open(credentials_path, "r") as f:
                credentials = json.load(f)

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
            raise AuthenticationError(service=self.base_url, credentials_path=credentials_path)
        # self.session.cookies.set_cookie(requests.cookies.create_cookie(domain="https://leakth.is", name="xf_notice_dismiss", value="-1"))
        # print(self.session.cookies)

        self.logged_in_as = credentials["username"]


    def pickle_session(self):
        with open("session_cookies", "wb") as f:
            pickle.dump(self.session.cookies, f)

    def logout(self):
        try:
            with open("session_cookies", "rb") as f:
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
        files = []
        for url in urls:
            download = URLParser().download(url)
            # Make sure the URL is associated with a supported hosting service
            if download is None:
                logger.debug(f"Could not identify associated service for post '{post_url}'")
                with open("non_implemented_urls.txt", "a+") as f:
                    f.write(post_url + " " + url + "\n")
            elif download.get("unknown") == True:
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
                drive_id = upload_file(file_name, stream)
                files.append({
                    "url": url,
                    "download_url": download_url,
                    "file_name": file_name,
                    "drive_id": drive_id,
                    "cover": get_cover(stream)
                })

        return {
            "text": text,
            "cleaned_html": cleaned_html,
            "files": files
        }

    def parse_prefix(self, soup, prefix_tag):
        name = prefix_tag.find("span").text

        session = disableable_session_factory(self.config["disable_db"])
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
        session = disableable_session_factory(self.config["disable_db"])

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
                # Note: in the future, post_content could also be updated, e.g. useful if URLs have been updated.
                session.commit()
            session.close()
            return
        

        post_content = self.parse_post_content(post_data["post_url"])

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
        for file in post_content["files"]:
            if file.get("unknown") == True:
                file = File(
                    post_id=post.native_id,
                    file_name="",
                    url=file["url"],
                    download_url="",
                    drive_id="",
                    unknown=True,
                    exception=str(file["exception"]),
                    traceback=file["traceback"]
                )
            else:
                file = File(
                    post_id=post.native_id,
                    file_name=file["file_name"],
                    url=file["url"],
                    download_url=file["download_url"],
                    drive_id=file["drive_id"],
                    cover=file["cover"]
                )
            session.add(file)
        session.add(post)
        session.commit()
        if post_callback is not None: post_callback(post.native_id)
        session.close()

        return post_data["native_id"]

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

    def scrape(self, section, callback, pages=5):
        # Scrape `pages` pages initially. Then only check the first page afterwards.
        while True:
            try:
                self.update_config()
                self.scrape_posts(section, pages, callback)
                # Pages should be >1 on first loop (where you want to scrape extra to catch up with when the scraper wasn't running)
                # Set the pages back to only 1 after first loop to avoid scraping these extra pages again, because it's extremely unlikely
                # that enough posts to overflow the first page will be posted between scraping timeouts after catching up on the first loop.
                pages = 1
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                # This loop contains the critical scraping lifecycle. Errors should ideally *never* occur here, because that implies
                # that a post cannot be properly scraped/parsed. The only anticipated errors here would be request errors, e.g. connection
                # refusals, though still treat these as critical to be transparent.
                traceback.print_exc()
                # Dump the traceback to a log for further reference.
                self.log_critical(e)

            self.update_status(last_scraped=time.time())

            logger.debug("Sleeping for " + str(self.config["timeout_interval"]/1000) + "s.")
            time.sleep(self.config["timeout_interval"]/1000)

    def scrape_hip_hop_leaks(self, *args, **kwargs):
        return self.scrape("hip-hop-leaks", *args, **kwargs)

    def scrape_hip_hop_discussion(self, *args, **kwargs):
        return self.scrape("hip-hop-discussion", *args, **kwargs)

    """ Log the error and dump the traceback to a text log for further reference. 
        This method is expected to be called within the exception context
        (s.t. traceback works properly). """
    def log_critical(self, e):
        with open("critical_log.txt", "a+") as f:
            f.write(traceback.format_exc() + "\n")
        self.update_status(last_error={"error": str(e), "traceback": traceback.format_exc(), "time": time.time()})

    def get_status_data(self):
        with open("status.json", "r") as f:
            return json.load(f)

    def set_status_data(self, status_data):
        with open("status.json", "w") as f:
            json.dump(status_data, f)

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