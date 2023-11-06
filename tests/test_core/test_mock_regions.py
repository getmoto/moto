import os
from unittest import SkipTest, mock

import boto3
import pytest

from moto import mock_aws, settings


@mock_aws
def test_use_invalid_region() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode will throw different errors")
    client = boto3.client("sns", region_name="any-region")
    with pytest.raises(KeyError) as exc:
        client.list_platform_applications()
    assert "any-region" in str(exc.value)


@mock_aws
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-2"})
def test_use_region_from_env() -> None:  # type: ignore[misc]
    client = boto3.client("sns")
    assert client.list_platform_applications()["PlatformApplications"] == []


@mock_aws
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "any-region"})
def test_use_unknown_region_from_env() -> None:  # type: ignore[misc]
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set environment variables in ServerMode")
    client = boto3.client("sns")
    with pytest.raises(KeyError) as exc:
        client.list_platform_applications()
    assert "any-region" in str(exc.value)


@mock_aws
@mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "any-region"})
@mock.patch.dict(os.environ, {"MOTO_ALLOW_NONEXISTENT_REGION": "trUe"})
def test_use_unknown_region_from_env_but_allow_it() -> None:  # type: ignore[misc]
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set environemnt variables in ServerMode")
    client = boto3.client("sns")
    assert client.list_platform_applications()["PlatformApplications"] == []


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_ALLOW_NONEXISTENT_REGION": "trUe"})
def test_use_unknown_region_from_env_but_allow_it__dynamo() -> None:  # type: ignore[misc]
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set environemnt variables in ServerMode")
    dynamo_db = boto3.resource("dynamodb", region_name="test")
    dynamo_db.create_table(
        TableName="test_table",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    tables = list(dynamo_db.tables.all())
    assert [table.name for table in tables] == ["test_table"]
