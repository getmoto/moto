import boto3
import pytest
from botocore.exceptions import ClientError
from uuid import uuid4

from moto import mock_timestreamwrite
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from . import timestreamwrite_aws_verified


@pytest.mark.aws_verified
@timestreamwrite_aws_verified
def test_create_database_simple():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_name = "db_" + str(uuid4())[0:6]

    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    account_id = identity["Account"]

    try:
        database = ts.create_database(DatabaseName=db_name)["Database"]

        assert (
            database["Arn"]
            == f"arn:aws:timestream:us-east-1:{account_id}:database/{db_name}"
        )
        assert db_name == db_name
        assert database["TableCount"] == 0
        assert database["KmsKeyId"].startswith(
            f"arn:aws:kms:us-east-1:{account_id}:key/"
        )
        assert "CreationTime" in database
        assert "LastUpdatedTime" in database
    finally:
        ts.delete_database(DatabaseName=db_name)


@mock_timestreamwrite
def test_create_database_advanced():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    resp = ts.create_database(
        DatabaseName="mydatabase",
        KmsKeyId="mykey",
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )
    database = resp["Database"]

    assert database["Arn"] == (
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase"
    )
    assert database["DatabaseName"] == "mydatabase"
    assert database["TableCount"] == 0
    assert database["KmsKeyId"] == "mykey"


@mock_timestreamwrite
def test_describe_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase", KmsKeyId="mykey")

    database = ts.describe_database(DatabaseName="mydatabase")["Database"]

    assert database["Arn"] == (
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase"
    )
    assert database["DatabaseName"] == "mydatabase"
    assert database["TableCount"] == 0
    assert database["KmsKeyId"] == "mykey"


@pytest.mark.aws_verified
@timestreamwrite_aws_verified
def test_describe_unknown_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        ts.describe_database(DatabaseName="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The database unknown does not exist."


@mock_timestreamwrite
def test_list_databases():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="db_with", KmsKeyId="mykey")
    ts.create_database(DatabaseName="db_without")

    resp = ts.list_databases()
    databases = resp["Databases"]
    assert len(databases) == 2

    for db in databases:
        db.pop("CreationTime")
        db.pop("LastUpdatedTime")

    assert {
        "Arn": f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/db_with",
        "DatabaseName": "db_with",
        "TableCount": 0,
        "KmsKeyId": "mykey",
    } in databases
    assert {
        "Arn": f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/db_without",
        "DatabaseName": "db_without",
        "TableCount": 0,
        "KmsKeyId": f"arn:aws:kms:us-east-1:{ACCOUNT_ID}:key/default_key",
    } in databases


@mock_timestreamwrite
def test_delete_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="db_1", KmsKeyId="mykey")
    ts.create_database(DatabaseName="db_2")
    ts.create_database(DatabaseName="db_3", KmsKeyId="mysecondkey")

    assert len(ts.list_databases()["Databases"]) == 3

    ts.delete_database(DatabaseName="db_2")

    databases = ts.list_databases()["Databases"]
    assert len(databases) == 2
    assert [db["DatabaseName"] for db in databases] == ["db_1", "db_3"]


@mock_timestreamwrite
def test_update_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase", KmsKeyId="mykey")
    resp = ts.update_database(DatabaseName="mydatabase", KmsKeyId="updatedkey")
    assert "Database" in resp
    database = resp["Database"]
    assert "Arn" in database
    assert database["KmsKeyId"] == "updatedkey"

    database = ts.describe_database(DatabaseName="mydatabase")["Database"]
    assert database["KmsKeyId"] == "updatedkey"
