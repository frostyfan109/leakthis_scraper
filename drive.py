import logging
import traceback
import os
from pydrive.auth import GoogleAuth, ServiceAccountCredentials
from pydrive.drive import GoogleDrive
from httplib2 import Http
from apiclient.discovery import build
from io import BytesIO
from exceptions import MissingEnvironmentError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__file__)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('oauth2client.transport').setLevel(logging.ERROR)
logging.getLogger('oauth2client.client').setLevel(logging.ERROR)

def get_drive_credentials_path():
    value = os.environ.get("DRIVE_CREDENTIALS_FILE", "")
    if value == "":
        raise MissingEnvironmentError("DRIVE_CREDENTIALS_FILE")
    return value

def get_drive():
    gauth = GoogleAuth()
    scopes = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(get_drive_credentials_path(), scopes)
    drive = GoogleDrive(gauth)
    return drive

drive = get_drive()

def upload_file(file_name, stream):
    drive = get_drive()
    file = drive.CreateFile({"title": file_name})
    file.content = BytesIO(stream)
    file.Upload()
    file.InsertPermission({
        "type": "anyone",
        "value": "anyone",
        "role": "reader"
    })
    return file["id"]


def get_file(id):
    drive = get_drive()
    file = drive.CreateFile({"id": id})
    return file

def get_direct_url(id):
    drive = get_drive()
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