from __future__ import unicode_literals
import json
import sure  # noqa

import moto.server as server

"""
Test the different server responses
"""


def test_table_list():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()

    res = test_client.get("/")
    res.status_code.should.equal(404)

    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    res.data.should.contain(b"TableNames")


def test_update_item():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()

    create_table(test_client)

    headers, res = put_item(test_client)

    # UpdateItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.UpdateItem"
    request_body = {
        "TableName": "Table1",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
        "AttributeUpdates": {"new_att": {"Value": {"SS": ["val"]}, "Action": "PUT"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)

    # UpdateItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.UpdateItem"
    request_body = {
        "TableName": "Table1",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
        "AttributeUpdates": {"new_n": {"Value": {"N": "42"}, "Action": "PUT"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res["ConsumedCapacityUnits"].should.equal(0.5)
    res["Attributes"].should.equal(
        {
            "hkey": "customer",
            "name": "myname",
            "rkey": "12341234",
            "new_att": ["val"],
            "new_n": "42",
        }
    )

    # UpdateItem - multiples
    headers["X-Amz-Target"] = "DynamoDB_20111205.UpdateItem"
    request_body = {
        "TableName": "Table1",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
        "AttributeUpdates": {
            "new_n": {"Value": {"N": 7}, "Action": "ADD"},
            "new_att": {"Value": {"S": "val2"}, "Action": "ADD"},
            "name": {"Action": "DELETE"},
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res["ConsumedCapacityUnits"].should.equal(0.5)
    res["Attributes"].should.equal(
        {
            "hkey": "customer",
            "rkey": "12341234",
            "new_att": ["val", "val2"],
            "new_n": "49",
        }
    )

    # GetItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.GetItem"
    request_body = {
        "TableName": "Table1",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res["Item"].should.have.key("new_att").equal({"SS": ["val", "val2"]})
    res["Item"].should.have.key("new_n").equal({"N": "49"})
    res["Item"].shouldnt.have.key("name")


def test_update_item_that_doesnt_exist():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()

    create_table(test_client)

    # UpdateItem
    headers = {"X-Amz-Target": "DynamoDB_20111205.UpdateItem"}
    request_body = {
        "TableName": "Table1",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
        "AttributeUpdates": {"new_att": {"Value": {"SS": ["val"]}, "Action": "PUT"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_update_item_in_nonexisting_table():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()

    # UpdateItem
    headers = {"X-Amz-Target": "DynamoDB_20111205.UpdateItem"}
    request_body = {
        "TableName": "nonexistent",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
        "AttributeUpdates": {"new_att": {"Value": {"SS": ["val"]}, "Action": "PUT"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def put_item(test_client, rkey="12341234"):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.PutItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": "Table1",
        "Item": {
            "hkey": {"S": "customer"},
            "rkey": {"N": rkey},
            "name": {"S": "myname"},
        },
        "ReturnValues": "ALL_OLD",
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    return headers, res


def create_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.CreateTable",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": "Table1",
        "KeySchema": {
            "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"},
            "RangeKeyElement": {"AttributeName": "rkey", "AttributeType": "N"},
        },
        "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
    }
    return test_client.post("/", headers=headers, json=request_body)
