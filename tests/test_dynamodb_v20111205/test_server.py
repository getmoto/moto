import json
import sure  # noqa # pylint: disable=unused-import
import pytest

import moto.server as server
from moto.dynamodb_v20111205 import dynamodb_backends

"""
Test the different server responses
Docs:
https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Appendix.APIv20111205.html
"""

TABLE_NAME = "my_table_name"
TABLE_WITH_RANGE_NAME = "my_table_with_range_name"


@pytest.fixture(autouse=True)
def test_client():
    backend = server.create_backend_app("dynamodb_v20111205")
    test_client = backend.test_client()

    yield test_client

    for _, backend in dynamodb_backends.items():
        backend.reset()


def test_404(test_client):

    res = test_client.get("/")
    res.status_code.should.equal(404)


def test_table_list(test_client):
    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    json.loads(res.data).should.equal({"TableNames": []})


def test_create_table(test_client):
    res = create_table(test_client)
    res = json.loads(res.data)["Table"]
    res.should.have.key("CreationDateTime")
    del res["CreationDateTime"]
    res.should.equal(
        {
            "KeySchema": {
                "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"},
                "RangeKeyElement": {"AttributeName": "rkey", "AttributeType": "N"},
            },
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
            "TableName": TABLE_WITH_RANGE_NAME,
            "TableStatus": "ACTIVE",
            "ItemCount": 0,
            "TableSizeBytes": 0,
        }
    )

    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    res = json.loads(res.data)
    res.should.equal({"TableNames": [TABLE_WITH_RANGE_NAME]})


def test_create_table_without_range_key(test_client):
    res = create_table(test_client, use_range_key=False)
    res = json.loads(res.data)["Table"]
    res.should.have.key("CreationDateTime")
    del res["CreationDateTime"]
    res.should.equal(
        {
            "KeySchema": {
                "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"}
            },
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
            "TableName": TABLE_NAME,
            "TableStatus": "ACTIVE",
            "ItemCount": 0,
            "TableSizeBytes": 0,
        }
    )

    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    res = json.loads(res.data)
    res.should.equal({"TableNames": [TABLE_NAME]})


# This test is pointless, as we treat DynamoDB as a global resource
def test_create_table_in_different_regions(test_client):
    create_table(test_client)
    create_table(test_client, name="Table2", region="us-west-2")

    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    res = json.loads(res.data)
    res.should.equal({"TableNames": [TABLE_WITH_RANGE_NAME, "Table2"]})


def test_update_item(test_client):

    create_table(test_client)

    headers, res = put_item(test_client)

    # UpdateItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.UpdateItem"
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
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
        "TableName": TABLE_WITH_RANGE_NAME,
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
        "TableName": TABLE_WITH_RANGE_NAME,
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
        "TableName": TABLE_WITH_RANGE_NAME,
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


@pytest.mark.parametrize(
    "use_range_key", [True, False], ids=["using range key", "using hash key only"]
)
def test_delete_table(use_range_key, test_client):
    create_table(test_client, use_range_key=use_range_key)

    headers = {"X-Amz-Target": "DynamoDB_20111205.DeleteTable"}
    name = TABLE_WITH_RANGE_NAME if use_range_key else TABLE_NAME
    test_client.post("/", headers=headers, json={"TableName": name})

    headers = {"X-Amz-Target": "DynamoDB_20111205.ListTables"}
    res = test_client.post("/", headers=headers)
    res = json.loads(res.data)
    res.should.equal({"TableNames": []})


def test_delete_unknown_table(test_client):
    headers = {"X-Amz-Target": "DynamoDB_20111205.DeleteTable"}
    res = test_client.post("/", headers=headers, json={"TableName": "unknown_table"})
    res.status_code.should.equal(400)

    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_describe_table(test_client):
    create_table(test_client)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DescribeTable",
        "Content-Type": "application/x-amz-json-1.0",
    }
    res = test_client.post(
        "/", headers=headers, json={"TableName": TABLE_WITH_RANGE_NAME}
    )
    res = json.loads(res.data)["Table"]
    res.should.have.key("CreationDateTime")
    del res["CreationDateTime"]
    res.should.equal(
        {
            "KeySchema": {
                "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"},
                "RangeKeyElement": {"AttributeName": "rkey", "AttributeType": "N"},
            },
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
            "TableName": TABLE_WITH_RANGE_NAME,
            "TableStatus": "ACTIVE",
            "ItemCount": 0,
            "TableSizeBytes": 0,
        }
    )


def test_describe_missing_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DescribeTable",
        "Content-Type": "application/x-amz-json-1.0",
    }
    res = test_client.post("/", headers=headers, json={"TableName": "unknown_table"})
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


