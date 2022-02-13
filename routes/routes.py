import logging
import json
import platform
import sys
import os
import pkg_resources
import ffmpeg
import portalocker
import tempfile
import time
import math
from subprocess import Popen, PIPE
from math import ceil
from importlib_metadata import distributions
from dotenv import dotenv_values
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import extract, func
from flask import Response, request, send_file, stream_with_context
from flask_restplus import Resource, inputs, abort
from werkzeug import datastructures
from io import BytesIO
from fuzzywuzzy.fuzz import partial_ratio
from urllib.parse import urlencode
from api import app, api, cache, Flask_Session
from db import Post, File, Prefix
from url_parser import Hosts
from commons import get_mimetype
from config import load_config, save_config
from main import Scraper
from exceptions import AuthenticationError
from drive import (
    get_direct_url, get_direct_url2, get_file,
    get_drive, get_drive_project_ids, load_storage_cache,
    get_available_project_ids, get_active_project_id, get_all_files,
    upload_file
)
from pydrive.files import ApiRequestError

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def cache_key():
    args = request.args
    key = request.path + '?' + urlencode([
        (k, v) for k in sorted(args) for v in sorted(args.getlist(k))
    ])
    return key

section_entries_parser = api.parser()
section_entries_parser.add_argument("posts", type=int, help="Posts per page", location="args", default=20)
section_entries_parser.add_argument("sort_by", type=str, help="Sorting category", location="args", default="latest")
section_entries_parser.add_argument("hide_pinned", type=inputs.boolean, help="Include/exclude pinned posts", location="args", default=True)
section_entries_parser.add_argument("hide_deleted", type=inputs.boolean, help="Include/exclude deleted posts", location="args", default=False)
section_entries_parser.add_argument("prefix_raw_id", type=int, action="append", help="Filter by prefix", location="args", default=None)
section_entries_parser.add_argument("author", type=str, help="Filter by author", location="args", default=None)
section_entries_parser.add_argument("query", type=str, help="Search query", location="args", default=None)
@api.route("/section/<string:section_name>/<int:page>")
class SectionEntries(Resource):
    @api.expect(section_entries_parser)
        # @db_resource
    def get(self, section_name, page):
        args = section_entries_parser.parse_args()
        per_page = args["posts"]
        sort_by = args["sort_by"]
        hide_pinned = args["hide_pinned"]
        hide_deleted = args["hide_deleted"]
        prefix_raw_ids = args["prefix_raw_id"]
        author = args["author"]
        query = args["query"]
        section_id = Scraper.SECTIONS[section_name]["id"]

        session = Flask_Session()

        # Page starts at 0, i.e. page=0, posts=20 will get the 0-19 most recent posts and page=1, posts=20 will get 20-39 most recent posts.
        # 1) WHERE posts.section_id=`section_id`
        # 2) ORDER_BY posts.id DESC
        # 3) LIMIT `per_page`
        # 4) OFFSET `per_page * page`
        def filter_chain(filtered):
            if hide_deleted:
                filtered = filtered.filter((Post.deleted == False) | (Post.deleted == None))
            if prefix_raw_ids is not None:
                for prefix_raw_id in prefix_raw_ids:
                    prefix = session.query(Prefix).filter_by(id=prefix_raw_id).first()
                    # filtered = filtered.filter(Post.prefix == prefix.name)
                    # Post.prefixes is a JSON wrapper abstraction that is really just a Unicode string.
                    # This makes it difficult to do performant sorting on it, when it needs to be treated as a list.
                    filtered = filtered.filter(Post.prefixes.contains(prefix.name))
            if author is not None:
                filtered = filtered.filter(Post.created_by == author)
            if query is not None:
                files_filtered = [
                    file.post_id for file in session.query(File).filter(
                        File.file_name.contains(query)
                    )
                ]
                filtered = filtered.filter(
                    Post.title.contains(query) |
                    Post.created_by.contains(query) |
                    Post.body.contains(query) |
                    Post.id.in_(files_filtered)
                )
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
        if page > num_pages - 1:
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
            "per_page": per_page,
            "search_term": query
        }

@api.route("/sections")
class Sections(Resource):
    def get(self):
        return Scraper.SECTIONS

