SHELL := /bin/bash

SERVICE_NAME = "default"
TEST_NAMES = "*"

ifeq ($(TEST_SERVER_MODE), true)
	# Exclude parallel tests
	TEST_EXCLUDE := --ignore tests/test_acm --ignore tests/test_amp --ignore tests/test_awslambda --ignore tests/test_batch --ignore tests/test_dynamodb --ignore tests/test_ec2 --ignore tests/test_s3/ --ignore tests/test_sqs
	# Parallel tests will be run separate
	PARALLEL_TESTS := ./tests/test_acm/ ./tests/test_acmpca/ ./tests/test_amp/ ./tests/test_awslambda ./tests/test_dynamodb ./tests/test_ec2 ./tests/test_s3/ ./tests/test_sqs
else
	TEST_EXCLUDE := --ignore tests/test_batch --ignore tests/test_dynamodb --ignore tests/test_ec2 --ignore tests/test_s3/ --ignore tests/test_sqs
	PARALLEL_TESTS := ./tests/test_dynamodb ./tests/test_ec2 tests/test_s3/ ./tests/test_sqs
endif

# Skip testing services that are not whitelisted for LocalStack
WHITELIST_EXCLUDE := --ignore tests/test_amp
WHITELIST_EXCLUDE += --ignore tests/test_apigatewaymanagementapi
WHITELIST_EXCLUDE += --ignore tests/test_appconfig
WHITELIST_EXCLUDE += --ignore tests/test_appmesh
WHITELIST_EXCLUDE += --ignore tests/test_appsync
WHITELIST_EXCLUDE += --ignore tests/test_athena
WHITELIST_EXCLUDE += --ignore tests/test_backup
WHITELIST_EXCLUDE += --ignore tests/test_batch
WHITELIST_EXCLUDE += --ignore tests/test_batch_simple
WHITELIST_EXCLUDE += --ignore tests/test_bedrock
WHITELIST_EXCLUDE += --ignore tests/test_bedrockagent
WHITELIST_EXCLUDE += --ignore tests/test_budgets
WHITELIST_EXCLUDE += --ignore tests/test_clouddirectory
WHITELIST_EXCLUDE += --ignore tests/test_cloudfront
WHITELIST_EXCLUDE += --ignore tests/test_cloudhsmv2
WHITELIST_EXCLUDE += --ignore tests/test_cloudtrail
WHITELIST_EXCLUDE += --ignore tests/test_comprehend
WHITELIST_EXCLUDE += --ignore tests/test_connect
WHITELIST_EXCLUDE += --ignore tests/test_connectcampaigns
WHITELIST_EXCLUDE += --ignore tests/test_databrew
WHITELIST_EXCLUDE += --ignore tests/test_datapipeline
WHITELIST_EXCLUDE += --ignore tests/test_datasync
WHITELIST_EXCLUDE += --ignore tests/test_dax
WHITELIST_EXCLUDE += --ignore tests/test_directconnect
WHITELIST_EXCLUDE += --ignore tests/test_dms
WHITELIST_EXCLUDE += --ignore tests/test_ds
WHITELIST_EXCLUDE += --ignore tests/test_dsql
WHITELIST_EXCLUDE += --ignore tests/test_dynamodbstreams
WHITELIST_EXCLUDE += --ignore tests/test_dynamodb_v20111205
WHITELIST_EXCLUDE += --ignore tests/test_ebs
WHITELIST_EXCLUDE += --ignore tests/test_ec2instanceconnect
WHITELIST_EXCLUDE += --ignore tests/test_efs
WHITELIST_EXCLUDE += --ignore tests/test_eks
WHITELIST_EXCLUDE += --ignore tests/test_elasticache
WHITELIST_EXCLUDE += --ignore tests/test_elasticbeanstalk
WHITELIST_EXCLUDE += --ignore tests/test_emrcontainers
WHITELIST_EXCLUDE += --ignore tests/test_emrserverless
WHITELIST_EXCLUDE += --ignore tests/test_es
WHITELIST_EXCLUDE += --ignore tests/test_firehose
WHITELIST_EXCLUDE += --ignore tests/test_forecast
WHITELIST_EXCLUDE += --ignore tests/test_fsx
WHITELIST_EXCLUDE += --ignore tests/test_glue
WHITELIST_EXCLUDE += --ignore tests/test_greengrass
WHITELIST_EXCLUDE += --ignore tests/test_guardduty
WHITELIST_EXCLUDE += --ignore tests/test_inspector2
WHITELIST_EXCLUDE += --ignore tests/test_ivs
WHITELIST_EXCLUDE += --ignore tests/test_kafka
WHITELIST_EXCLUDE += --ignore tests/test_kinesis
WHITELIST_EXCLUDE += --ignore tests/test_kinesisanalyticsv2
WHITELIST_EXCLUDE += --ignore tests/test_kinesisvideo
WHITELIST_EXCLUDE += --ignore tests/test_kinesisvideoarchivedmedia
WHITELIST_EXCLUDE += --ignore tests/test_lakeformation
WHITELIST_EXCLUDE += --ignore tests/test_lexv2models
WHITELIST_EXCLUDE += --ignore tests/test_macie
WHITELIST_EXCLUDE += --ignore tests/test_mediaconnect
WHITELIST_EXCLUDE += --ignore tests/test_medialive
WHITELIST_EXCLUDE += --ignore tests/test_mediapackage
WHITELIST_EXCLUDE += --ignore tests/test_mediapackagev2
WHITELIST_EXCLUDE += --ignore tests/test_mediastore
WHITELIST_EXCLUDE += --ignore tests/test_mediastoredata
WHITELIST_EXCLUDE += --ignore tests/test_memorydb
WHITELIST_EXCLUDE += --ignore tests/test_meteringmarketplace
WHITELIST_EXCLUDE += --ignore tests/test_mq
WHITELIST_EXCLUDE += --ignore tests/test_neptune
WHITELIST_EXCLUDE += --ignore tests/test_networkfirewall
WHITELIST_EXCLUDE += --ignore tests/test_networkmanager
WHITELIST_EXCLUDE += --ignore tests/test_opensearch
WHITELIST_EXCLUDE += --ignore tests/test_opensearchserverless
WHITELIST_EXCLUDE += --ignore tests/test_osis
WHITELIST_EXCLUDE += --ignore tests/test_panorama
WHITELIST_EXCLUDE += --ignore tests/test_personalize
WHITELIST_EXCLUDE += --ignore tests/test_pipes
WHITELIST_EXCLUDE += --ignore tests/test_polly
WHITELIST_EXCLUDE += --ignore tests/test_quicksight
WHITELIST_EXCLUDE += --ignore tests/test_rdsdata
WHITELIST_EXCLUDE += --ignore tests/test_redshiftdata
WHITELIST_EXCLUDE += --ignore tests/test_rekognition
WHITELIST_EXCLUDE += --ignore tests/test_resiliencehub
WHITELIST_EXCLUDE += --ignore tests/test_resourcegroupstaggingapi
WHITELIST_EXCLUDE += --ignore tests/test_route53domains
WHITELIST_EXCLUDE += --ignore tests/test_s3bucket_path
WHITELIST_EXCLUDE += --ignore tests/test_s3tables
WHITELIST_EXCLUDE += --ignore tests/test_s3vectors
WHITELIST_EXCLUDE += --ignore tests/test_sagemakermetrics
WHITELIST_EXCLUDE += --ignore tests/test_sagemakerruntime
WHITELIST_EXCLUDE += --ignore tests/test_sdb
WHITELIST_EXCLUDE += --ignore tests/test_securityhub
WHITELIST_EXCLUDE += --ignore tests/test_servicecatalog
WHITELIST_EXCLUDE += --ignore tests/test_servicecatalogappregistry
WHITELIST_EXCLUDE += --ignore tests/test_servicediscovery
WHITELIST_EXCLUDE += --ignore tests/test_servicequotas
WHITELIST_EXCLUDE += --ignore tests/test_sesv2
WHITELIST_EXCLUDE += --ignore tests/test_signer
WHITELIST_EXCLUDE += --ignore tests/test_stepfunctions
WHITELIST_EXCLUDE += --ignore tests/test_synthetics
WHITELIST_EXCLUDE += --ignore tests/test_timestreaminfluxdb
WHITELIST_EXCLUDE += --ignore tests/test_timestreamquery
WHITELIST_EXCLUDE += --ignore tests/test_timestreamwrite
WHITELIST_EXCLUDE += --ignore tests/test_transfer
WHITELIST_EXCLUDE += --ignore tests/test_vpclattice
WHITELIST_EXCLUDE += --ignore tests/test_workspaces
WHITELIST_EXCLUDE += --ignore tests/test_workspacesweb

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
	rm -rf cover
	pytest -sv -rs --cov=moto --cov-report xml ./tests/ $(TEST_EXCLUDE) $(WHITELIST_EXCLUDE)
	# https://github.com/aws/aws-xray-sdk-python/issues/196 - Run these tests separately without Coverage enabled
	pytest -sv -rs ./tests/test_xray
	# Run tests that require a clean slate
	pytest -sv --cov=moto --cov-report xml --cov-append ./tests/ $(WHITELIST_EXCLUDE) -m requires_clean_slate
	# Run parallel tests - except those that require a clean slate
	MOTO_CALL_RESET_API=false pytest -sv --cov=moto --cov-report xml --cov-append -n 4 $(PARALLEL_TESTS) $(WHITELIST_EXCLUDE) --dist loadscope -m "not requires_clean_slate"

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
