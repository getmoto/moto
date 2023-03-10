SHELL := /bin/bash

ifdef SERVICE_NAME
TEST_SERVICE = and ${SERVICE_NAME}
TEST_SERVICE_DIR = test_${SERVICE_NAME}
TF_SERVICE_NAME = ${SERVICE_NAME}
MYPY_EXPLICIT_FILES ?= moto/${SERVICE_NAME}/*.py*
endif

TF_SERVICE_NAME ?= default
TEST_NAMES ?= "*"

# Parallel tests will be run separate
# -m tags are specified in tests/conftest.py, or on individual files/tests
ifeq ($(TEST_SERVER_MODE), true)
	TEST_EXCLUDE := -m "not parallel and not parallel_server_only and not skip_server ${TEST_SERVICE}"
	PARALLEL_TESTS := -m "parallel or parallel_server_only ${TEST_SERVICE}"
else
	TEST_EXCLUDE := -m "not parallel ${TEST_SERVICE}"
	PARALLEL_TESTS := -m "parallel ${TEST_SERVICE}"
endif

init:
	@pip install -e .
	@pip install -r requirements-dev.txt

lint:
	@echo "Running flake8..."
	flake8 moto/${SERVICE_NAME} tests/${TEST_SERVICE_DIR}
	@echo "Running black... "
	$(eval black_version := $(shell grep "^black==" requirements-dev.txt | sed "s/black==//"))
	@echo "(Make sure you have black-$(black_version) installed, as other versions will produce different results)"
	black --check moto/${SERVICE_NAME} tests/${TEST_SERVICE_DIR}
	@echo "Running pylint..."
	pylint -j 0 moto/${SERVICE_NAME} tests/${TEST_SERVICE_DIR}
	@echo "Running MyPy..."
	if [[ "${SKIP_MYPY}" == "" ]]; then mypy --install-types --non-interactive ${MYPY_EXPLICIT_FILES}; else echo "Skipping"; fi

format:
	black moto/ tests/

test-only:
	rm -f .coverage
	rm -rf cover
	pytest -sv --cov=moto --cov-report xml ./tests $(TEST_EXCLUDE) ${PYTEST_ARGS}
	# https://github.com/aws/aws-xray-sdk-python/issues/196 - Run these tests separately without Coverage enabled
	if [[ "${SERVICE_NAME}" == "" || "${SERVICE_NAME}" == "xray" ]]; then pytest -sv ./tests/test_xray ${PYTEST_ARGS}; else echo "Skipping"; fi
	MOTO_CALL_RESET_API=false pytest --cov=moto --cov-report xml --cov-append -n 4 $(PARALLEL_TESTS) ${PYTEST_ARGS}

test: lint test-only
	@echo "USAGE: make test [SERVICE_NAME=s3] [SKIP_MYPY=true]"
	@echo "     defaults to all services and running mypy (not all services are mypy proof, see also setup.cfg)"

terraformtests:
	@echo "Make sure that the MotoServer is already running on port 4566 (moto_server -p 4566)"
	@echo "USAGE: make terraformtests SERVICE_NAME=acm TEST_NAMES=TestAccACMCertificate"
	@echo ""
	cd tests/terraformtests && bin/run_go_test $(TF_SERVICE_NAME) "$(TEST_NAMES)"

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
