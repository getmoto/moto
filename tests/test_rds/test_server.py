from urllib.parse import urlencode
import moto.server as server
import sure  # noqa # pylint: disable=unused-import


def test_list_databases():
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeDBInstances")

    res.data.decode("utf-8").should.contain("<DescribeDBInstancesResult>")


def test_create_db_instance():
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()

    params = {
        "Action": "CreateDBInstance",
        "DBInstanceIdentifier": "hi",
        "DBInstanceClass": "db.m4.large",
        "Engine": "aurora",
        "StorageType": "standard",
        "Port": 3306,
    }
    qs = urlencode(params)
    resp = test_client.post(f"/?{qs}")

    response = resp.data.decode("utf-8")
    response.shouldnt.contain("<DBClusterIdentifier>")
    response.should.contain("<DBInstanceIdentifier>hi</DBInstanceIdentifier")
    # We do not pass these values - they should default to false
    response.should.contain("<MultiAZ>false</MultiAZ>")
    response.should.contain(
        "<IAMDatabaseAuthenticationEnabled>false</IAMDatabaseAuthenticationEnabled>"
    )
