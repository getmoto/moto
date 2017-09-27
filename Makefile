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

aws_managed_policies:
	scripts/update_managed_policies.py

upload_pypi_artifact:
	python setup.py sdist bdist_wheel upload

push_dockerhub_image:
	docker build -t motoserver/moto .
	docker push motoserver/moto

tag_github_release:
	git tag `python setup.py --version`
	git push origin `python setup.py --version`

publish: upload_pypi_artifact push_dockerhub_image tag_github_release

scaffold:
	@pip install -r requirements-dev.txt > /dev/null
	exec python scripts/scaffold.py
