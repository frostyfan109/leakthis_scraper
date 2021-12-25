PYTHON = python

install.web:
	cd web; \
	npm install;

install.python:
	${PYTHON} -m pip install -r requirements.txt

install:
	install.python install.web

run.web:
	cd web; \
	npm start;

run.scraper:
	${PYTHON} main.py

run.api:
	${PYTHON} api.py

run.conversion_api:
	${PYTHON} audio_conversion_api.py

run:
	run.web run.scraper run.api run.conversion_api

test.python:
	${PYTHON} -m pytest tests

test.web:
	cd web; \
	npm test;

test:
	test.python test.web