@api.route("/prefixes")
class Prefixes(Resource):
    @cache.cached(timeout=600, key_prefix=cache_key)
    def get(self):
        session = Flask_Session()
        prefixes = [prefix.serialize() for prefix in session.query(Prefix)]
        for prefix in prefixes:
            prefix["post_count"] = session.query(Post).filter(Post.prefixes.contains(prefix["name"])).count()
        session.close()
        return prefixes

user_search_parser = api.parser()
user_search_parser.add_argument("limit", type=int, help="Result limit", location="args", default=20)
@api.route("/users/<string:search>")
class UserSearch(Resource):
    @cache.cached(timeout=600,key_prefix=cache_key)
    @api.expect(user_search_parser)
    def get(self, search):
        args = user_search_parser.parse_args()
        limit = args["limit"]
        session = Flask_Session()
        users = [user[0] for user in session.query(Post.created_by).distinct().filter(Post.created_by.contains(search)).limit(limit)]
        session.close()
        return [
            {
                "name": user,
                "post_count": session.query(Post).filter_by(created_by=user).count()
            }
            for user in users
        ]

drive_files_parser = api.parser()
drive_files_parser.add_argument("files", type=int, help="Files per page", location="args", default=20)
drive_files_parser.add_argument("query", type=str, help="Search query", location="args", default=None)
# drive_files_parser.add_argument("page_token", type=str, help="Drive page token", location="args", default=None)
@api.route("/drive_files/<string:drive_id>/<int:page>")
class DriveFiles(Resource):
    # Only update drive results every 5 minutes.
    """ Could update this to automatically cache all the other pages since it needs to load them all regardless. """
    @cache.cached(timeout=300, key_prefix=cache_key)
    def get(self, drive_id, page):
        args = drive_files_parser.parse_args()
        per_page = args["files"]
        query = args["query"]
        logger.info(f"Grabbing uncached resource with args: {drive_id} {page} {per_page} {query}")
        """ In the future, to shorten response times, could return nextPageToken and use it to get the next page faster. """
        def match_file(file):
            # file_name = re.sub(r"\W+", " ", file["name"]).lower()
            file_name = file["title"].lower()
            return (
                (partial_ratio(file_name, query.lower()) > 80 if query is not None else True)
            )
        # page_token = args["page_token"]
        try:
            drive = get_drive(drive_id)
            drive_data = {}
            # drive_data = { "maxResults" : per_page }
            # if page_token is not None: drive_data["pageToken"] = page_token
            results = drive.ListFile(drive_data)
            files = results.GetList()
            files = [
                file for file in files if match_file(file)
            ]
            page_files = files[page * per_page : page*per_page + per_page]
            page_files = [
                {
                    k: v for (k, v) in f.items() if k in [
                        "kind", "id", "etag", "selfLink", "webContentLink", "alternateLink",
                        "embedLink", "iconLink", "title", "mimeType", "createdDate", "modifiedDate",
                        "downloadUrl", "originalFilename", "fileExtension", "md5Checksum", "fileSize",
                        "quotaBytesUsed", "ownerNames", "explicitlyTrashed"
                    ]
                } for f in page_files
            ]
            return {
                # e.g., page=0, per_page=20 => files[0:20]; page=2, per_page=5 => files[10:15]
                "files": page_files,
                "total": len(files),
                "pages": ceil(len(files) / per_page),
                "page": page,
                "per_page": per_page,
                # "page_token": page_token,
                # "next_page_token": page.metadata["nextPageToken"],
                "search_term": query,
            }
        except AuthenticationError as e:
            return abort(400, f"Invalid project ID '{drive_id}'.")
        except ZeroDivisionError as e:
            return abort(400, f"`files` param cannot be 0.")

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
            with open(os.path.join(os.path.dirname(__file__), "../", "pidfile"), "r") as f:
                pid = f.read()
        except FileNotFoundError:
            scraper_running = False
        try:
            with portalocker.Lock(os.path.join(os.path.dirname(__file__), "../", "status.json"), "r") as fh:
                status_data = json.load(fh)
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
        def partition_query(query, time_column, options):
            per_day = {
                "labels": [day.strftime("%A") for day in days],
                "data": [
                    query.filter(
                        extract('year', time_column) == day.year,
                        extract('month', time_column) == day.month,
                        extract('day', time_column) == day.day
                    ).count() for day in days
                ],
                "min": 2,
                "max": 14,
                "default": 7,
                "range": cur_range if sort == "days" else None,
                "y_label": options.get("y_label"),
                "label": options.get("label")
            }
            per_week = {
                "labels": [week.strftime("%B") + " " + str(week.day) for week in weeks],
                "data": [
                    query.filter(
                        extract('year', time_column) == week.year,
                        extract('month', time_column) == week.month,
                        func.strftime("%W", time_column) == week.strftime("%W")
                    ).count() for week in weeks
                ],
                "min": 2,
                "max": 16,
                "default": 8,
                "range": cur_range if sort == "weeks" else None,
                "y_label": options.get("y_label"),
                "label": options.get("label")
            }
            per_month = {
                "labels": [month.strftime("%B") for month in months],
                "data": [
                    query.filter(
                        extract('year', time_column) == month.year,
                        extract('month', time_column) == month.month
                    ).count() for month in months
                ],
                "min": 2,
                "max": 24,
                "default": 12,
                "range": cur_range if sort == "months" else None,
                "y_label": options.get("y_label"),
                "label": options.get("label")
            }
            return [per_day, per_week, per_month]
        def line_to_bar(data):
            # data is a list of datasets in form {days, weeks, months}
            # new_data is converted to bar form [label: str] -> count
            new_data = {}
            for dataset in data:
                # Days, weeks, months
                for (time_column, meta) in dataset.items():
                    label = meta["label"]
                    if not time_column in new_data:
                        new_data[time_column] = {
                            **meta,
                            "data": {}
                        }
                    if label not in new_data[time_column]["data"]:
                        new_data[time_column]["data"][label] = 0
                    new_data[time_column]["data"][label] += sum(meta["data"])
            for (time_column, data) in new_data.items():
                data["labels"] = list(data["data"].keys())
                data["data"] = list(data["data"].values())
                data["label"] = data["labels"]
            return [new_data]
            # return {
            #     **meta,
            #     "labels": list(new_data.keys()),
            #     "data": list(new_data.values())
            # }

        [scrapes_per_day, scrapes_per_week, scrapes_per_month] = partition_query(
            session.query(Post),
            time_column=Post.first_scraped,
            options={"y_label": "Posts"}
        )
        [files_per_day, files_per_week, files_per_month] = partition_query(
            session.query(File).filter((File.unknown == False) | (File.unknown == None)),
            time_column=File.first_scraped,
            options={"y_label": "Files"}
        )
        host_distribution_data = [
            {
                "days": days,
                "weeks": weeks,
                "months": months
            } for (days, weeks, months) in [
                partition_query(
                    session.query(File).filter(File.hosting_service == hosting_service.name),
                    time_column=File.first_scraped,
                    options={"y_label": "Hosts", "label": hosting_service.name}
                )
                for hosting_service in Hosts
            ]
        ]

        post_count = session.query(Post).count()
        known_file_count = session.query(File).filter((File.unknown == False) | (File.unknown == None)).count()
        total_file_count = session.query(File).count()

        """
        drive = get_drive()
        about = drive.GetAbout()
        drive_quota_used = int(about["quotaBytesUsed"])
        drive_quota_total = int(about["quotaBytesTotal"])
        drive_user = about["name"]
        drive_project = about[]
        """
        project_ids = get_drive_project_ids()
        available_project_ids = get_available_project_ids()
        active_project_id = get_active_project_id()
        drive_storage_cache = load_storage_cache()
        drive_data = {}
        for project_id in project_ids:
            drive_data[project_id] = {
                "available": project_id in available_project_ids,
                "in_use": project_id == active_project_id,
                **drive_storage_cache[project_id]
            }

        session.close()

        with open(os.path.join(os.path.dirname(__file__), "../", "requirements.txt"), "r") as req_txt:
            required_dependencies = [{"name": req.name, "version": str(req.specifier)} for req in pkg_resources.parse_requirements(req_txt)]
        installed_dependencies = [{"name": dist.metadata["name"], "version": dist.version} for dist in list(distributions())]

        return {
            "data": {
                "scrape_data": {
                    "graphs": {
                        "posts_scraped": {
                            "title": "Posts scraped",
                            "type": "line",
                            "data": [{
                                "days": scrapes_per_day,
                                "weeks": scrapes_per_week,
                                "months": scrapes_per_month
                            }]
                        },
                        "files_scraped": {
                            "title": "Files scraped",
                            "type": "line",
                            "data": [{
                                "days": files_per_day,
                                "weeks": files_per_week,
                                "months": files_per_month
                            }]
                        },
                        "host_distribution_line": {
                            "title": "Hosting services  (line)",
                            "type": "line",
                            "data": host_distribution_data
                        },
                        "host_distribution_bar": {
                            "title": "Hosting services (bar)",
                            "type": "bar",
                            "data": line_to_bar(host_distribution_data)
                        }
                    },
                    "default_graph": "posts_scraped",
                    "post_count": post_count,
                    "known_file_count": known_file_count,
                    "total_file_count": total_file_count,
                }
            },
            "status": {
                "running": scraper_running,
                "pid": pid if scraper_running else None,
                "last_scraped": last_scraped,
                "last_error": last_error,
                "most_recent_post": most_recent_post.serialize() if most_recent_post else None,
                "account_info": {
                    "leakthis_username": leakthis_username,
                    "leakthis_password": leakthis_password,
                    "leakthis_user_agent": leakthis_user_agent,
                    "drive": drive_data
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

@api.route("/download_url/<int:file_id>")
class DownloadURL(Resource):
    def get(self, file_id):
        session = Flask_Session()
        file = session.query(File).filter_by(id=file_id).first()
        if file is None:
            session.close()
            return abort(404, f"File with id '{file_id}' does not exist.")
        if file.unknown:
            session.close()
            return abort(404, f"File with id '{file_id}' is not downloaded.")
        drive_id = file.drive_id
        session.close()
        return get_direct_url2(drive_id)

direct_download_parser = api.parser()
direct_download_parser.add_argument("download", type=inputs.boolean, help="Download as attachment rather than inline.", location="args", default=True, required=False)
@api.route("/download/<int:file_id>")
class DirectDownload(Resource):
    # @cache.cached(timeout=3600, key_prefix=cache_key)
    def get(self, file_id):
        args = direct_download_parser.parse_args()

        attachment = args.get("download", True)

        session = Flask_Session()
        file = session.query(File).filter_by(id=file_id).first()
        if file is None:
            session.close()
            return abort(404, f"File with id '{file_id}' does not exist.")
        if file.unknown:
            session.close()
            return abort(404, f"File with id '{file_id}' is not downloaded.")
        drive_file = get_file(file.drive_project_id, file.drive_id)
        try:
            drive_file.FetchContent()
        except ApiRequestError as e:
            session.close()
            return abort(404, f"Could not download file with id '{file_id}'.", drive_error=True)
        # Could also get Drive's inferred mimetype from file.FetchMetadata() and file["mimeType"],
        # but it's more accurate to just go off of the file name in the first place.
        file_name = file.file_name
        mimetype = get_mimetype(file.file_name)
        session.close()

        def stream_file():
            chunk = drive_file.content.read(8192)
            while len(chunk) != 0:
                yield chunk
                chunk = drive_file.content.read(8192)
        response = send_file(
            drive_file.content,
            conditional=True,
            mimetype=mimetype
        )
        drive_file.content.seek(0)
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
config_parser.add_argument("check_deleted_interval", type=int, help="Check deleted interval", location="form", required=False)
config_parser.add_argument("check_deleted_depth", type=int, help="Check deleted depth", location="form", required=False)
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
        subsequent_pages_scraped = form.get("subsequent_pages_scraped")
        check_deleted_interval = form.get("check_deleted_interval")
        check_deleted_depth = form.get("check_deleted_depth")

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

        if subsequent_pages_scraped is not None:
            config["subsequent_pages_scraped"] = subsequent_pages_scraped
        
        if check_deleted_interval is not None:
            config["check_deleted_interval"] = check_deleted_interval

        if check_deleted_depth is not None:
            config["check_deleted_depth"] = check_deleted_depth

        save_config(config)

        return config
        # print_posts_scraped = form.get("print_posts_scraped")
        # log_level = form.get("log_level")