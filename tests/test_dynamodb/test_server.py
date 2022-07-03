import sure  # noqa # pylint: disable=unused-import

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
    res.headers.should.have.key("X-Amz-Crc32")
