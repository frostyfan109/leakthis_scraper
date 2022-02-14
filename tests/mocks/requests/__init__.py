"""
This directory should contain .py files that define mocked responses.

A mocked response is a dict in compliance with the following schema:
---
- content?: bytes|function - Binary data or callback that returns binary data.
- text?: str|function - String data or callback that returns string data.
- cookies?: requests.cookies.RequestsCookieJar|dict - Cookie jar returned by response.
- headers?: dict - Headers returned by response.
- reason?: str - Textual explanation of response status code.
- json?: str|function - Dict representing `text` parsed as JSON or callback that returns such a dict.
- raw?: object|function - File-like object representation of response or callback that returns such an object.
- status_code?: int - Status code of response.

See:
- https://github.com/jamielennox/requests-mock/blob/34f840fd66d2c03d273206e18f48a219c853a34b/requests_mock/response.py#L211
- https://docs.python-requests.org/en/latest/api/#requests.Response
"""

import os

requests_path = os.path.join(os.path.dirname(__file__), "mock_requests")

def load_mock_file(file_path):
    with open(os.path.join(requests_path, file_path), "rb") as f:
        return f.read()