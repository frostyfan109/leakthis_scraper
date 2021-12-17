import logging
import json
import platform
import sys
import os
import pkg_resources
from math import ceil
from importlib_metadata import distributions
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import extract, func
from flask import Response, request, send_file, stream_with_context
from flask_restplus import Resource, inputs
from mimetypes import guess_type
from api import app, api, Flask_Session
from db import Post, File, Prefix
from main import Scraper
from drive import get_direct_url, get_direct_url2, get_file

logger = logging.getLogger(__file__)

section_entries_parser = api.parser()
section_entries_parser.add_argument("posts", type=int, help="Posts per page", location="args", default=20)
section_entries_parser.add_argument("sort_by", type=str, help="Sorting category", location="args", default="latest")
section_entries_parser.add_argument("hide_pinned", type=inputs.boolean, help="Include/exclude pinned posts", location="args", default=True)
section_entries_parser.add_argument("prefix_id", type=int, help="Filter by prefix", location="args", default=None)
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
        prefix_id = args["prefix_id"]
        author = args["author"]
        section_id = Scraper.SECTIONS[section_name]["id"]

        session = Flask_Session()

        # Page starts at 0, i.e. page=0, posts=20 will get the 0-19 most recent posts and page=1, posts=20 will get 20-39 most recent posts.
        # 1) WHERE posts.section_id=`section_id`
        # 2) ORDER_BY posts.id DESC
        # 3) LIMIT `per_page`
        # 4) OFFSET `per_page * page`
        filtered = session.query(Post).filter_by(section_id=section_id)
        if prefix_id is not None:
            prefix = session.query(Prefix).filter_by(prefix_id=prefix_id).first()
            filtered = filtered.filter(Post.prefix == prefix.name)
        if author is not None:
            filtered = filtered.filter(Post.created_by == author)
        if hide_pinned:
            filtered = filtered.filter(Post.pinned == False)
        if sort_by == "latest":
            ordered = filtered.order_by(Post.created.desc())
        elif sort_by == "popular":
            ordered = filtered.order_by(Post.view_count.desc())
        elif sort_by == "active":
            ordered = filtered.order_by(Post.reply_count.desc())
        posts = ordered.limit(per_page).offset(per_page*page)

        session.close()

        return {
            "posts": [post.serialize() for post in posts],
            "pages": ceil(filtered.count() / per_page),
            "total": filtered.count(),
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
                last_scraped = status_data["last_scraped"]
                last_error = status_data["last_error"]
        except FileNotFoundError:
            last_scraped = None
            last_error = None

        with open(os.path.join(os.path.dirname(__file__), "debug_config.json"), "r") as f:
            debug_config = json.load(f)

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
                    }
                }
            },
            "status": {
                "running": scraper_running,
                "pid": pid if scraper_running else None,
                "last_scraped": last_scraped,
                "last_error": last_error,
                "most_recent_post": most_recent_post.serialize()
            },
            "config": {
                "debug_config": debug_config
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
                "timezone": str(datetime.now(timezone.utc).astimezone().tzinfo)
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
@api.route("/config")
class Config(Resource):
    @api.expect(config_parser)
    def post(self):
        form = config_parser.parse_args()

        print_posts_scraped = form.get("print_posts_scraped")
        log_level = form.get("log_level")

        with open(os.path.join(os.path.dirname(__file__), "debug_config.json"), "r") as f:
            config = json.load(f)

        if print_posts_scraped != None:
            config["print_posts_scraped"] = print_posts_scraped

        if log_level != None:
            log_level = log_level.upper()
            if log_level in logging._nameToLevel:
                config["log_level"] = log_level

        with open(os.path.join(os.path.dirname(__file__), "debug_config.json"), "w") as f:
            json.dump(config, f)

        return config
        # print_posts_scraped = form.get("print_posts_scraped")
        # log_level = form.get("log_level")