import pytest
import os
import json
from uuid import uuid4
from io import BytesIO
from .mock_filesystem import file_mocker
from .mock_env import mock_env, MOCKING

DRIVE_CREDENTIALS_FILE = "drive_credentials_tmp.json"
DRIVE_STORAGE_CACHE_PATH = "drive_storage_cache.json"

DRIVE_DIR = "drive_tmp"
class DriveFile:
    def __init__(self, drive, data):
        self.__drive = drive
        self.content = data.get("content")
        self.id = data.get("id", str(uuid4()))
    def Upload(self):
        self.__drive._upload(self)
    def FetchContent(self):
        self.content = self.__drive._get_file(self)
    def InsertPermission(self, *args, **kwargs):
        pass
    def __getitem__(self, key):
        return getattr(self, key)
class Drive:
    def __init__(self, file_mocker, project_id):
        self.file_mocker = file_mocker
        self.project_id = project_id
    
    def _get_file_path(self, drive_file):
        return os.path.join(DRIVE_DIR, self.project_id, drive_file.id)

    def _upload(self, drive_file):
        file_path = self._get_file_path(drive_file)
        # `drive_file.content` must be defined to invoke `drive_file.Upload`
        drive_file.content.seek(0)
        self.file_mocker.mock_file(file_path, drive_file.content.read())
    
    def _get_file(self, drive_file):
        file_path = self._get_file_path(drive_file)
        with open(file_path, "rb") as f:
            return BytesIO(f.read())
    
    @property
    def mocked_files(self):
        file_dir = os.path.join(self.file_mocker.tmp_path, DRIVE_DIR, self.project_id)
        try:
            return [os.path.join(file_dir, i) for i in os.listdir(file_dir)]
        except:
            # Dir has not been created yet -> no files have been created
            return []

    def CreateFile(self, data):
        return DriveFile(self, data)
    def GetAbout(self):
        total_bytes = 0
        for fp in self.mocked_files:
            total_bytes += os.path.getsize(fp)
        return {
            "quotaBytesUsed": total_bytes,
            "quotaBytesTotal": 16106127360
        }

def get_drive(file_mocker, project_id):
    return Drive(file_mocker, project_id)

""" Mocking should always be enabled on Google Drive. """
@pytest.fixture
def mock_drive(file_mocker, mock_env, monkeypatch):
    file_mocker.mock_file("settings.yaml")

    file_mocker.mock_file(DRIVE_STORAGE_CACHE_PATH, "{}")

    # drive.py uses glob to determine the file paths from DRIVE_CREDENTIALS_FILE
    # which means that it does not look in the temp directory unless explicitly told to.
    (_, tmp_path) = file_mocker.create_tmp_file(DRIVE_CREDENTIALS_FILE, json.dumps({
        "project_id": "mocked_drive_project"
    }))
    fp = os.path.abspath(tmp_path)
    file_mocker._mock_file(fp, tmp_path)
    mock_env("DRIVE_CREDENTIALS_FILE", fp)

    # file_mocker and mock_env already take $MOCKING into account. The following does not.
    # if not MOCKING: return

    monkeypatch.setattr("drive.get_drive", lambda project_id: get_drive(file_mocker, project_id))