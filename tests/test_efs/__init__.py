import boto3
import pytest

from moto import mock_ec2, mock_efs


@pytest.fixture(scope="function", name="ec2")
def fixture_ec2():
    with mock_ec2():
        yield boto3.client("ec2", region_name="us-east-1")


@pytest.fixture(scope="function", name="efs")
def fixture_efs():
    with mock_efs():
        yield boto3.client("efs", region_name="us-east-1")
