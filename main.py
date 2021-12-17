import pidfile
from dotenv import load_dotenv
from scraper import Scraper
from db import session_factory

if __name__ == "__main__":
    load_dotenv()
    with pidfile.PIDFile():
        def post_added(post_id):
            session = session_factory()
            print(f"Archived new post '{session.query(Post).filter_by(native_id=post_id).first().title}'.")
            session.close()

        scraper = Scraper()
        scraper.scrape_hip_hop_leaks(post_added)
    # scraper.scrape_posts("hip-hop-leaks", pages=1)
    # post_ids = scraper.parse_posts(requests.get("https://leakth.is/forums/hip-hop-leaks.10/").content, "hip-hop-leaks")
