SHELL := /bin/bash

init:
	@python setup.py develop
	@pip install -r requirements.txt

test:
	rm -f .coverage
	@nosetests -sv --with-coverage ./tests/

publish:
	python setup.py sdist bdist_wheel upload
