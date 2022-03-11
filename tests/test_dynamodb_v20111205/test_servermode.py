import json
import sure  # noqa # pylint: disable=unused-import
import requests

from moto import settings
from unittest import SkipTest
from uuid import uuid4

"""
Test the different server responses
Docs:
https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Appendix.APIv20111205.html
"""


def test_table_list():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("Only run test with external server")
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.ListTables",
        "Host": "dynamodb.us-east-1.amazonaws.com",
    }
    requests.post(settings.test_server_mode_endpoint() + "/moto-api/reset")
    res = requests.get(settings.test_server_mode_endpoint(), headers=headers)
    res.status_code.should.equal(200)
    json.loads(res.content).should.equal({"TableNames": []})


def test_create_table():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("Only run test with external server")

    table_name = str(uuid4())

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.CreateTable",
        "Content-Type": "application/x-amz-json-1.0",
        "AUTHORIZATION": "AWS4-HMAC-SHA256 Credential=ACCESS_KEY/20220226/us-east-1/dynamodb/aws4_request, SignedHeaders=content-type;host;x-amz-date;x-amz-target, Signature=sig",
    }
    request_body = {
        "TableName": table_name,
        "KeySchema": {
            "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"}
        },
        "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
    }
    res = requests.post(
        settings.test_server_mode_endpoint(), headers=headers, json=request_body
    )

    res = json.loads(res.content)["Table"]
    res.should.have.key("CreationDateTime")
    del res["CreationDateTime"]
    res.should.equal(
        {
            "KeySchema": {
                "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"}
            },
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
            "TableName": table_name,
            "TableStatus": "ACTIVE",
            "ItemCount": 0,
            "TableSizeBytes": 0,
        }
    )

    headers["X-Amz-Target"] = "DynamoDB_20111205.ListTables"
    res = requests.get(settings.test_server_mode_endpoint(), headers=headers)
    res = json.loads(res.content)
    table_name.should.be.within(res["TableNames"])
