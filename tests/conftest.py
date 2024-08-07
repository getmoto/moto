import boto3
import pytest

from moto import mock_aws


@pytest.fixture(scope="function")
def account_id():
    """Return the current Account ID. Will reach out to AWS if so configured."""
    from . import allow_aws_request

    if allow_aws_request():
        identity = boto3.client("sts", "us-east-1").get_caller_identity()
        yield identity["Account"]
    else:
        with mock_aws():
            identity = boto3.client("sts", "us-east-1").get_caller_identity()
            yield identity["Account"]
