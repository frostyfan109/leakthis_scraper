import logging
from flask import Flask
from flask_restplus import API
from flask_cors import CORS
"""
** Current functionality is still located in the web API. **

In the future, data such as Drive read/write, Scraper status/pidfile, Scraper config, and other file-read operations should be moved
into here.

This will be important once the server is multithreaded, as currently this data is handled via thread-unsafe read/writes.

Also, will be able to update log level of API to be in line with the Scraper config's log level value.
"""

logger = logging.getLogger(__file__)
app = Flask(__name__)
CORS(app)
api = Api(app)

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="Specify API arguments")
    parser.add_argument("--host", action="store", default="0.0.0.0")
    parser.add_argument("--port", action="store", default=8002, type=int)
    parser.add_argument("-r", "--reloader", help="Automatically restart API upon modification", action="store_true", default=True)
    args = parser.parse_args()

    app.run(
        host=args.host,
        port=args.port,
        use_reloader=args.reloader
    )