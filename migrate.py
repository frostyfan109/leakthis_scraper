import requests
import json
from db import *
from drive import drive, get_direct_url
from commons import get_cover

files = persistent_session.query(File)
for file in files:
    with open("migrated.json", "r") as f:
        migrated = json.load(f)
    if file.unknown or file.id in migrated:
        print(f"Skipping '{file.file_name}'")
        continue

    res = requests.get(get_direct_url(file.drive_id))
    cover = get_cover(res.content)

    file.cover = cover
    print(f"Finished migrating '{file.file_name}' ({cover is not None}).")
    persistent_session.commit()

    with open("migrated.json", "w") as f:
        migrated.append(file.id)
        json.dump(migrated, f)
