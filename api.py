import logging
from flask import Flask
from flask_restplus import Api
# from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from db import DB_URI, Base, flask_session_factory

logger = logging.getLogger(__file__)

app = Flask(__name__)
CORS(app)
api = Api(app)

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
