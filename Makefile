PYTHON          := /usr/bin/env python3
VIRTUALENV_NAME := "venv"

venv: venv.touchfile
venv.touchfile: requirements.txt
	test -d venv || ${PYTHON} -m venv $(VIRTUALENV_NAME)
	. venv/bin/activate
	touch venv/touchfile

install.web:
	cd web; \
	npm install;

install.python: venv
	. venv/bin/activate; ${PYTHON} -m pip install -r requirements.txt --use-deprecated=legacy-resolver

install: install.python install.web;

run.web:
	cd web; \
	npm start;

run.scraper: venv
	. venv/bin/activate; ${PYTHON} main.py

run.api: venv
	. venv/bin/activate; ${PYTHON} api.py

run.conversion_api: venv
	. venv/bin/activate; ${PYTHON} audio_conversion_api.py

run: run.web run.scraper run.api run.conversion_api

test.python: venv
	. venv/bin/activate; export TESTING=true&&export TESTS_MOCKING=true&&${PYTHON} -m pytest tests; \
	export TESTING=true&&export TESTS_MOCKING=false&&${PYTHON} -m pytest tests

test.web:
	cd web; \
	npm test;

test: test.python test.web