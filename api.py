import logging
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
import flask.scaffold
flask.helpers._endpoint_from_view_func = flask.scaffold._endpoint_from_view_func
from flask import Flask
from flask_restplus import Api
# from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_caching import Cache
from flask_socketio import SocketIO
from db import flask_session_factory

logger = logging.getLogger(__file__)

app = Flask(__name__)
app.config.from_mapping({
    "CACHE_TYPE": "simple",
    # 5 mins
    "CACHE_DEFAULT_TIMEOUT": 300
})
CORS(app)
socket = SocketIO(app, cors_allowed_origins="*", path="/ws", async_mode="threading")
api = Api(app)
cache = Cache(app)

# app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI

# db = SQLAlchemy(app)

Flask_Session = flask_session_factory()
# Note: `session` sometimes appears to be undefined when using this, so it's
# not in usage. Not sure if this is an underlying issue with session instantiation
# or the decorator itself.
# db_resource is a decorator which injects a flask-ready SQLAlchemy session
# into the function's global namespace. It then closes the session after the
# function has completed. Not sure if this is bad practice, but was aiming to
# replicate the feel of Flask's contexts such as `request`.
def db_resource(func):
    def inner(*args, **kwargs):
        g = func.__globals__
        sentinel = object()

        __SESSION__ = Flask_Session()

        old_value = g.get("session", sentinel)
        g["session"] = __SESSION__


        try:
            r = func(*args, **kwargs)
        finally:
            if old_value is sentinel:
                del g["session"]
            else:
                g["session"] = old_value

        __SESSION__.close()

        return r
    return inner


@app.teardown_request
def cleanup(res_or_exc):
    Flask_Session.remove()


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    from urllib.parse import urlsplit
    from commons import get_env_var
    load_dotenv()
    
    from routes import *
    parser = argparse.ArgumentParser(description="Specify API arguments")
    # parser.add_argument("--host", action="store", default="0.0.0.0")
    # parser.add_argument("--port", action="store", default=8001, type=int)
    parser.add_argument("-r", "--reloader", help="Automatically restart API upon modification", action="store_true", default=True)
    args = parser.parse_args()

    api_url = urlsplit(get_env_var("API_URL"))
    # host = f"{api_url.scheme}://{api_url.hostname}"
    host = api_url.hostname
    port = api_url.port

    app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=args.reloader,
        threaded=True
    )