@pytest.mark.parametrize(
    "use_range_key", [True, False], ids=["using range key", "using hash key only"]
)
def test_update_table(test_client, use_range_key):
    table_name = TABLE_WITH_RANGE_NAME if use_range_key else TABLE_NAME
    create_table(test_client, use_range_key=use_range_key)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.UpdateTable",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_data = {
        "TableName": table_name,
        "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 15},
    }
    test_client.post("/", headers=headers, json=request_data)

    # DescribeTable - verify the throughput is persisted
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DescribeTable",
        "Content-Type": "application/x-amz-json-1.0",
    }
    res = test_client.post("/", headers=headers, json={"TableName": table_name})
    throughput = json.loads(res.data)["Table"]["ProvisionedThroughput"]

    throughput.should.equal({"ReadCapacityUnits": 5, "WriteCapacityUnits": 15})


def test_put_return_none(test_client):
    create_table(test_client)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.PutItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Item": {
            "hkey": {"S": "customer"},
            "rkey": {"N": "12341234"},
            "name": {"S": "myname"},
        },
        "ReturnValues": "NONE",
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    # This seems wrong - it should return nothing, considering return_values is set to none
    res["Attributes"].should.equal(
        {"hkey": "customer", "name": "myname", "rkey": "12341234"}
    )


def test_put_return_none_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.PutItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "Item": {"hkey": {"S": "customer"}, "name": {"S": "myname"}},
        "ReturnValues": "NONE",
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    # This seems wrong - it should return nothing, considering return_values is set to none
    res["Attributes"].should.equal({"hkey": "customer", "name": "myname"})


def test_put_item_from_unknown_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.PutItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": "unknown_table",
        "Item": {
            "hkey": {"S": "customer"},
            "rkey": {"N": "12341234"},
            "name": {"S": "myname"},
        },
        "ReturnValues": "NONE",
    }
    res = test_client.post("/", headers=headers, json=request_body)

    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_get_item_from_unknown_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.GetItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": "unknown_table",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)

    res.status_code.should.equal(404)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


@pytest.mark.parametrize(
    "use_range_key", [True, False], ids=["using range key", "using hash key only"]
)
def test_get_unknown_item_from_table(use_range_key, test_client):
    create_table(test_client, use_range_key=use_range_key)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.GetItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    table_name = TABLE_WITH_RANGE_NAME if use_range_key else TABLE_NAME
    request_body = {
        "TableName": table_name,
        "Key": {"HashKeyElement": {"S": "customer"}},
    }
    if use_range_key:
        request_body["Key"]["RangeKeyElement"] = {"N": "12341234"}
    res = test_client.post("/", headers=headers, json=request_body)

    res.status_code.should.equal(404)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_get_item_without_range_key(test_client):
    create_table(test_client)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.GetItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {"HashKeyElement": {"S": "customer"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)

    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazon.coral.validate#ValidationException"}
    )


def test_put_and_get_item(test_client):
    create_table(test_client)

    headers, res = put_item(test_client)

    res["ConsumedCapacityUnits"].should.equal(1)
    res["Attributes"].should.equal(
        {"hkey": "customer", "name": "myname", "rkey": "12341234"}
    )

    # GetItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.GetItem"
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res["ConsumedCapacityUnits"].should.equal(0.5)
    res["Item"].should.equal(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341234"}}
    )

    # GetItem - return single attribute
    headers["X-Amz-Target"] = "DynamoDB_20111205.GetItem"
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
        "AttributesToGet": ["name"],
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res["ConsumedCapacityUnits"].should.equal(0.5)
    res["Item"].should.equal({"name": {"S": "myname"}})


