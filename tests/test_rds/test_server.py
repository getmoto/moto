import json
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

    body = {
        "DBInstanceIdentifier": "hi",
        "DBInstanceClass": "db.m4.large",
        "Engine": "aurora",
        "StorageType": "standard",
        "Port": 3306,
    }
    res = test_client.post("/?Action=CreateDBInstance", data=json.dumps(body))

    response = res.data.decode("utf-8")
    response.shouldnt.contain("<DBClusterIdentifier>")

    # We do not pass these values - they should default to false
    response.should.contain("<MultiAZ>false</MultiAZ>")
    response.should.contain(
        "<IAMDatabaseAuthenticationEnabled>false</IAMDatabaseAuthenticationEnabled>"
    )
