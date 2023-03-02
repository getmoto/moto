import json
import sure  # noqa # pylint: disable=unused-import
from moto import mock_dynamodb
import moto.server as server

"""
Test the different server responses
"""


@mock_dynamodb
def test_table_list():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()
    res = test_client.get("/")
    res.status_code.should.equal(404)

    headers = {"X-Amz-Target": "TestTable.ListTables"}
    res = test_client.get("/", headers=headers)
    res.data.should.contain(b"TableNames")
    res.headers.should.have.key("X-Amz-Crc32")

    headers = {"X-Amz-Target": "DynamoDB_20120810.DescribeTable"}
    res = test_client.post(
        "/", headers=headers, data=json.dumps({"TableName": "test-table2"})
    )
    res.headers.should.have.key("X-Amzn-ErrorType").equals("ResourceNotFoundException")
    body = json.loads(res.data.decode("utf-8"))
    body.should.equal(
        {
            "__type": "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
            "message": "Requested resource not found: Table: test-table2 not found",
        }
    )
