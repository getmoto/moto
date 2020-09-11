SHELL := /bin/bash

ifeq ($(TEST_SERVER_MODE), true)
	# exclude test_iot and test_iotdata for now
	# because authentication of iot is very complicated

	# exclude test_kinesisvideoarchivedmedia
	# because testing with moto_server is difficult with data-endpoint

	TEST_EXCLUDE :=  --exclude='test_iot.*' --exclude="test_kinesisvideoarchivedmedia.*"
else
	TEST_EXCLUDE :=
endif

init:
	@python setup.py develop
	@pip install -r requirements-dev.txt

lint:
	flake8 moto
	black --check moto/ tests/

test-only:
	rm -f .coverage
	rm -rf cover
	@nosetests -sv --with-coverage --cover-html ./tests/ $(TEST_EXCLUDE)


test: lint test-only

test_server:
	@TEST_SERVER_MODE=true nosetests -sv --with-coverage --cover-html ./tests/

aws_managed_policies:
	scripts/update_managed_policies.py

upload_pypi_artifact:
	python setup.py sdist bdist_wheel
	twine upload dist/*

push_dockerhub_image:
	docker build -t motoserver/moto .
	docker push motoserver/moto

tag_github_release:
	git tag `python setup.py --version`
	git push origin `python setup.py --version`

publish: upload_pypi_artifact \
	tag_github_release \
	push_dockerhub_image

implementation_coverage:
	./scripts/implementation_coverage.py
	git commit IMPLEMENTATION_COVERAGE.md -m "Updating implementation coverage" || true

scaffold:
	@pip install -r requirements-dev.txt > /dev/null
	exec python scripts/scaffold.py
