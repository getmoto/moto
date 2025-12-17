from unittest import SkipTest

import boto3
import pytest
import requests

from moto import mock_aws, settings
from moto.awslambda.models import LambdaBackend
from moto.awslambda.utils import get_backend
from moto.awslambda_simple.models import LambdaSimpleBackend
from moto.core import DEFAULT_ACCOUNT_ID
from moto.core.config import default_user_config
from moto.core.exceptions import ServiceNotWhitelisted


@mock_aws
def test_change_configuration_using_api() -> None:
    assert default_user_config["batch"] == {"use_docker": True}
    assert default_user_config["lambda"] == {"use_docker": True}

    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )
    resp = requests.get(f"http://{base_url}/moto-api/config")
    assert resp.json()["batch"] == {"use_docker": True}
    assert resp.json()["lambda"] == {"use_docker": True}

    # Update a single configuration item
    requests.post(
        f"http://{base_url}/moto-api/config", json={"batch": {"use_docker": False}}
    )

    resp = requests.get(f"http://{base_url}/moto-api/config")
    assert resp.json()["batch"] == {"use_docker": False}
    assert resp.json()["lambda"] == {"use_docker": True}

    if settings.TEST_DECORATOR_MODE:
        isinstance(get_backend(DEFAULT_ACCOUNT_ID, "us-east-1"), LambdaBackend)

    # Update multiple configuration items
    requests.post(
        f"http://{base_url}/moto-api/config",
        json={"batch": {"use_docker": True}, "lambda": {"use_docker": False}},
    )

    resp = requests.get(f"http://{base_url}/moto-api/config")
    assert resp.json()["batch"] == {"use_docker": True}
    assert resp.json()["lambda"] == {"use_docker": False}

    if settings.TEST_DECORATOR_MODE:
        isinstance(get_backend(DEFAULT_ACCOUNT_ID, "us-east-1"), LambdaSimpleBackend)

    # reset
    requests.post(
        f"http://{base_url}/moto-api/config",
        json={"batch": {"use_docker": True}, "lambda": {"use_docker": True}},
    )


def test_whitelist() -> None:
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this anywhere else")

    with mock_aws(config={"core": {"service_whitelist": ["s3"]}}):
        dynamodb = boto3.client("dynamodb", "us-east-1")
        s3 = boto3.client("s3", "us-east-1")

        # S3 is whitelisted, so all calls are allowed
        s3.list_buckets()

        # DynamoDB is not whitelisted
        with pytest.raises(ServiceNotWhitelisted):
            dynamodb.list_tables()

    # Empty whitelist, so no calls are allowed
    with mock_aws(config={"core": {"service_whitelist": []}}):
        with pytest.raises(ServiceNotWhitelisted):
            s3.list_buckets()

        with pytest.raises(ServiceNotWhitelisted):
            dynamodb.list_tables()

    # Both are whitelisted, so both are allowed
    with mock_aws(config={"core": {"service_whitelist": ["dynamodb", "s3"]}}):
        s3.list_buckets()

        dynamodb.list_tables()
