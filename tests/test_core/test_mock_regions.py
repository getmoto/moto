import boto3
import mock
import os
import pytest
from moto import mock_sns


@mock_sns
def test_use_invalid_region():
    client = boto3.client("sns", region_name="any-region")
    with pytest.raises(KeyError) as exc:
        client.list_platform_applications()
    str(exc.value).should.contain("any-region")


@mock_sns
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-2"})
def test_use_region_from_env():
    client = boto3.client("sns")
    client.list_platform_applications()["PlatformApplications"].should.equal([])


@mock_sns
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "any-region"})
def test_use_unknown_region_from_env():
    client = boto3.client("sns")
    with pytest.raises(KeyError) as exc:
        client.list_platform_applications()
    str(exc.value).should.contain("any-region")


@mock_sns
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "any-region"})
@mock.patch.dict(os.environ, {"MOTO_ALLOW_NONEXISTENT_REGION": "trUe"})
def test_use_unknown_region_from_env_but_allow_it():
    client = boto3.client("sns")
    client.list_platform_applications()["PlatformApplications"].should.equal([])
