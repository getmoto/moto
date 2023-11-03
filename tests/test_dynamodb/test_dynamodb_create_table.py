import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import pytest

from moto import mock_dynamodb
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from . import dynamodb_aws_verified


@mock_dynamodb
def test_create_table_standard():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="messages",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
    )
    actual = client.describe_table(TableName="messages")["Table"]

    assert actual["AttributeDefinitions"] == [
        {"AttributeName": "id", "AttributeType": "S"},
        {"AttributeName": "subject", "AttributeType": "S"},
    ]
    assert isinstance(actual["CreationDateTime"], datetime)
    assert actual["GlobalSecondaryIndexes"] == []
    assert actual["LocalSecondaryIndexes"] == []
    assert actual["ProvisionedThroughput"] == {
        "NumberOfDecreasesToday": 0,
        "ReadCapacityUnits": 1,
        "WriteCapacityUnits": 5,
    }
    assert actual["TableSizeBytes"] == 0
    assert actual["TableName"] == "messages"
    assert actual["TableStatus"] == "ACTIVE"
    assert (
        actual["TableArn"] == f"arn:aws:dynamodb:us-east-1:{ACCOUNT_ID}:table/messages"
    )
    assert actual["KeySchema"] == [
        {"AttributeName": "id", "KeyType": "HASH"},
        {"AttributeName": "subject", "KeyType": "RANGE"},
    ]
    assert actual["ItemCount"] == 0


