# Leakthis Scraper
## Components
This project consists of 3 components:
- Scraper/parser
- Webapp
- REST API

### Scraper/Parser
The scraper and parser are responsible for scraping the website, parsing media-referencing URLs within posts and resolving their direct download URLs, caching media to Google Drive, and saving data to an SQLite DB.

The scraper and parser are built using:
- Beautiful Soup 4
- TinyCSS 2
- SQLAlchemy
- pydrive
- pytest

Note: the Scraper is currently not updated to function with the newest version of the [site](https://leaked.cx). Additionally, the media parser is not updated to support the parsing of up-to-date file hosters such as [dropbay](https://dropbay.net).

### Webapp
The webapp is an interface for the responsive viewing, sorting, and playback of scraped content.

The webapp are built using:
- React
- Redux/React-Redux
- Bootstrap 4/React-Bootstrap

### REST API
The API facilitates interaction between the Scraper/DB and the webapp.

The API is built using:
- Flask
- Flask-RESTPlus

## Usage
### Scraper
1) Create a virtual environment using Python 3.7.x
2) Install `requirements.txt`
3) Create `credentials.json`, containing keys `username`, `password`, `user-agent`. The website requires an account to access certain sections of the forum, so it is important that one is provided to the scraper.
4) Create `drive_credentials.json`, which should be a JSON keyfile. To get a keyfile, setup a Google project and create a service account with Drive permissions.
5) Run `python main.py`

###
Webapp
1) Install `package.json` using `npm install`
2) Run `npm start`

### REST API
1) Run `python routes.py`