import os
from url_parser import URLParser, GoFile, OnlyFilesIo

url_parser = URLParser()

SHORT = True

mock_files = [
    {
        "file_name": "file_audio1.mp3",
        "file_data": open(os.path.join(os.path.dirname(__file__), "mocks", "audio", "audio1.mp3"), "rb")
    },
    {
        "file_name": "file_audio2.mp3",
        "file_data": open(os.path.join(os.path.dirname(__file__), "mocks", "audio", "audio2.mp3"), "rb")
    }
]

for file in mock_files:
    file["file_length"] = len(file["file_data"].read())
    file["file_data"].seek(0)

if SHORT: files = [mock_files[0]]
else: files = mock_files

def _test_hosting_service(host):
    urls = host.upload_files(files)
    # Reset file for next read
    for file in files:
        file["file_data"].seek(0)
    for i in range(len(files)):
        url = urls[i]
        file = files[i]
        download = url_parser.download(url)
        assert download[0]["file_name"] == file["file_name"]
        # Service may perform compression, but files should still be the same length. 
        assert len(download[0]["stream"]) == file["file_length"]
        # assert download[0]["stream"] == file["file_data"]
        
def test_onlyfiles_io():
    _test_hosting_service(OnlyFilesIo())

def test_gofile():
    _test_hosting_service(GoFile())
    # url = GoFile().upload_files([file])[0]
    # url = "https://goffile.io/d/Vl9QtA"