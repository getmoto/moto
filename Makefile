SHELL := /bin/bash

init:
	python setup.py develop
	pip install -r requirements.txt

test:
	rm .coverage
	nosetests --with-coverage ./tests/
