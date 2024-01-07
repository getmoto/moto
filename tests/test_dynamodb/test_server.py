import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_table_list():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()
    res = test_client.get("/")
    assert res.status_code == 404

    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    assert b"TableNames" in res.data
    assert "X-Amz-Crc32" in res.headers

    headers = {"X-Amz-Target": "DynamoDB_20120810.DescribeTable"}
    res = test_client.post(
        "/", headers=headers, data=json.dumps({"TableName": "test-table2"})
    )
    assert res.headers["X-Amzn-ErrorType"] == "ResourceNotFoundException"
    body = json.loads(res.data.decode("utf-8"))
    assert body == {
        "__type": "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
        "message": "Requested resource not found: Table: test-table2 not found",
    }
