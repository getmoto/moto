import re
from typing import Optional, TypedDict


class _docker_config(TypedDict, total=False):
    use_docker: bool


class _passthrough_config(TypedDict, total=False):
    services: list[str]
    urls: list[str]


class _core_config(TypedDict, total=False):
    mock_credentials: bool
    passthrough: _passthrough_config
    reset_boto3_session: bool
    service_whitelist: Optional[list[str]]


class _iam_config(TypedDict, total=False):
    load_aws_managed_policies: bool


class _sfn_config(TypedDict, total=False):
    execute_state_machine: bool


class _iot_config(TypedDict, total=False):
    use_valid_cert: bool


DefaultConfig = TypedDict(
    "DefaultConfig",
    {
        "batch": _docker_config,
        "core": _core_config,
        "lambda": _docker_config,
        "iam": _iam_config,
        "stepfunctions": _sfn_config,
        "iot": _iot_config,
    },
    total=False,
)

default_user_config: DefaultConfig = {
    "batch": {"use_docker": True},
    "lambda": {"use_docker": True},
    "core": {
        "mock_credentials": True,
        "passthrough": {"urls": [], "services": []},
        "reset_boto3_session": True,
        # Important: When whitelisting a new service, make sure to unskip the service test suite in Makefile
        "service_whitelist": [
            "acm",
            "acmpca",
            "apigateway",
            "applicationautoscaling",
            "autoscaling",
            "awslambda",  # Not used by LocalStack but has cross-service dependency within Moto
            "ce",
            "cloudformation",  # Not used by LocalStack but has cross-service dependency within Moto
            "cloudwatch",
            "codebuild",
            "codecommit",
            "codedeploy",
            "codepipeline",
            "cognitoidentity",
            "cognitoidp",  # Not used by LocalStack but has cross-service dependency within Moto
            "config",
            "dynamodb",  # Not used by LocalStack but has cross-service dependency within Moto
            "ec2",
            "ecr",
            "ecs",  # Not used by LocalStack but has cross-service dependency within Moto
            "efs",
            "elb",
            "elbv2",
            "emr",
            "events",
            "glacier",
            "iam",
            "identitystore",
            "instance_metadata",  # Not used by LocalStack but has cross-service dependency within Moto
            "iot",
            "iotdata",
            "kms",  # Not used by LocalStack but has cross-service dependency within Moto
            "logs",
            "managedblockchain",
            "moto_api._internal",  # Not used by LocalStack but has cross-service dependency within Moto
            "organizations",  # Not used by LocalStack but has cross-service dependency within Moto
            "pinpoint",
            "ram",
            "rds",  # Not used by LocalStack but has cross-service dependency within Moto
            "redshift",
            "resourcegroups",
            "resourcegroupstaggingapi",
            "route53",
            "route53resolver",
            "s3",  # Not used by LocalStack but has cross-service dependency within Moto
            "s3control",
            "sagemaker",
            "scheduler",
            "secretsmanager",
            "ses",
            "shield",
            "sns",  # Not used by LocalStack but has cross-service dependency within Moto
            "sqs",  # Not used by LocalStack but has cross-service dependency within Moto
            "ssm",
            "ssoadmin",
            "sts",
            "support",
            "swf",
            "textract",
            "transcribe",
            "wafv2",
            "xray",
        ],
    },
    "iam": {"load_aws_managed_policies": False},
    "stepfunctions": {"execute_state_machine": False},
    "iot": {"use_valid_cert": False},
}


def service_whitelisted(service: str) -> bool:
    services_whitelisted = default_user_config.get("core", {}).get("service_whitelist")
    return services_whitelisted is None or service in services_whitelisted


def passthrough_service(service: str) -> bool:
    passthrough_services = (
        default_user_config.get("core", {}).get("passthrough", {}).get("services", [])
    )
    return service in passthrough_services


def passthrough_url(clean_url: str) -> bool:
    passthrough_urls = (
        default_user_config.get("core", {}).get("passthrough", {}).get("urls", [])
    )
    return any(re.match(url, clean_url) for url in passthrough_urls)


def mock_credentials() -> bool:
    return (
        default_user_config.get("core", {}).get("mock_credentials", True) is not False
    )
