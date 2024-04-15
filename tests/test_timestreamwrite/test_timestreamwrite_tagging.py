from uuid import uuid4

import boto3
import pytest

from moto import mock_aws

from . import timestreamwrite_aws_verified


@mock_aws
def test_list_tagging_for_table_without_tags():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    resp = ts.create_table(
        DatabaseName="mydatabase",
        TableName="mytable",
        RetentionProperties={
            "MemoryStoreRetentionPeriodInHours": 7,
            "MagneticStoreRetentionPeriodInDays": 42,
        },
    )
    table_arn = resp["Table"]["Arn"]

    resp = ts.list_tags_for_resource(ResourceARN=table_arn)
    assert resp["Tags"] == []


@mock_aws
def test_list_tagging_for_table_with_tags():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    resp = ts.create_table(
        DatabaseName="mydatabase",
        TableName="mytable",
        RetentionProperties={
            "MemoryStoreRetentionPeriodInHours": 7,
            "MagneticStoreRetentionPeriodInDays": 42,
        },
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    table_arn = resp["Table"]["Arn"]

    resp = ts.list_tags_for_resource(ResourceARN=table_arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}]


@mock_aws
def test_list_tagging_for_database_without_tags():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_arn = ts.create_database(DatabaseName="mydatabase")["Database"]["Arn"]

    resp = ts.list_tags_for_resource(ResourceARN=db_arn)
    assert resp["Tags"] == []


@mock_aws
def test_list_tagging_for_database_with_tags():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_arn = ts.create_database(
        DatabaseName="mydatabase", Tags=[{"Key": "k1", "Value": "v1"}]
    )["Database"]["Arn"]

    resp = ts.list_tags_for_resource(ResourceARN=db_arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}]


@pytest.mark.aws_verified
@timestreamwrite_aws_verified
def test_tag_and_untag_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_name = "db_" + str(uuid4())[0:6]

    try:
        db_arn = ts.create_database(
            DatabaseName=db_name, Tags=[{"Key": "k1", "Value": "v1"}]
        )["Database"]["Arn"]

        ts.tag_resource(
            ResourceARN=db_arn,
            Tags=[{"Key": "k2", "Value": "v2"}, {"Key": "k3", "Value": "v3"}],
        )

        tags = ts.list_tags_for_resource(ResourceARN=db_arn)["Tags"]
        assert len(tags) == 3
        assert {"Key": "k1", "Value": "v1"} in tags
        assert {"Key": "k2", "Value": "v2"} in tags
        assert {"Key": "k3", "Value": "v3"} in tags

        ts.untag_resource(ResourceARN=db_arn, TagKeys=["k2"])

        tags = ts.list_tags_for_resource(ResourceARN=db_arn)["Tags"]
        assert len(tags) == 2
        assert {"Key": "k1", "Value": "v1"} in tags
        assert {"Key": "k3", "Value": "v3"} in tags
    finally:
        ts.delete_database(DatabaseName=db_name)
