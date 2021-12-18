import pidfile
import argparse
import keyring
from dotenv import load_dotenv
from getpass import getpass
from scraper import Scraper
from db import session_factory, Post
from exceptions import AuthenticationError

KEYRING_SERVICE = "leakthis_scraper"

if __name__ == "__main__":
    load_dotenv()
    with pidfile.PIDFile():
        # This has been disabled since both the API and Scraper should have the same environments.
        # In the future, this could be changed to configure individual CONFIG_PATH values themselves,
        # which would be more useful.
        """
        parser = argparse.ArgumentParser(description="Override env configuration")
        parser.add_argument("-s", "--scraper", action="store", default=None, help="LEAKTHIS_CREDENTIALS_FILE")
        parser.add_argument("-d", "--drive", action="store", default=None, help="DRIVE_CREDENTIALS_FILE")
        parser.add_argument("-c", "--config", action="store", default=None, help="CONFIG_PATH")

        args = parser.parse_args()
        if args.scraper: os.environ["LEAKTHIS_CREDENTIALS_FILE"] = args.scraper
        if args.drive: os.environ["DRIVE_CREDENTIALS_FILE"] = args.drive
        if args.config: os.environ["CONFIG_PATH"] = args.config
        """

        parser = argparse.ArgumentParser(description="Leakthis credential override")
        parser.add_argument("-n", "--username", action="store", default=None, help="Leakthis username")
        # parser.add_argument("-p", "--password", action="store", default=None, help="Leakthis password")

        args = parser.parse_args()
        
        username = args.username
        credentials = None
        # Only construct credentials if username is provided. Otherwise it is assumed that they will be accessible
        # through environment vars.
        if username is not None:
            password = keyring.get_password(KEYRING_SERVICE, username)
            if password is None:
                password = getpass()
                keyring.set_password(KEYRING_SERVICE, username, password)
            credentials = {
                "username": username,
                "password": password
            }
        

        # if (username is not None) ^ (password is not None):
            # parser.error("--username and --password must be given together.")


        def post_added(post_id):
            session = session_factory()
            print(f"Archived new post '{session.query(Post).filter_by(native_id=post_id).first().title}'.")
            session.close()

        try:
            scraper = Scraper(credentials)
        except AuthenticationError as e:
            if username is not None:
                # Delete the password if it could be invalid.
                # It's also possible that authentication simply failed for another reason,
                # but this is much less painless since that's for the most part a fringe case.
                keyring.delete_password(KEYRING_SERVICE, username)
            raise e
        scraper.scrape_hip_hop_leaks(post_added)
    # scraper.scrape_posts("hip-hop-leaks", pages=1)
    # post_ids = scraper.parse_posts(requests.get("https://leakth.is/forums/hip-hop-leaks.10/").content, "hip-hop-leaks")
