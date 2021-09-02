import requests
import logging
import traceback
import time
import re
import json
import os
import pickle
import pidfile
from datetime import datetime
from bs4 import BeautifulSoup
from tinycss2 import parse_stylesheet, parse_declaration_list
from urllib.parse import urlparse, parse_qsl
from db import session_factory, Post, File, Prefix
from drive import upload_file, get_direct_url
from url_parser import URLParser
from commons import assert_is_ok, unabbr_number, get_cover

default_log_level = logging.ERROR
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__file__)
logger.setLevel(default_log_level)

def update_session(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.pickle_session()
    return wrapper

class Scraper:
    SECTIONS = {
        "hip-hop-leaks": {
            "path": "/hip-hop-leaks.10",
            "id": 10,
            "name": "Hip-Hop Leaks",
            "description": "Hip Hop leaks only. Any threads that aren't a direct song leak should go in hip-hop discussion or another relevant section."
        },
        "hip-hop-discussion": {
            "path": "/hip-hop-discussion.46",
            "id": 46,
            "name": "Hip-Hop Discussion",
            "description": "A place to discuss hip-hop, both commercial releases and leaks."
        }
    }
    def __init__(self, account_credentials=None, interval=30000, skip_old=True):
        self.interval = interval # in ms
        self.skip_old = skip_old
        self.base_url = "https://leakth.is"
        self.token_expires = None
        self.update_debug_config()
        self.login(account_credentials)

    # @update_session
    def login(self, credentials):
        if credentials == None:
            with open(os.path.join(os.path.dirname(__file__), "credentials.json"), "r") as f:
                credentials = json.load(f)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent" : credentials["user-agent"]})

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
            raise Exception("Login failed.")
        # self.session.cookies.set_cookie(requests.cookies.create_cookie(domain="https://leakth.is", name="xf_notice_dismiss", value="-1"))
        # print(self.session.cookies)

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
                    "url": url
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

        session = session_factory()
        existing_prefix = session.query(Prefix).filter_by(name=name).first()
        if existing_prefix != None:
            return
        url = prefix_tag["href"]
        query_args = dict(parse_qsl(urlparse(url).query))
        prefix_id = query_args.get("prefix_id")

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
            if selector  == "." + ".".join(prefix_class_names):
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


    def parse_posts(self, content, section, post_callback=None):
        post_ids = []
        soup = BeautifulSoup(content, "html.parser")
        for el in soup.select(".structItem--thread"):
            session = session_factory()

            native_id = int([match for match in [re.match(r"^js-threadListItem-(\d+)$", class_name) for class_name in el["class"]] if match != None][0].group(1))

            title_el = el.select_one(".structItem-title")
            title = title_el.find("a", class_="")
            logger.debug(f"Parsing post '{title.text}'")

            prefix = title_el.find("a", class_="labelLink")
            if prefix is not None and prefix.find("span") is not None: self.parse_prefix(soup, prefix)

            existing_post = session.query(Post).filter_by(native_id=native_id).first()
            if existing_post != None and self.skip_old:
                # Post already indexed
                logger.debug(f"Skipping already indexed post '{existing_post.title}'.")
                session.close()
                continue

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

            post_content = self.parse_post_content(post_url)

            if self.debug_config["print_posts_scraped"] == True:
                print(title.text)

            post = Post(
                title=title.text,
                url=post_url,
                prefix=prefix.find("span").text if (prefix is not None and prefix.find("span") is not None) else None,
                created_by=username.text,
                created=datetime.fromtimestamp(int(created_time["data-time"])),
                reply_count=unabbr_number(replies.text),
                view_count=unabbr_number(views.text),
                body=post_content["text"],
                html=post_content["cleaned_html"],
                pinned=pinned_el != None,

                native_id=native_id,
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
                        unknown=True
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
            post_ids.append(post.native_id)

            session.commit()

            if post_callback is not None: post_callback(post.native_id)
            session.close()



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

    def scrape(self, section, callback, pages=2):
        # Scrape `pages` pages initially. Then only check the first page afterwards.
        while True:
            try:
                self.update_debug_config()
                self.scrape_posts(section, pages, callback)
                pages = 1 # After the first loop, set pages back to 1 so that it doesn't make unnecessary requests.
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                traceback.print_exc()
                # logger.critical(e)
                with open("critical_log.txt", "a+") as f:
                    f.write(traceback.format_exc() + "\n")
                self.update_status(last_error={"error": str(e), "traceback": traceback.format_exc(), "time": time.time()})

            self.update_status(last_scraped=time.time())

            logger.debug("Sleeping for " + str(self.interval/1000) + "s.")
            time.sleep(self.interval/1000)

    def scrape_hip_hop_leaks(self, *args, **kwargs):
        return self.scrape("hip-hop-leaks", *args, **kwargs)

    def scrape_hip_hop_discussion(self, *args, **kwargs):
        return self.scrape("hip-hop-discussion", *args, **kwargs)

    def update_debug_config(self):
        with open(os.path.join(os.path.dirname(__file__), "debug_config.json"), "r") as f:
            self.debug_config = json.load(f)
        log_level = self.debug_config["log_level"]
        if log_level == None: log_level = default_log_level
        if logger.getEffectiveLevel() != logging.getLevelName(log_level):
            print(f"Setting log level to '{log_level}'")
        logging.root.setLevel(logging.getLevelName(log_level))
        logger.setLevel(logging.getLevelName(log_level))

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


if __name__ == "__main__":
    with pidfile.PIDFile():
        def post_added(post_id):
            session = session_factory()
            print(f"Archived new post '{session.query(Post).filter_by(native_id=post_id).first().title}'.")
            session.close()

        scraper = Scraper()
        scraper.scrape_hip_hop_leaks(post_added)
    # scraper.scrape_posts("hip-hop-leaks", pages=1)
    # post_ids = scraper.parse_posts(requests.get("https://leakth.is/forums/hip-hop-leaks.10/").content, "hip-hop-leaks")
