import boto3
import pytest
from botocore.config import Config

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
@pytest.mark.parametrize("endpoint_mode", ["disabled", "preferred", "required"])
def test_dynamodb_with_account_id_routing(endpoint_mode):
    endpoint_config = Config(account_id_endpoint_mode=endpoint_mode)
    client = boto3.client(
        "dynamodb",
        aws_access_key_id="ACCESS_KEY",
        aws_secret_access_key="SECRET_KEY",
        aws_account_id=ACCOUNT_ID,
        region_name="us-west-2",
        config=endpoint_config,
    )
    client.create_table(
        TableName="test",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
