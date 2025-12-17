from uuid import uuid4

import boto3

from moto import mock_aws


@mock_aws
def test_update_table__billing_mode():
    client = boto3.client("dynamodb", region_name="us-east-1")
    table_name = f"T{uuid4()}"
    client.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    client.update_table(
        TableName=table_name,
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    actual = client.describe_table(TableName=table_name)["Table"]
    assert actual["BillingModeSummary"] == {"BillingMode": "PROVISIONED"}
    assert actual["ProvisionedThroughput"] == {
        "ReadCapacityUnits": 1,
        "WriteCapacityUnits": 1,
    }


@mock_aws
def test_update_table_throughput():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName=f"T{uuid4()}",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    assert table.provisioned_throughput["ReadCapacityUnits"] == 5
    assert table.provisioned_throughput["WriteCapacityUnits"] == 5

    table.update(
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 6}
    )

    assert table.provisioned_throughput["ReadCapacityUnits"] == 5
    assert table.provisioned_throughput["WriteCapacityUnits"] == 6


@mock_aws
def test_update_table_deletion_protection_enabled():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName=f"T{uuid4()}",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
        DeletionProtectionEnabled=False,
    )
    assert not table.deletion_protection_enabled

    table.update(DeletionProtectionEnabled=True)

    assert table.deletion_protection_enabled


@mock_aws
def test_update_table_deletion_protection_disabled():
    conn = boto3.resource("dynamodb", region_name="us-west-2")
    table = conn.create_table(
        TableName=f"T{uuid4()}",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
        DeletionProtectionEnabled=True,
    )
    assert table.deletion_protection_enabled

    table.update(DeletionProtectionEnabled=False)

    assert not table.deletion_protection_enabled


@mock_aws
def test_update_table__enable_stream():
    conn = boto3.client("dynamodb", region_name="us-east-1")
    table_name = f"T{uuid4()}"

    resp = conn.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )

    assert "StreamSpecification" not in resp["TableDescription"]

    resp = conn.update_table(
        TableName=table_name,
        StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_IMAGE"},
    )

    assert "StreamSpecification" in resp["TableDescription"]
    assert resp["TableDescription"]["StreamSpecification"] == {
        "StreamEnabled": True,
        "StreamViewType": "NEW_IMAGE",
    }
    assert "LatestStreamLabel" in resp["TableDescription"]
    assert "LatestStreamArn" in resp["TableDescription"]


@mock_aws
def test_update_table_warm_throughput():
    client = boto3.client("dynamodb", region_name="us-east-1")
    table_name = f"T{uuid4()}"
    client.create_table(
        TableName=table_name,
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.update_table(
        TableName=table_name,
        WarmThroughput={
            "ReadUnitsPerSecond": 15000,
            "WriteUnitsPerSecond": 5000,
        },
    )
    table = client.describe_table(TableName=table_name)["Table"]
    assert (
        table["WarmThroughput"]
        == {
            "ReadUnitsPerSecond": 15000,
            "Status": "ACTIVE",
            "WriteUnitsPerSecond": 5000,
        }
        or table["WarmThroughput"]["Status"] == "UPDATING"
    )
