import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_dynamodb


@mock_dynamodb
def test_update_different_map_elements_in_single_request():
    # https://github.com/spulec/moto/issues/5552
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="example_table",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    record = {
        "id": "example_id",
        "d": {"hello": "h", "world": "w"},
    }
    table = dynamodb.Table("example_table")
    table.put_item(Item=record)
    updated = table.update_item(
        Key={"id": "example_id"},
        UpdateExpression="set d.hello = :h, d.world = :w",
        ExpressionAttributeValues={":h": "H", ":w": "W"},
        ReturnValues="ALL_NEW",
    )
    updated["Attributes"].should.equal(
        {"id": "example_id", "d": {"hello": "H", "world": "W"}}
    )
