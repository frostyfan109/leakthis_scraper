import pytest
import os
from unittest.mock import patch
from .mock_env import MOCKING

class NoMockFile(Exception):
    def __init__(self, rel_file_path, abs_file_path):
        super().__init__(f"File path not mocked: {rel_file_path} -> {abs_file_path}")
        self.rel_file_path = rel_file_path
        self.abs_file_path = abs_file_path

class FileMocker:
    def __init__(self, monkeypatch, tmpdir, options):
        self.tmp_path = tmpdir.mkdir("temp_mocks")
        self.mocked_files = {}
        self._open = open

        # If False, monkeypatching will be disabled.
        enabled = options.get("enabled", True)
        
        if enabled: monkeypatch.setattr("builtins.open", self.mock_open)

    # @property
    # def enabled(self):
    #     return self._enabled

    # @enabled.setter
    # def enabled(self, value):
    #     if value:
    #         self._monkeypatch.setattr("builtins.open", self.mock_open)
    #     else:
    #         self._monkeypatch.setattr("builtins.open", self._open)
    #     self._enabled = value

    """ Create a temporary mockfile and write `value` to it. """
    def mock_file(self, file_path, value=None):
        (abs_path, tmp_path) = self.create_tmp_file(file_path, value)
        self._mock_file(abs_path, tmp_path)
        return tmp_path
    
    def _mock_file(self, abs_path, tmp_path):
        self.mocked_files[abs_path] = tmp_path

    def create_tmp_file(self, file_path, value=None):
        file_path = os.path.abspath(file_path)
        tmp_path = self.tmp_path / os.path.relpath(file_path)
        dir_head = os.path.split(tmp_path)[0]
        os.makedirs(dir_head, exist_ok=True)
        if value is not None:
            mode = "wb+" if isinstance(value, bytes) else "w+"
            with self._open(tmp_path, mode) as fh:
                fh.write(value)
        return (file_path, tmp_path)

    """ Whitelist a file path from mocking (escape hatch). """
    def whitelist_file(self, file_path):
        self.mocked_files[file_path] = file_path

    """ Whitelist every file in a directory. `recursive` will whitelist subdirectories recursively. """
    def whitelist_directory(self, path, recursive=False):
        for f_or_dir in os.listdir(path):
            is_dir = os.path.isdir(os.path.join(path, f_or_dir))
            if not is_dir:
                self.whitelist_file(os.path.join(path, f_or_dir))
            elif recursive:
                self.whitelist_directory(os.path.join(path, f_or_dir))

    def mock_open(self, file_path, *args, **kwargs):
        _fp = file_path
        file_path = os.path.abspath(file_path)
        try:
            mocked_path = self.mocked_files[file_path]
        except KeyError:
            raise NoMockFile(_fp, file_path)
        return self._open(mocked_path, *args, **kwargs)


""" Mocking should always be enabled on the filesystem. """
@pytest.fixture
def file_mocker(monkeypatch, tmpdir):
    f_mocker = FileMocker(monkeypatch, tmpdir, {
        "enabled": True
    })
    return f_mocker

# @pytest.fixture
# def file_mocker(monkeypatch, tmpdir):
#     f_mocker = FileMocker(monkeypatch, tmpdir, {
#         "enabled": MOCKING
#     })
#     if not MOCKING:
#         return MockedObject(f_mocker)
#     return f_mocker