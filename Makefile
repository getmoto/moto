SHELL := /bin/bash

SERVICE_NAME = "default"
TEST_NAMES = "*"

ifeq ($(TEST_SERVER_MODE), true)
	# exclude test_kinesisvideoarchivedmedia
	# because testing with moto_server is difficult with data-endpoint
	TEST_EXCLUDE := --ignore tests/test_kinesisvideoarchivedmedia --ignore tests/test_acm --ignore tests/test_amp --ignore tests/test_awslambda --ignore tests/test_batch --ignore tests/test_ec2 --ignore tests/test_sqs
	# Parallel tests will be run separate
	PARALLEL_TESTS := ./tests/test_acm/ ./tests/test_acmpca/ ./tests/test_amp/ ./tests/test_awslambda ./tests/test_batch ./tests/test_ec2 ./tests/test_sqs
else
	TEST_EXCLUDE := --ignore tests/test_batch --ignore tests/test_ec2 --ignore tests/test_sqs
	PARALLEL_TESTS := ./tests/test_batch ./tests/test_ec2 ./tests/test_sqs
endif

init:
	@pip install -e .
	@pip install -r requirements-dev.txt

lint:
	@echo "Running flake8..."
	flake8 moto tests
	@echo "Running black... "
	$(eval black_version := $(shell grep "^black==" requirements-dev.txt | sed "s/black==//"))
	@echo "(Make sure you have black-$(black_version) installed, as other versions will produce different results)"
	black --check moto/ tests/
	@echo "Running pylint..."
	pylint -j 0 moto tests
	@echo "Running MyPy..."
	mypy --install-types --non-interactive

format:
	black moto/ tests/

test-only:
	rm -f .coverage
	rm -rf cover
	pytest -sv -rs --cov=moto --cov-report xml ./tests/ $(TEST_EXCLUDE)
	# https://github.com/aws/aws-xray-sdk-python/issues/196 - Run these tests separately without Coverage enabled
	pytest -sv -rs ./tests/test_xray
	MOTO_CALL_RESET_API=false pytest -rs --cov=moto --cov-report xml --cov-append -n 4 $(PARALLEL_TESTS)

test: lint test-only

terraformtests:
	@echo "Make sure that the MotoServer is already running on port 4566 (moto_server -p 4566)"
	@echo "USAGE: make terraformtests SERVICE_NAME=acm TEST_NAMES=TestAccACMCertificate"
	@echo ""
	cd tests/terraformtests && bin/run_go_test $(SERVICE_NAME) "$(TEST_NAMES)"

publish:
	python -m build
	twine upload dist/*

test_server:
	@TEST_SERVER_MODE=true pytest -sv --cov=moto --cov-report xml ./tests/

aws_managed_policies:
	scripts/update_managed_policies.py

implementation_coverage:
	./scripts/implementation_coverage.py
	git commit IMPLEMENTATION_COVERAGE.md -m "Updating implementation coverage" || true

cloudformation_coverage:
	./scripts/cloudformation_coverage.py
	git commit CLOUDFORMATION_COVERAGE.md -m "Updating CloudFormation coverage" || true

coverage: implementation_coverage cloudformation_coverage

scaffold:
	@pip install -r requirements-dev.txt > /dev/null
	exec python scripts/scaffold.py

int_test:
	@./scripts/int_test.sh