@mock_dynamodb
def test_create_table_with_local_index():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="messages",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
            {"AttributeName": "threads", "AttributeType": "S"},
        ],
        LocalSecondaryIndexes=[
            {
                "IndexName": "threads_index",
                "KeySchema": [
                    {"AttributeName": "id", "KeyType": "HASH"},
                    {"AttributeName": "threads", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
    )
    actual = client.describe_table(TableName="messages")["Table"]

    assert actual["AttributeDefinitions"] == [
        {"AttributeName": "id", "AttributeType": "S"},
        {"AttributeName": "subject", "AttributeType": "S"},
        {"AttributeName": "threads", "AttributeType": "S"},
    ]
    assert isinstance(actual["CreationDateTime"], datetime)
    assert actual["GlobalSecondaryIndexes"] == []
    assert actual["LocalSecondaryIndexes"] == [
        {
            "IndexName": "threads_index",
            "KeySchema": [
                {"AttributeName": "id", "KeyType": "HASH"},
                {"AttributeName": "threads", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]
    assert actual["ProvisionedThroughput"] == {
        "NumberOfDecreasesToday": 0,
        "ReadCapacityUnits": 1,
        "WriteCapacityUnits": 5,
    }
    assert actual["TableSizeBytes"] == 0
    assert actual["TableName"] == "messages"
    assert actual["TableStatus"] == "ACTIVE"
    assert (
        actual["TableArn"] == f"arn:aws:dynamodb:us-east-1:{ACCOUNT_ID}:table/messages"
    )
    assert actual["KeySchema"] == [
        {"AttributeName": "id", "KeyType": "HASH"},
        {"AttributeName": "subject", "KeyType": "RANGE"},
    ]
    assert actual["ItemCount"] == 0


@mock_dynamodb
def test_create_table_with_gsi():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [{"AttributeName": "subject", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    assert table["TableDescription"]["GlobalSecondaryIndexes"] == [
        {
            "KeySchema": [{"KeyType": "HASH", "AttributeName": "subject"}],
            "IndexName": "test_gsi",
            "Projection": {"ProjectionType": "ALL"},
            "IndexStatus": "ACTIVE",
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 0,
                "WriteCapacityUnits": 0,
            },
        }
    ]

    table = dynamodb.create_table(
        TableName="users2",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [{"AttributeName": "subject", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 3,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
    )
    assert table["TableDescription"]["GlobalSecondaryIndexes"] == [
        {
            "KeySchema": [{"KeyType": "HASH", "AttributeName": "subject"}],
            "IndexName": "test_gsi",
            "Projection": {"ProjectionType": "ALL"},
            "IndexStatus": "ACTIVE",
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 3,
                "WriteCapacityUnits": 5,
            },
        }
    ]


@mock_dynamodb
def test_create_table_with_stream_specification():
    conn = boto3.client("dynamodb", region_name="us-east-1")

    resp = conn.create_table(
        TableName="test-streams",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

    assert resp["TableDescription"]["StreamSpecification"] == {
        "StreamEnabled": True,
        "StreamViewType": "NEW_AND_OLD_IMAGES",
    }
    assert "LatestStreamLabel" in resp["TableDescription"]
    assert "LatestStreamArn" in resp["TableDescription"]

    resp = conn.delete_table(TableName="test-streams")

    assert "StreamSpecification" in resp["TableDescription"]


@mock_dynamodb
def test_create_table_with_tags():
    client = boto3.client("dynamodb", region_name="us-east-1")

    resp = client.create_table(
        TableName="test-streams",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        Tags=[{"Key": "tk", "Value": "tv"}],
    )

    resp = client.list_tags_of_resource(
        ResourceArn=resp["TableDescription"]["TableArn"]
    )
    assert resp["Tags"] == [{"Key": "tk", "Value": "tv"}]


@mock_dynamodb
def test_create_table_pay_per_request():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test1",
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

    actual = client.describe_table(TableName="test1")["Table"]
    assert actual["BillingModeSummary"] == {"BillingMode": "PAY_PER_REQUEST"}
    assert actual["ProvisionedThroughput"] == {
        "NumberOfDecreasesToday": 0,
        "ReadCapacityUnits": 0,
        "WriteCapacityUnits": 0,
    }


@mock_dynamodb
def test_create_table__provisioned_throughput():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 2, "WriteCapacityUnits": 3},
    )

    actual = client.describe_table(TableName="test1")["Table"]
    assert actual["BillingModeSummary"] == {"BillingMode": "PROVISIONED"}
    assert actual["ProvisionedThroughput"] == {
        "NumberOfDecreasesToday": 0,
        "ReadCapacityUnits": 2,
        "WriteCapacityUnits": 3,
    }


@mock_dynamodb
def test_create_table_without_specifying_throughput():
    dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        dynamodb_client.create_table(
            TableName="my-table",
            AttributeDefinitions=[
                {"AttributeName": "some_field", "AttributeType": "S"}
            ],
            KeySchema=[{"AttributeName": "some_field", "KeyType": "HASH"}],
            BillingMode="PROVISIONED",
            StreamSpecification={"StreamEnabled": False, "StreamViewType": "NEW_IMAGE"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "One or more parameter values were invalid: ReadCapacityUnits and WriteCapacityUnits must both be specified when BillingMode is PROVISIONED"
    )


@mock_dynamodb
def test_create_table_error_pay_per_request_with_provisioned_param():
    client = boto3.client("dynamodb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_table(
            TableName="test1",
            AttributeDefinitions=[
                {"AttributeName": "client", "AttributeType": "S"},
                {"AttributeName": "app", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "client", "KeyType": "HASH"},
                {"AttributeName": "app", "KeyType": "RANGE"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
            BillingMode="PAY_PER_REQUEST",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "ProvisionedThroughput cannot be specified when BillingMode is PAY_PER_REQUEST"
    )


@mock_dynamodb
def test_create_table_with_ssespecification__false():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
        SSESpecification={"Enabled": False},
    )

    actual = client.describe_table(TableName="test1")["Table"]
    assert "SSEDescription" not in actual


@mock_dynamodb
def test_create_table_with_ssespecification__true():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
        SSESpecification={"Enabled": True},
    )

    actual = client.describe_table(TableName="test1")["Table"]
    assert "SSEDescription" in actual
    assert actual["SSEDescription"]["Status"] == "ENABLED"
    assert actual["SSEDescription"]["SSEType"] == "KMS"
    # Default KMS key for DynamoDB
    assert actual["SSEDescription"]["KMSMasterKeyArn"].startswith("arn:aws:kms")


@mock_dynamodb
def test_create_table_with_ssespecification__custom_kms_key():
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="test1",
        AttributeDefinitions=[
            {"AttributeName": "client", "AttributeType": "S"},
            {"AttributeName": "app", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "client", "KeyType": "HASH"},
            {"AttributeName": "app", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
        SSESpecification={"Enabled": True, "KMSMasterKeyId": "custom-kms-key"},
    )

    actual = client.describe_table(TableName="test1")["Table"]
    assert "SSEDescription" in actual
    assert actual["SSEDescription"]["Status"] == "ENABLED"
    assert actual["SSEDescription"]["SSEType"] == "KMS"
    assert actual["SSEDescription"]["KMSMasterKeyArn"] == "custom-kms-key"


@pytest.mark.aws_verified
@dynamodb_aws_verified(create_table=False)
def test_create_table__specify_non_key_column():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="unknown-key-type",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "SORT"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'SORT' at 'keySchema.2.member.keyType' failed to satisfy constraint: Member must satisfy enum value set: [HASH, RANGE]"
    )

    # Verify we get the same message for Global Secondary Indexes
    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="unknown-key-type",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "TestGSI",
                    # Note that the attributes are not declared, which is also invalid
                    # But AWS trips over the KeyType=SORT first
                    "KeySchema": [
                        {"AttributeName": "n/a", "KeyType": "HASH"},
                        {"AttributeName": "sth", "KeyType": "SORT"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'SORT' at 'globalSecondaryIndexes.1.member.keySchema.2.member.keyType' failed to satisfy constraint: Member must satisfy enum value set: [HASH, RANGE]"
    )

    # Verify we get the same message for Local Secondary Indexes
    with pytest.raises(ClientError) as exc:
        dynamodb.create_table(
            TableName="unknown-key-type",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            LocalSecondaryIndexes=[
                {
                    "IndexName": "test_lsi",
                    "KeySchema": [
                        {"AttributeName": "pk", "KeyType": "HASH"},
                        {"AttributeName": "lsi_range_key", "KeyType": "SORT"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'SORT' at 'localSecondaryIndexes.1.member.keySchema.2.member.keyType' failed to satisfy constraint: Member must satisfy enum value set: [HASH, RANGE]"
    )
