import boto3

from moto import mock_timestreamwrite


@mock_timestreamwrite
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


@mock_timestreamwrite
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


@mock_timestreamwrite
def test_list_tagging_for_database_without_tags():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_arn = ts.create_database(DatabaseName="mydatabase")["Database"]["Arn"]

    resp = ts.list_tags_for_resource(ResourceARN=db_arn)
    assert resp["Tags"] == []


@mock_timestreamwrite
def test_list_tagging_for_database_with_tags():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_arn = ts.create_database(
        DatabaseName="mydatabase", Tags=[{"Key": "k1", "Value": "v1"}]
    )["Database"]["Arn"]

    resp = ts.list_tags_for_resource(ResourceARN=db_arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}]


@mock_timestreamwrite
def test_tag_and_untag_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_arn = ts.create_database(
        DatabaseName="mydatabase", Tags=[{"Key": "k1", "Value": "v1"}]
    )["Database"]["Arn"]

    ts.tag_resource(
        ResourceARN=db_arn,
        Tags=[{"Key": "k2", "Value": "v2"}, {"Key": "k3", "Value": "v3"}],
    )

    resp = ts.list_tags_for_resource(ResourceARN=db_arn)
    assert resp["Tags"] == [
        {"Key": "k1", "Value": "v1"},
        {"Key": "k2", "Value": "v2"},
        {"Key": "k3", "Value": "v3"},
    ]

    ts.untag_resource(ResourceARN=db_arn, TagKeys=["k2"])

    resp = ts.list_tags_for_resource(ResourceARN=db_arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}, {"Key": "k3", "Value": "v3"}]
