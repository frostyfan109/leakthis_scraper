import logging
import time
import ffmpeg
import tempfile
import os
import math
from flask import Flask, send_file
from flask_restplus import Api, Resource
from flask_cors import CORS
from werkzeug import datastructures
from subprocess import Popen, PIPE
from io import BytesIO
from commons import get_mimetype

"""
Seemed appropriate to separate this functionality into a standalone API that can be run if desired.

The webapp will use this API's endpoints to convert file types that don't have native support in browsers
to better-supported formats.

Note that this expects FFmpeg binaries to be in locatable in path.
"""

app = Flask(__name__)
CORS(app)
api = Api(app)

app.logger.setLevel(logging.INFO)

convert_audio_parser = api.parser()
convert_audio_parser.add_argument("file", type=datastructures.FileStorage, location="files")
@api.route("/convert_audio/<string:in_filename>/<string:out_filename>")
class ConvertAudio(Resource):
    @api.expect(convert_audio_parser)
    def post(self, in_filename, out_filename):
        args = convert_audio_parser.parse_args()
        file = args["file"]

        if in_filename.find(".") == -1:
            # Extension
            in_filename = "_." + in_filename
        if out_filename.find(".") == -1:
            # Extension
            out_filename = "_." + out_filename

        in_ext = in_filename.split(".")[-1]
        out_ext = out_filename.split(".")[-1]

        out_args = {
            "loglevel": "quiet",
            "b:a": "320k",
            "vn": None,
            "movflags": "+faststart",
        }
        app.logger.info(f"Converting {in_filename} to {out_filename}.")
        """ Need to use a temp file to move the moov atom of mp4/m4a containers to the front using qt-faststart.
            Since it's piping the input into ffmpeg, there's no FS search for the metadata, so the moov atom
            has to be at the front or it will be considered corrupted. """
        # delete=False to ensure read/write perms.
        t = time.time()
        tmp = tempfile.NamedTemporaryFile(delete=False)
        with open(tmp.name, "wb") as tmpf:
            tmpf.write(file.read())
        """ Note: demuxing isn't supported for m4a. """
        arg = ffmpeg.input(tmp.name, format=in_ext).output("pipe:", format=out_ext, **out_args).compile()
        process = Popen(arg, stdout=PIPE)
        stdout_bytes = process.communicate()[0]
        process.terminate()
        # Cleanup temp file.
        tmp.close()
        os.unlink(tmp.name)
        
        app.logger.info(f"Spent {math.floor(time.time() - t)}s converting from {in_filename} to {out_filename}.")
        response = send_file(
            BytesIO(stdout_bytes),
            conditional=True,
            attachment_filename=out_filename,
            mimetype=get_mimetype(out_filename)
        )
        response.headers.set("Content-Length", str(len(stdout_bytes)))
        return response

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
        use_reloader=args.reloader,
        threaded=True
    )