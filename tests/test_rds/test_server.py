from urllib.parse import urlencode
import moto.server as server


def test_list_databases():
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeDBInstances")

    assert "<DescribeDBInstancesResult>" in res.data.decode("utf-8")


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
    assert "<DBClusterIdentifier>" not in response
    assert "<DBInstanceIdentifier>hi</DBInstanceIdentifier" in response
    # We do not pass these values - they should default to false
    assert "<MultiAZ>false</MultiAZ>" in response
    assert (
        "<IAMDatabaseAuthenticationEnabled>false</IAMDatabaseAuthenticationEnabled>"
    ) in response
