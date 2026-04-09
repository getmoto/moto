import boto3
import pytest

from moto import mock_aws
from tests import allow_aws_request


@pytest.fixture(scope="session")
def valid_ami():
    path = "/aws/service/ami-amazon-linux-latest"
    if allow_aws_request():
        client = boto3.client("ssm", region_name="us-east-1")
        param = client.get_parameters_by_path(Path=path, MaxResults=1)["Parameters"][0]
    else:
        with mock_aws():
            client = boto3.client("ssm", region_name="us-east-1")
            param = client.get_parameters_by_path(Path=path, MaxResults=1)[
                "Parameters"
            ][0]
    yield param["Value"]