def test_put_and_get_item_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    headers, res = put_item(test_client, use_range_key=False)

    res["ConsumedCapacityUnits"].should.equal(1)
    res["Attributes"].should.equal({"hkey": "customer", "name": "myname"})

    # GetItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.GetItem"
    request_body = {
        "TableName": TABLE_NAME,
        "Key": {"HashKeyElement": {"S": "customer"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res["ConsumedCapacityUnits"].should.equal(0.5)
    res["Item"].should.equal({"hkey": {"S": "customer"}, "name": {"S": "myname"}})

    # GetItem - return single attribute
    headers["X-Amz-Target"] = "DynamoDB_20111205.GetItem"
    request_body = {
        "TableName": TABLE_NAME,
        "Key": {"HashKeyElement": {"S": "customer"}},
        "AttributesToGet": ["name"],
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res["ConsumedCapacityUnits"].should.equal(0.5)
    res["Item"].should.equal({"name": {"S": "myname"}})


def test_scan_simple(test_client):
    create_table(test_client)

    put_item(test_client)
    put_item(test_client, rkey="12341235")
    put_item(test_client, rkey="12341236")

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {"TableName": TABLE_WITH_RANGE_NAME}
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(3)
    res.should.have.key("ScannedCount").equal(3)
    res.should.have.key("ConsumedCapacityUnits").equal(1)
    res.should.have.key("Items").length_of(3)

    items = res["Items"]
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341234"}}
    )
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341235"}}
    )
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341236"}}
    )


def test_scan_with_filter(test_client):
    create_table(test_client)

    put_item(test_client, rkey="1230", name="somename")
    put_item(test_client, rkey="1234", name=None)
    put_item(test_client, rkey="1246")

    # SCAN specific item
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "ScanFilter": {
            "rkey": {"AttributeValueList": [{"S": "1234"}], "ComparisonOperator": "EQ"}
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(1)
    res.should.have.key("ScannedCount").equal(3)
    res.should.have.key("ConsumedCapacityUnits").equal(1)
    res.should.have.key("Items").length_of(1)

    items = res["Items"]
    items.should.contain({"hkey": {"S": "customer"}, "rkey": {"N": "1234"}})

    # SCAN begins_with
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "ScanFilter": {
            "rkey": {
                "AttributeValueList": [{"S": "124"}],
                "ComparisonOperator": "BEGINS_WITH",
            }
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1246"}}
    )

    # SCAN contains
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "ScanFilter": {
            "name": {
                "AttributeValueList": [{"S": "mena"}],
                "ComparisonOperator": "CONTAINS",
            }
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "somename"}, "rkey": {"N": "1230"}}
    )

    # SCAN null
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "ScanFilter": {"name": {"ComparisonOperator": "NULL"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.contain({"hkey": {"S": "customer"}, "rkey": {"N": "1234"}})

    # SCAN NOT NULL
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "ScanFilter": {"name": {"ComparisonOperator": "NOT_NULL"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.equal(
        [
            {
                "hkey": {"S": "customer"},
                "name": {"S": "somename"},
                "rkey": {"N": "1230"},
            },
            {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1246"}},
        ]
    )

    # SCAN between
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "ScanFilter": {
            "rkey": {
                "AttributeValueList": [{"S": "1230"}, {"S": "1240"}],
                "ComparisonOperator": "BETWEEN",
            }
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "somename"}, "rkey": {"N": "1230"}}
    )


def test_scan_with_filter_in_table_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    put_item(test_client, use_range_key=False, hkey="customer1", name=None)
    put_item(test_client, use_range_key=False, hkey="customer2")
    put_item(test_client, use_range_key=False, hkey="customer3", name="special")

    # SCAN specific item
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "ScanFilter": {
            "name": {
                "AttributeValueList": [{"S": "special"}],
                "ComparisonOperator": "EQ",
            }
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(1)
    res.should.have.key("ScannedCount").equal(3)
    res.should.have.key("ConsumedCapacityUnits").equal(1)
    res.should.have.key("Items").length_of(1)

    items = res["Items"]
    items.should.contain({"hkey": {"S": "customer3"}, "name": {"S": "special"}})

    # SCAN begins_with
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "ScanFilter": {
            "hkey": {
                "AttributeValueList": [{"S": "cust"}],
                "ComparisonOperator": "BEGINS_WITH",
            }
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.have.length_of(3)  # all customers start with cust

    # SCAN contains
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "ScanFilter": {
            "name": {
                "AttributeValueList": [{"S": "yna"}],
                "ComparisonOperator": "CONTAINS",
            }
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.have.equal([{"hkey": {"S": "customer2"}, "name": {"S": "myname"}}])

    # SCAN null
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "ScanFilter": {"name": {"ComparisonOperator": "NULL"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.equal([{"hkey": {"S": "customer1"}}])

    # SCAN NOT NULL
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "ScanFilter": {"name": {"ComparisonOperator": "NOT_NULL"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.have.length_of(2)
    items.should.contain({"hkey": {"S": "customer2"}, "name": {"S": "myname"}})
    items.should.contain({"hkey": {"S": "customer3"}, "name": {"S": "special"}})


def test_scan_with_undeclared_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {"TableName": "unknown_table"}
    res = test_client.post("/", headers=headers, json=request_body)
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_query_in_table_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    put_item(test_client, use_range_key=False)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {"TableName": TABLE_NAME, "HashKeyValue": {"S": "customer"}}
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(1)
    res.should.have.key("ConsumedCapacityUnits").equal(1)
    res.should.have.key("Items").length_of(1)

    items = res["Items"]
    items.should.contain({"hkey": {"S": "customer"}, "name": {"S": "myname"}})

    # QUERY for unknown value
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {"TableName": TABLE_NAME, "HashKeyValue": {"S": "unknown-value"}}
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    # TODO: We should not get any results here
    # res.should.have.key("Count").equal(0)
    # res.should.have.key("Items").length_of(0)


def test_query_item_by_hash_only(test_client):
    create_table(test_client)

    put_item(test_client)
    put_item(test_client, rkey="12341235")
    put_item(test_client, rkey="12341236")

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(3)
    res.should.have.key("ConsumedCapacityUnits").equal(1)
    res.should.have.key("Items").length_of(3)

    items = res["Items"]
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341234"}}
    )
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341235"}}
    )
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341236"}}
    )


def test_query_item_by_range_key(test_client):
    create_table(test_client, use_range_key=True)

    put_item(test_client, rkey="1234")
    put_item(test_client, rkey="1235")
    put_item(test_client, rkey="1247")

    # GT some
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "1235"}],
            "ComparisonOperator": "GT",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(1)
    res.should.have.key("ConsumedCapacityUnits").equal(1)
    res.should.have.key("Items").length_of(1)

    items = res["Items"]
    items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1247"}}
    )

    # GT all
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "0"}],
            "ComparisonOperator": "GT",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(3)
    res.should.have.key("Items").length_of(3)

    # GT none
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "9999"}],
            "ComparisonOperator": "GT",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res["ConsumedCapacityUnits"].should.equal(1)
    res["Items"].should.equal([])
    res["Count"].should.equal(0)

    # CONTAINS some
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "24"}],
            "ComparisonOperator": "CONTAINS",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.equal(
        [{"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1247"}}]
    )

    # BEGINS_WITH
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "123"}],
            "ComparisonOperator": "BEGINS_WITH",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.equal(
        [
            {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1234"}},
            {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1235"}},
        ]
    )

    # CONTAINS
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "0"}, {"N": "1240"}],
            "ComparisonOperator": "BETWEEN",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    items = json.loads(res.data)["Items"]

    items.should.equal(
        [
            {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1234"}},
            {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "1235"}},
        ]
    )


