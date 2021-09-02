from io import BytesIO
from mutagen import File as MutagenFile

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
    ending = endings.get(value[-1].lower())
    if not ending:
        return int(value)
    return int(value[:-1]) * ending

def get_cover(stream):
    id3 = MutagenFile(BytesIO(stream))
    if id3 is not None and hasattr(id3, "tags") and id3.tags is not None and "APIC:" in id3.tags:
        return id3.tags["APIC:"].data