import boto3
import pytest

from moto import mock_aws
from tests import allow_aws_request


def _get_param() -> str:
    # Ideally we just pick the first parameter in "/aws/service/ami-amazon-linux-latest"
    # But we usually need x86_64 - and the chance if randomly picking ARM64 is quite high
    # Alternative implementation: call get_parameters_by_path(..) until we find a x86_64 kernel
    # (There is currently no option to filter by architecture)
    client = boto3.client("ssm", region_name="us-east-1")
    return client.get_parameters(
        Names=["/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"],
    )["Parameters"][0]["Value"]


def get_valid_ami():
    if allow_aws_request():
        param = _get_param()
    else:
        with mock_aws():
            param = _get_param()
    return param


@pytest.fixture(scope="session")
def valid_ami():
    yield get_valid_ami()