def test_query_item_with_undeclared_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Query",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": "unknown_table",
        "HashKeyValue": {"S": "customer"},
        "RangeKeyCondition": {
            "AttributeValueList": [{"N": "1235"}],
            "ComparisonOperator": "GT",
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_delete_item(test_client):
    create_table(test_client)

    put_item(test_client)
    put_item(test_client, rkey="12341235")
    put_item(test_client, rkey="12341236")

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DeleteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341236"},
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res.should.equal({"Attributes": [], "ConsumedCapacityUnits": 0.5})

    # GetItem
    headers["X-Amz-Target"] = "DynamoDB_20111205.GetItem"
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341234"},
        },
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res["Item"].should.have.key("hkey").equal({"S": "customer"})
    res["Item"].should.have.key("rkey").equal({"N": "12341234"})
    res["Item"].should.have.key("name").equal({"S": "myname"})


def test_update_item_that_doesnt_exist(test_client):
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
    res = json.loads(res.data)
    res.should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_delete_item_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    put_item(test_client, use_range_key=False)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DeleteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_NAME,
        "Key": {"HashKeyElement": {"S": "customer"}},
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res.should.equal({"Attributes": [], "ConsumedCapacityUnits": 0.5})


def test_delete_item_with_return_values(test_client):
    create_table(test_client)

    put_item(test_client)
    put_item(test_client, rkey="12341235")
    put_item(test_client, rkey="12341236")

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DeleteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341236"},
        },
        "ReturnValues": "ALL_OLD",
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    res.should.equal(
        {
            "Attributes": {"hkey": "customer", "name": "myname", "rkey": "12341236"},
            "ConsumedCapacityUnits": 0.5,
        }
    )


def test_delete_unknown_item(test_client):
    create_table(test_client)

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DeleteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": TABLE_WITH_RANGE_NAME,
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341236"},
        },
        "ReturnValues": "ALL_OLD",
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_update_item_in_nonexisting_table(test_client):
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


def test_delete_from_unknown_table(test_client):
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.DeleteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": "unknown_table",
        "Key": {
            "HashKeyElement": {"S": "customer"},
            "RangeKeyElement": {"N": "12341236"},
        },
        "ReturnValues": "ALL_OLD",
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"}
    )


