import moto.server as server
import sure  # noqa # pylint: disable=unused-import


def test_list_databases():
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeDBInstances")

    res.data.decode("utf-8").should.contain("<DescribeDBInstancesResult>")
