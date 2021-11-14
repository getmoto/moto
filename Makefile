SHELL := /bin/bash

ifeq ($(TEST_SERVER_MODE), true)
	# exclude test_kinesisvideoarchivedmedia
	# because testing with moto_server is difficult with data-endpoint
	TEST_EXCLUDE := -k 'not (test_kinesisvideoarchivedmedia or test_awslambda or test_batch or test_ec2 or test_sqs)'
	# Parallel tests will be run separate
	PARALLEL_TESTS := ./tests/test_awslambda ./tests/test_batch ./tests/test_ec2 ./tests/test_sqs
else
	TEST_EXCLUDE :=
	PARALLEL_TESTS := ./tests/test_core
endif

init:
	@python setup.py develop
	@pip install -r requirements-dev.txt

lint:
	flake8 moto
	black --check moto/ tests/
	pylint -j 0 tests

format:
	black moto/ tests/

test-only:
	rm -f .coverage
	rm -rf cover
	pytest -sv --cov=moto --cov-report xml ./tests/ $(TEST_EXCLUDE)
	MOTO_CALL_RESET_API=false pytest -n 4 $(PARALLEL_TESTS)

test: lint test-only

test_server:
	@TEST_SERVER_MODE=true pytest -sv --cov=moto --cov-report xml ./tests/

aws_managed_policies:
	scripts/update_managed_policies.py

implementation_coverage:
	./scripts/implementation_coverage.py
	git commit IMPLEMENTATION_COVERAGE.md -m "Updating implementation coverage" || true

scaffold:
	@pip install -r requirements-dev.txt > /dev/null
	exec python scripts/scaffold.py

int_test:
	@./scripts/int_test.sh
