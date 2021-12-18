# Leakthis Scraper
Web scraping service that catalogs the contents of [leaked.cx](leaked.cx).

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
- PyDrive
- (minimal) Selenium/ChromeDriver
- pytest

### Webapp
The webapp is an interface for the responsive viewing, sorting, and playback of scraped content.

The webapp are built using:
- React
- Bootstrap 4/React-Bootstrap

### REST API
The API facilitates bidirectional interaction between the Scraper/DB and the webapp.

The API is built using:
- Flask
- Flask-RESTPlus

## Usage
This project expects Python >=3.7.x.
A `.env` file is required and should be configured before running the scraper/API. See `.env.sample` for reference.

```bash
$ make install
$ make run
```
The scraper can also be run by providing the `--username` argument, e.g.:
```bash
$ make install
$ make run.api
$ make run.web
$ python main.py --username {XXX}
```