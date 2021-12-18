import logging
import json
import platform
import sys
import os
import pkg_resources
from math import ceil
from importlib_metadata import distributions
from dotenv import dotenv_values
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import extract, func
from flask import Response, request, send_file, stream_with_context
from flask_restplus import Resource, inputs, abort
from mimetypes import guess_type
from api import app, api, Flask_Session
from db import Post, File, Prefix
from config import load_config, save_config
from main import Scraper
from drive import get_direct_url, get_direct_url2, get_file, get_drive

logger = logging.getLogger(__file__)

section_entries_parser = api.parser()
section_entries_parser.add_argument("posts", type=int, help="Posts per page", location="args", default=20)
section_entries_parser.add_argument("sort_by", type=str, help="Sorting category", location="args", default="latest")
section_entries_parser.add_argument("hide_pinned", type=inputs.boolean, help="Include/exclude pinned posts", location="args", default=True)
section_entries_parser.add_argument("prefix_raw_id", type=int, help="Filter by prefix", location="args", default=None)
section_entries_parser.add_argument("author", type=str, help="Filter by author", location="args", default=None)

@api.route("/section/<string:section_name>/<int:page>")
class SectionEntries(Resource):
    @api.expect(section_entries_parser)
        # @db_resource
    def get(self, section_name, page):
        args = section_entries_parser.parse_args()
        per_page = args["posts"]
        sort_by = args["sort_by"]
        hide_pinned = args["hide_pinned"]
        prefix_raw_id = args["prefix_raw_id"]
        author = args["author"]
        section_id = Scraper.SECTIONS[section_name]["id"]

        session = Flask_Session()

        # Page starts at 0, i.e. page=0, posts=20 will get the 0-19 most recent posts and page=1, posts=20 will get 20-39 most recent posts.
        # 1) WHERE posts.section_id=`section_id`
        # 2) ORDER_BY posts.id DESC
        # 3) LIMIT `per_page`
        # 4) OFFSET `per_page * page`
        def filter_chain(filtered):
            if prefix_raw_id is not None:
                prefix = session.query(Prefix).filter_by(id=prefix_raw_id).first()
                # filtered = filtered.filter(Post.prefix == prefix.name)
                # Post.prefixes is a JSON wrapper abstraction that is really just a Unicode string.
                # This makes it difficult to do performant sorting on it, when it needs to be treated as a list.
                filtered = filtered.filter(Post.prefixes.contains(prefix.name)) 
            if author is not None:
                filtered = filtered.filter(Post.created_by == author)
            # if hide_pinned:
                # filtered = filtered.filter(Post.pinned == False)
            if sort_by == "latest":
                ordered = filtered.order_by(Post.created.desc())
            elif sort_by == "popular":
                ordered = filtered.order_by(Post.view_count.desc())
            elif sort_by == "active":
                ordered = filtered.order_by(Post.reply_count.desc())
            return ordered

        non_pinned = filter_chain(session.query(Post).filter((Post.section_id == section_id) & (Post.pinned == False)))
        # Only the first page should have pinned posts. And only when hide_pinned == False.
        if page == 0 and not hide_pinned:
            pinned = filter_chain(session.query(Post).filter((Post.section_id == section_id) & (Post.pinned == True)))
        else:
            # Create an empty query
            pinned = session.query(Post).filter(False)

        num_pages = ceil(non_pinned.count() / per_page)
        # If the page number is greater than the total number of pages, return the last page.
        if page > num_pages:
            # `page` goes from 0 to `num_pages - 1`
            page = num_pages - 1

        # Pinned posts don't count towards the pagination limit, i.e., the first page will have the pinned posts + normal pagination limit.
        posts = pinned.all() + non_pinned.limit(per_page).offset(per_page*page).all()

        session.close()

        return {
            "posts": [post.serialize() for post in posts],
            "pages": num_pages,
            "total": non_pinned.count(),
            "page": page,
            "per_page": per_page
        }

@api.route("/sections")
class Sections(Resource):
    def get(self):
        return Scraper.SECTIONS

@api.route("/prefixes")
class Prefixes(Resource):
    # @db_resource
    def get(self):
        session = Flask_Session()
        prefixes = [prefix.serialize() for prefix in session.query(Prefix)]
        session.close()
        return prefixes

