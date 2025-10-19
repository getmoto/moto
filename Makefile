SHELL := /bin/bash

SERVICE_NAME = "default"
TEST_NAMES = "*"

ifeq ($(TEST_SERVER_MODE), true)
	# Exclude parallel tests
	TEST_EXCLUDE := --ignore tests/test_acm --ignore tests/test_amp --ignore tests/test_awslambda --ignore tests/test_batch --ignore tests/test_ec2 --ignore tests/test_sqs
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
	@echo "Running ruff..."
	ruff check moto tests
	ruff format --check moto tests
	@echo "Running MyPy..."
	mypy --install-types --non-interactive

format:
	ruff format moto/ tests/
	ruff check --fix moto/ tests/

test-only:
	rm -f .coverage
	MOTO_CALL_RESET_API=false pytest -sv -n auto tests --dist loadscope

test: lint test-only

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
