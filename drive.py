import logging
import traceback
import os
import json
import glob
import portalocker
from pydrive.auth import GoogleAuth, ServiceAccountCredentials
from pydrive.drive import GoogleDrive
from httplib2 import Http
from apiclient.discovery import build
from io import BytesIO
from itertools import chain
from dotenv import load_dotenv
from commons import get_env_var
from exceptions import MissingEnvironmentError, AuthenticationError, StorageError

load_dotenv()

logger = logging.getLogger(__file__)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('oauth2client').setLevel(logging.ERROR)
# logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)
# logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
# logging.getLogger('oauth2client.transport').setLevel(logging.ERROR)
# logging.getLogger('oauth2client.client').setLevel(logging.ERROR)

# Drive projects will stop being used once their storage usage reaches DRIVE_STORAGE_CUTOFF.
try:
    DRIVE_STORAGE_CUTOFF = get_env_var("DRIVE_STORAGE_CUTOFF")
except MissingEnvironmentError:
    DRIVE_STORAGE_CUTOFF = ".975"
DRIVE_STORAGE_CUTOFF = float(DRIVE_STORAGE_CUTOFF)

def load_storage_cache():
    try:
        with portalocker.Lock("drive_storage_cache.json", "r") as fh:
            cache = json.load(fh)
    except FileNotFoundError:
        # If the file doesn't exist yet, create the cache and populate it.
        cache = update_storage_cache({})
    
    return cache

def update_storage_cache(cache, project_id=None):
    if project_id is None: ids = get_drive_project_ids()
    else: ids = [project_id]
    for project_id in ids:
        [quota_used, quota_total] = get_storage_quota(project_id)
        cache[project_id] = {
            "quota_used": quota_used,
            "quota_total": quota_total
        }
    save_storage_cache(cache)
    return cache

def save_storage_cache(cache):
    with portalocker.Lock("drive_storage_cache.json", "w+") as fh:
        json.dump(cache, fh)

def get_drive_credential_paths():
    value = get_env_var("DRIVE_CREDENTIALS_FILE")
    
    glob_expressions = value.split(",")
    # Get lists of file paths and flatten.
    paths = list(chain.from_iterable([glob.glob(glob_expr) for glob_expr in glob_expressions]))
    return paths

""" Get the Project ID of a JSON key file from its path. """
def get_project_id(path):
    with open(path, "r") as f:
        try:
            credentials = json.load(f)
            return credentials["project_id"]
        except FileNotFoundError as e:
            raise AuthenticationError(f"Could not locate JSON key file with path '{path}'.")
        except (json.JSONDecodeError, KeyError) as e:
            raise AuthenticationError(f"Invalid JSON key file with path '{path}'.")

""" Get the path for a key file from its project_id.
    - Validates that every key file exists, is valid JSON, and has a project_id key.
    - Does not validate whether or not each file is a valid key file (use get_drive). """
def get_drive_credential_path(project_id):
    paths = get_drive_credential_paths()
    for path in paths:
        if get_project_id(path) == project_id:
            key_file_path = path
    try:
        return key_file_path
    except NameError:
        raise AuthenticationError(f"Could not locate JSON key file with Project ID '{project_id}'.")

def get_drive_project_ids():
    return [get_project_id(path) for path in get_drive_credential_paths()]
    

""" Get a pydrive.GoogleDrive instance from a project_id.
    Validates that:
    - each key file exists
    - each key file is valid JSON
    - key file corresponding to`project_id` is a valid key file. """
def get_drive(project_id):
    gauth = GoogleAuth()
    scopes = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(get_drive_credential_path(project_id), scopes)
    drive = GoogleDrive(gauth)
    return drive

def get_inactive_project_ids():
    active_project_id = get_active_project_id()
    return [project_id for project_id in get_drive_project_ids() if project_id != active_project_id]
def get_available_project_ids():
    storage_cache = load_storage_cache()
    available = []
    for project_id in get_drive_project_ids():
        quota_used = storage_cache[project_id]["quota_used"]
        quota_total = storage_cache[project_id]["quota_total"]
        if (quota_used / quota_total) < DRIVE_STORAGE_CUTOFF:
            available.append(project_id)
    return available
""" Find the first Drive project that is under the storage cutoff. """
def get_active_project_id():
    try:
        return get_available_project_ids()[0]
    except IndexError:
        storage_breakdown = get_storage_breakdown(storage_cache)
        raise StorageError(f"Every Drive project is above the storage cutoff of {DRIVE_STORAGE_CUTOFF * 100}%. Breakdown: {', '.join(storage_breakdown)}.")

def get_active_drive():
    return get_drive(get_active_project_id())

def upload_file(file_name, stream):
    project_id = get_active_project_id()
    drive = get_drive(project_id)
    file = drive.CreateFile({"title": file_name})
    file.content = BytesIO(stream)
    file.Upload()
    file.InsertPermission({
        "type": "anyone",
        "value": "anyone",
        "role": "reader"
    })
    update_storage_cache(load_storage_cache())
    return (project_id, file["id"])


def get_file(project_id, id):
    drive = get_drive(project_id)
    file = drive.CreateFile({"id": id})
    return file

def get_direct_url(project_id, id):
    drive = get_drive(project_id)
    file = drive.CreateFile({"id": id})
    try:
        return file["webContentLink"]
    except:
        # File does not exist. This should never happen.
        logger.critical(f"File with id '{id}' does not exist.")
        traceback.print_exc()
        return None

def get_direct_url2(id):
    return "https://drive.google.com/uc?id=" + id + "&export=download"

def get_storage_quota(project_id=None):
    if project_id is None:
        project_id = get_active_project_id()
    drive = get_drive(project_id)
    about = drive.GetAbout()
    drive_quota_used = int(about["quotaBytesUsed"])
    drive_quota_total = int(about["quotaBytesTotal"])
    return [drive_quota_used, drive_quota_total]


def get_storage_breakdown(storage_cache):
    update_storage_cache(load_storage_cache())
    storage_breakdown = []
    for project_id in storage_cache:
        val = storage_cache[project_id]
        storage_used = val['quota_used'] / val['quota_total']
        storage_usage = round((storage_used) * 1000) / 10
        storage_breakdown.append(
            f"{project_id} ({storage_usage}%)" + (" [FULL]" if storage_used >= DRIVE_STORAGE_CUTOFF else " [AVAILABLE]")
        )
    return storage_breakdown

def get_drive_breakdown():
    storage_breakdown = get_storage_breakdown(load_storage_cache())
    N_L = "\n"
    return f"""
Google Drive initialized with project ids: {", ".join(get_drive_project_ids())}.

Storage breakdown ({DRIVE_STORAGE_CUTOFF * 100}% cutoff):
- {(N_L + "- ").join(storage_breakdown)}
    """.strip()

def get_all_files(project_id):
    return get_drive(project_id).ListFile().GetList()