info_parser = api.parser()
info_parser.add_argument("sort", type=str, help="Current scraping sort", location="args")
info_parser.add_argument("range", type=int, help="Current number (per current sort)", location="args")

@api.route("/info")
class Info(Resource):
    # @db_resource
    @api.expect(info_parser)
    def get(self):
        args = info_parser.parse_args()
        sort = args["sort"]
        cur_range = args["range"]

        session = Flask_Session()

        scraper_running = True
        try:
            with open(os.path.join(os.path.dirname(__file__), "pidfile"), "r") as f:
                pid = f.read()
        except FileNotFoundError:
            scraper_running = False
        try:
            with open(os.path.join(os.path.dirname(__file__), "status.json"), "r") as f:
                status_data = json.load(f)    
        except FileNotFoundError:
            status_data = {}

        last_scraped = status_data.get("last_scraped", None)
        last_error = status_data.get("last_error", None)
        leakthis_username = status_data.get("leakthis_username", None)
        leakthis_password = status_data.get("leakthis_password", None)
        leakthis_user_agent = status_data.get("leakthis_user_agent", None)

        config = load_config()

        most_recent_post = session.query(Post).order_by(Post.first_scraped.desc()).first()

        num_days = 7
        num_weeks = 8
        num_months = 12

        if sort == "days":
            num_days = cur_range
        elif sort == "weeks":
            num_weeks = cur_range
        elif sort == "months":
            num_months = cur_range

        days = [(datetime.today() - relativedelta(days=num_days-1-n)) for n in range(num_days)]
        weeks = [(datetime.today() - relativedelta(weeks=num_weeks-1-n)) for n in range(num_weeks)]
        months = [(datetime.today() - relativedelta(months=num_months-1-n)) for n in range(num_months)]
        scrapes_per_day = {
            "labels": [day.strftime("%A") for day in days],
            "data": [
                session.query(Post).filter(
                    extract('year', Post.first_scraped) == day.year,
                    extract('month', Post.first_scraped) == day.month,
                    extract('day', Post.first_scraped) == day.day
                ).count() for day in days
            ],
            "min": 2,
            "max": 14,
            "default": 7,
            "range": cur_range if sort == "days" else None
        }
        scrapes_per_week = {
            "labels": [week.strftime("%B") + " " + str(week.day) for week in weeks],
            "data": [
                session.query(Post).filter(
                    extract('year', Post.first_scraped) == week.year,
                    extract('month', Post.first_scraped) == week.month,
                    func.strftime("%W", Post.first_scraped) == week.strftime("%W")
                ).count() for week in weeks
            ],
            "min": 2,
            "max": 16,
            "default": 8,
            "range": cur_range if sort == "weeks" else None
        }
        scrapes_per_month = {
            "labels": [month.strftime("%B") for month in months],
            "data": [
                session.query(Post).filter(
                    extract('year', Post.first_scraped) == month.year,
                    extract('month', Post.first_scraped) == month.month
                ).count() for month in months
            ],
            "min": 2,
            "max": 24,
            "default": 12,
            "range": cur_range if sort == "months" else None
        }

        post_count = session.query(Post).count()
        known_file_count = session.query(File).filter((File.unknown == False) | (File.unknown == None)).count()
        total_file_count = session.query(File).count()

        drive = get_drive()
        about = drive.GetAbout()
        drive_quota_used = int(about["quotaBytesUsed"])
        drive_quota_total = int(about["quotaBytesTotal"])
        drive_user = about["name"]

        session.close()

        with open(os.path.join(os.path.dirname(__file__), "requirements.txt"), "r") as req_txt:
            required_dependencies = [{"name": req.name, "version": str(req.specifier)} for req in pkg_resources.parse_requirements(req_txt)]
        installed_dependencies = [{"name": dist.metadata["name"], "version": dist.version} for dist in list(distributions())]

        return {
            "data": {
                "scrape_data": {
                    "data": {
                        "days": scrapes_per_day,
                        "weeks": scrapes_per_week,
                        "months": scrapes_per_month
                    },
                    "post_count": post_count,
                    "known_file_count": known_file_count,
                    "total_file_count": total_file_count,
                    "drive_quota_used": drive_quota_used,
                    "drive_quota_total": drive_quota_total
                }
            },
            "status": {
                "running": scraper_running,
                "pid": pid if scraper_running else None,
                "last_scraped": last_scraped,
                "last_error": last_error,
                "most_recent_post": most_recent_post.serialize(),
                "account_info": {
                    "leakthis_username": leakthis_username,
                    "leakthis_password": leakthis_password,
                    "leakthis_user_agent": leakthis_user_agent,
                    "drive_user": drive_user
                }
            },
            "config": {
                "scraper_config": config
            },
            "environment": {
                "platform": platform.system(),
                "arch": platform.architecture()[0],
                "release": platform.version(),
                "version": [sys.version_info.major, sys.version_info.minor, sys.version_info.micro],
                "virtualenv": "VIRTUAL_ENV" in os.environ,
                "dependencies": [
                    {
                        "name": "Required",
                        "dependencies": required_dependencies
                    },
                    {
                        "name": "Installed",
                        "dependencies": installed_dependencies
                    }
                ],
                "timezone": str(datetime.now(timezone.utc).astimezone().tzinfo),
                "environment_vars": dotenv_values()
            },
            "meta": {
                "log_levels": list(logging._nameToLevel.keys())
            }
        }

