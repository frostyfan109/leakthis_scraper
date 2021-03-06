import os
from io import BytesIO
from mimetypes import guess_type
from mutagen import File as MutagenFile
from exceptions import MissingEnvironmentError

""" Get a required environment variable. """
def get_env_var(var):
    value = os.environ.get(var, "")
    if value == "":
        raise MissingEnvironmentError(var)
    return value

def assert_is_ok(res):
    if not res.ok:
        res.raise_for_status()

def unabbr_number(value):
    # Convert sql string to <t>
    endings = {
        "k": 1000,
        "m": 1000000,
        "b": 1000000000
    }
    value = value.strip()
    ending = endings.get(value[-1].lower())
    if not ending:
        return int(value)
    return int(value[:-1]) * ending

def get_cover(stream):
    id3 = MutagenFile(BytesIO(stream))
    if id3 is not None and hasattr(id3, "tags") and id3.tags is not None and "APIC:" in id3.tags:
        return id3.tags["APIC:"].data

def get_mimetype(file_name):
    """ Extend to include common mimetypes that mimetypes doesn't properly support. """
    common_types = {
        ".m4a": "audio/x-m4a",
        ".rar": "application/x-rar-compressed",
        ".7z": "application/x-7z-compressed",
        ".aac": "audio/aac"
    }
    for key in common_types:
        if file_name.endswith(key):
            return common_types[key]
    return guess_type(file_name)[0]