def test_batch_get_item(test_client):
    create_table(test_client)

    put_item(test_client)
    put_item(test_client, rkey="12341235")
    put_item(test_client, rkey="12341236")

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.BatchGetItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "RequestItems": {
            TABLE_WITH_RANGE_NAME: {
                "Keys": [
                    {
                        "HashKeyElement": {"S": "customer"},
                        "RangeKeyElement": {"N": "12341235"},
                    },
                    {
                        "HashKeyElement": {"S": "customer"},
                        "RangeKeyElement": {"N": "12341236"},
                    },
                ],
            }
        }
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)["Responses"]

    res.should.have.key("UnprocessedKeys").equal({})
    table_items = [i["Item"] for i in res[TABLE_WITH_RANGE_NAME]["Items"]]
    table_items.should.have.length_of(2)

    table_items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341235"}}
    )
    table_items.should.contain(
        {"hkey": {"S": "customer"}, "name": {"S": "myname"}, "rkey": {"N": "12341236"}}
    )


def test_batch_get_item_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    put_item(test_client, use_range_key=False, hkey="customer1")
    put_item(test_client, use_range_key=False, hkey="customer2")
    put_item(test_client, use_range_key=False, hkey="customer3")

    headers = {
        "X-Amz-Target": "DynamoDB_20111205.BatchGetItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "RequestItems": {
            TABLE_NAME: {
                "Keys": [
                    {"HashKeyElement": {"S": "customer1"}},
                    {"HashKeyElement": {"S": "customer3"}},
                ],
            }
        }
    }
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)["Responses"]

    res.should.have.key("UnprocessedKeys").equal({})
    table_items = [i["Item"] for i in res[TABLE_NAME]["Items"]]
    table_items.should.have.length_of(2)

    table_items.should.contain({"hkey": {"S": "customer1"}, "name": {"S": "myname"}})
    table_items.should.contain({"hkey": {"S": "customer3"}, "name": {"S": "myname"}})


def test_batch_write_item(test_client):
    create_table(test_client)

    # BATCH-WRITE
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.BatchWriteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "RequestItems": {
            TABLE_WITH_RANGE_NAME: [
                {
                    "PutRequest": {
                        "Item": {"hkey": {"S": "customer"}, "rkey": {"S": "1234"}}
                    }
                },
                {
                    "PutRequest": {
                        "Item": {"hkey": {"S": "customer"}, "rkey": {"S": "1235"}}
                    }
                },
            ],
        }
    }
    test_client.post("/", headers=headers, json=request_body)

    # SCAN - verify all items are present
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {"TableName": TABLE_WITH_RANGE_NAME}
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(2)


def test_batch_write_item_without_range_key(test_client):
    create_table(test_client, use_range_key=False)

    # BATCH-WRITE
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.BatchWriteItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "RequestItems": {
            TABLE_NAME: [
                {"PutRequest": {"Item": {"hkey": {"S": "customer"}}}},
                {"PutRequest": {"Item": {"hkey": {"S": "customer2"}}}},
            ],
        }
    }
    test_client.post("/", headers=headers, json=request_body)

    # SCAN - verify all items are present
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.Scan",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {"TableName": TABLE_NAME}
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)

    res.should.have.key("Count").equal(2)


def put_item(
    test_client, hkey="customer", rkey="12341234", name="myname", use_range_key=True
):
    table_name = TABLE_WITH_RANGE_NAME if use_range_key else TABLE_NAME
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.PutItem",
        "Content-Type": "application/x-amz-json-1.0",
    }
    request_body = {
        "TableName": table_name,
        "Item": {"hkey": {"S": hkey}},
        "ReturnValues": "ALL_OLD",
    }
    if name:
        request_body["Item"]["name"] = {"S": name}
    if rkey and use_range_key:
        request_body["Item"]["rkey"] = {"N": rkey}
    res = test_client.post("/", headers=headers, json=request_body)
    res = json.loads(res.data)
    return headers, res


def create_table(test_client, name=None, region=None, use_range_key=True):
    if not name:
        name = TABLE_WITH_RANGE_NAME if use_range_key else TABLE_NAME
    headers = {
        "X-Amz-Target": "DynamoDB_20111205.CreateTable",
        "Content-Type": "application/x-amz-json-1.0",
    }
    if region:
        headers["Host"] = "dynamodb.{}.amazonaws.com".format(region)
    request_body = {
        "TableName": name,
        "KeySchema": {
            "HashKeyElement": {"AttributeName": "hkey", "AttributeType": "S"}
        },
        "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 10},
    }
    if use_range_key:
        request_body["KeySchema"]["RangeKeyElement"] = {
            "AttributeName": "rkey",
            "AttributeType": "N",
        }
    return test_client.post("/", headers=headers, json=request_body)