@api.route("/download_url/<string:drive_id>")
class DownloadURL(Resource):
    def get(self, drive_id):
        return get_direct_url2(drive_id)

direct_download_parser = api.parser()
direct_download_parser.add_argument("download", type=inputs.boolean, help="Download as attachment rather than inline.", location="args", default=True, required=False)
@api.route("/download/<string:drive_id>")
class DirectDownload(Resource):
    def get(self, drive_id):
        args = direct_download_parser.parse_args()

        attachment = args.get("download", True)

        session = Flask_Session()
        file = session.query(File).filter_by(drive_id=drive_id).first()
        if file is None:
            return abort(404, f"File with drive id '{drive_id}' does not exist.")
        drive_file = get_file(drive_id)
        drive_file.FetchContent()
        # Could also get Drive's inferred mimetype from file.FetchMetadata() and file["mimeType"],
        # but it's more accurate to just go off of the file name in the first place.
        file_name = file.file_name
        mimetype = guess_type(file.file_name)[0]
        session.close()
        response = send_file(
            drive_file.content,
            # Docs say that download_name is supported in Flask 2.0.x, but apparently it isn't.
            # download_name=file_name,
            # Sets Content-Disposition
            # as_attachment=False,
            # attachment_filename=file_name,
            mimetype=mimetype
        )
        response.headers.set("Content-Disposition", f'{"attachment" if attachment else "inline"}; filename="{file_name}"')
        response.headers.set("Content-Length", str(drive_file.content.getbuffer().nbytes))
        return response

@api.route("/file/<int:file_id>/cover")
class FileCover(Resource):
    def get(self, file_id):
        session = Flask_Session()
        file = session.query(File).filter_by(id=file_id).first()
        if file == None:
            session.close()
            return {"message": "File not found"}, 404
        session.close()
        return send_file(
            BytesIO(file.cover),
            attachment_filename=file.file_name
        )


config_parser = api.parser()
config_parser.add_argument("print_posts_scraped", type=inputs.boolean, help="Log scraped posts", location="form", required=False)
config_parser.add_argument("log_level", type=str, help="Logging level", location="form", required=False)
config_parser.add_argument("timeout_interval", type=int, help="Timeout interval", location="form", required=False)
config_parser.add_argument("update_posts", type=inputs.boolean, help="Update posts", location="form", required=False)
@api.route("/config")
class Config(Resource):
    """ Update the scraping config """
    @api.expect(config_parser)
    def post(self):
        form = config_parser.parse_args()

        print_posts_scraped = form.get("print_posts_scraped")
        log_level = form.get("log_level")
        timeout_interval = form.get("timeout_interval")
        update_posts = form.get("update_posts")

        config = load_config()

        if print_posts_scraped is not None:
            config["print_posts_scraped"] = print_posts_scraped

        if log_level is not None:
            log_level = log_level.upper()
            if log_level in logging._nameToLevel:
                config["log_level"] = log_level

        if timeout_interval is not None:
            config["timeout_interval"] = timeout_interval

        if update_posts is not None:
            config["update_posts"] = update_posts

        save_config(config)

        return config
        # print_posts_scraped = form.get("print_posts_scraped")
        # log_level = form.get("log_level")