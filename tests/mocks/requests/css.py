from . import load_mock_file

STYLESHEETS = {
    "normalize.css": "style1.css",
    "notices.less": "style2.css",
    "md-icons.css": "md-icons.css"
}

GET_STYLE = lambda n: {
    "content": load_mock_file(STYLESHEETS[n])
}