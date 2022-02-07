from flask import send_from_directory
from api import app, api
from commons import get_env_var

static_dir = get_env_var("STATIC_DIRECTORY")

@app.route("/static_test/<path:path>")
def static_route(path):
    return send_from_directory(static_dir, path)