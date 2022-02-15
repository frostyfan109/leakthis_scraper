import pytest
import requests_mock
import os
import json
import glob
from urllib.parse import parse_qs
from .util import MockedObject
from .mock_env import MOCKING
from .requests.base import GET_BASE
from .requests.login import POST_LOGIN
from .requests.static import GET_LOGO, GET_FAVICON
from .requests.section import GET_HIPHOPLEAKS
from .requests.css import GET_STYLE
from .requests import requests_path
from scraper import Scraper

base_url = Scraper.base_url

""" This fixture would be named requests_mock as well, but pytest does not like importing fixtures under new aliases. """
@pytest.fixture
def mock_requests(requests_mock):
    if not MOCKING:
        requests_mock.real_http = True
        requests_mock._real_http = True
        return MockedObject(requests_mock)
    return requests_mock


def load_mock_request(mocker, mocked_request):
    mocker.register_uri(mocked_request.method, mocked_request.url, response_list=[mocked_request.response], **mocked_request.kwargs)
    for required_mock in mocked_request.required:
        load_mock_request(required_mock)

def load_mocks_from_directory(directory, glob_pattern="*.json"):
    mocks = []
    for file_path in glob.glob(os.path.join(directory, glob_pattern)):
        mock_data = json.load(open(file_path, "r"))
        method = mock_data["method"].upper()
        if method == "GET":
            HTTP_METHOD = GET
        elif method == "POST":
            HTTP_METHOD = POST
        else: raise Exception("Unknown HTTP method in JSON mock: ", method, file_path)
        mock = HTTP_METHOD(base_url + mock_data["url"], {
            "content": open(os.path.join(directory, mock_data["file"]), "rb").read()
        })
        mocks.append(mock)
    return mocks

class HTTP:
    def __init__(self, method, url, response, required=[], **kwargs):
        self.method = method
        self.url = url
        self.response = response
        self.required = required
        # Pass kwargs as extra options to register_uri
        self.kwargs = kwargs
class GET(HTTP):
    def __init__(self, *args, **kwargs):
        super().__init__("GET", *args, **kwargs)
class POST(HTTP):
    def __init__(self, *args, **kwargs):
        super().__init__("POST", *args, **kwargs)

def qs_matcher(request, sub_qs):
    qs = parse_qs(request.query)
    sub_qs = parse_qs(sub_qs)
    for qs_arg in sub_qs:
        if not qs_arg in qs or qs[qs_arg] != sub_qs[qs_arg]:
            return False
    return True

class MockRequest:
    class Base:
        GET = GET(base_url, GET_BASE)
    class Login:
        POST = POST(base_url + "/login/login", POST_LOGIN)
    class Static:
        class Logo:
            GET = lambda url: GET(url, GET_LOGO)
        class Favicon:
            GET = lambda url: GET(url, GET_FAVICON)
        Stylesheets = [
            GET(
                base_url + "/css.php",
                GET_STYLE("normalize.css"),
                additional_matcher=lambda req: qs_matcher(req, "css=public%3Anormalize.css%2Cpublic%3Afa.css%2Cpublic%3Acore.less%2Cpublic%3Aapp.less")
            ),
            GET(
                base_url + "/css.php",
                GET_STYLE("notices.less"),
                additional_matcher=lambda req: qs_matcher(req, "css=public%3Anotices.less%2Cpublic%3Aprefix_menu.less%2Cpublic%3Aselect2.less%2Cpublic%3Astructured_list.less%2Cpublic%3Asv_multiprefix_prefix_input.less%2Cpublic%3Auix.less%2Cpublic%3Auix_socialmedia.less%2Cpublic%3Axfes_suggested_threads.less%2Cpublic%3Aextra.less")
            ),
            GET(
                base_url + "/styles/uix_dark/fonts/icons/material-icons/css/materialdesignicons.min.css",
                GET_STYLE("md-icons.css")
            )
        ]
    class Section:
        class HipHopLeaks:
            GET = lambda url: GET(url, GET_HIPHOPLEAKS)
    class SectionPosts:
        HipHopLeaks = load_mocks_from_directory(os.path.join(requests_path, "hip_hop_leaks_posts"))