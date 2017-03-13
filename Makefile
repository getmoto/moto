SHELL := /bin/bash

init:
	@python setup.py develop
	@pip install -r requirements.txt

lint:
	flake8 moto

test: lint
	rm -f .coverage
	rm -rf cover
	@nosetests -sv --with-coverage --cover-html ./tests/

test_server:
	@TEST_SERVER_MODE=true nosetests -sv --with-coverage --cover-html ./tests/

publish:
	python setup.py sdist bdist_wheel upload
