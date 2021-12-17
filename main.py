import pidfile
import argparse
from dotenv import load_dotenv
from scraper import Scraper
from db import session_factory, Post

if __name__ == "__main__":
    load_dotenv()
    with pidfile.PIDFile():
        parser = argparse.ArgumentParser(description="Override env configuration")
        parser.add_argument("-s", "--scraper", action="store", default=None, help="LEAKTHIS_CREDENTIALS_FILE")
        parser.add_argument("-d", "--drive", action="store", default=None, help="DRIVE_CREDENTIALS_FILE")
        parser.add_argument("-c", "--config", action="store", default=None, help="CONFIG_PATH")

        args = parser.parse_args()
        if args.scraper: os.environ["LEAKTHIS_CREDENTIALS_FILE"] = args.scraper
        if args.drive: os.environ["DRIVE_CREDENTIALS_FILE"] = args.drive
        if args.config: os.environ["CONFIG_PATH"] = args.config


        def post_added(post_id):
            session = session_factory()
            print(f"Archived new post '{session.query(Post).filter_by(native_id=post_id).first().title}'.")
            session.close()

        scraper = Scraper()
        scraper.scrape_hip_hop_leaks(post_added)
    # scraper.scrape_posts("hip-hop-leaks", pages=1)
    # post_ids = scraper.parse_posts(requests.get("https://leakth.is/forums/hip-hop-leaks.10/").content, "hip-hop-leaks")
