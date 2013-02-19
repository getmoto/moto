SHELL := /bin/bash

init:
	python setup.py develop
	pip install -r requirements.txt

test:
	nosetests --with-coverage ./tests/ --cover-package=moto

travis:
	nosetests ./tests/
