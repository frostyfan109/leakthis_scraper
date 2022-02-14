import pytest
import requests_mock
import os
from .util import MockedObject
from .mock_env import MOCKING
from .requests.base import GET_BASE
from .requests.login import POST_LOGIN
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
    mocker.register_uri(mocked_request.method, mocked_request.url, response_list=[mocked_request.response])

class HTTP:
    def __init__(self, method, url, response):
        self.method = method
        self.url = url
        self.response = response
class GET(HTTP):
    def __init__(self, *args, **kwargs):
        super().__init__("GET", *args, **kwargs)
class POST(HTTP):
    def __init__(self, *args, **kwargs):
        super().__init__("POST", *args, **kwargs)

class MockRequest:
    class Base:
        GET = GET(base_url, GET_BASE)
    class Login:
        POST = POST(base_url + "/login/login", POST_LOGIN)