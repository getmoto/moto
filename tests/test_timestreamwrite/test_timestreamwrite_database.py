import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_timestreamwrite
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_timestreamwrite
def test_create_database_simple():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    resp = ts.create_database(DatabaseName="mydatabase")
    database = resp["Database"]

    database.should.have.key("Arn").equals(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase"
    )
    database.should.have.key("DatabaseName").equals("mydatabase")
    database.should.have.key("TableCount").equals(0)
    database.should.have.key("KmsKeyId").equals(
        f"arn:aws:kms:us-east-1:{ACCOUNT_ID}:key/default_key"
    )


@mock_timestreamwrite
def test_create_database_advanced():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    resp = ts.create_database(
        DatabaseName="mydatabase",
        KmsKeyId="mykey",
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )
    database = resp["Database"]

    database.should.have.key("Arn").equals(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase"
    )
    database.should.have.key("DatabaseName").equals("mydatabase")
    database.should.have.key("TableCount").equals(0)
    database.should.have.key("KmsKeyId").equal("mykey")


@mock_timestreamwrite
def test_describe_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase", KmsKeyId="mykey")

    database = ts.describe_database(DatabaseName="mydatabase")["Database"]

    database.should.have.key("Arn").equals(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase"
    )
    database.should.have.key("DatabaseName").equals("mydatabase")
    database.should.have.key("TableCount").equals(0)
    database.should.have.key("KmsKeyId").equal("mykey")


@mock_timestreamwrite
def test_describe_unknown_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        ts.describe_database(DatabaseName="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The database unknown does not exist.")


@mock_timestreamwrite
def test_list_databases():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="db_with", KmsKeyId="mykey")
    ts.create_database(DatabaseName="db_without")

    resp = ts.list_databases()
    databases = resp["Databases"]
    databases.should.have.length_of(2)
    databases.should.contain(
        {
            "Arn": f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/db_with",
            "DatabaseName": "db_with",
            "TableCount": 0,
            "KmsKeyId": "mykey",
        }
    )
    databases.should.contain(
        {
            "Arn": f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/db_without",
            "DatabaseName": "db_without",
            "TableCount": 0,
            "KmsKeyId": f"arn:aws:kms:us-east-1:{ACCOUNT_ID}:key/default_key",
        }
    )


@mock_timestreamwrite
def test_delete_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="db_1", KmsKeyId="mykey")
    ts.create_database(DatabaseName="db_2")
    ts.create_database(DatabaseName="db_3", KmsKeyId="mysecondkey")

    ts.list_databases()["Databases"].should.have.length_of(3)

    ts.delete_database(DatabaseName="db_2")

    databases = ts.list_databases()["Databases"]
    databases.should.have.length_of(2)
    [db["DatabaseName"] for db in databases].should.equal(["db_1", "db_3"])


@mock_timestreamwrite
def test_update_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase", KmsKeyId="mykey")
    resp = ts.update_database(DatabaseName="mydatabase", KmsKeyId="updatedkey")
    resp.should.have.key("Database")
    database = resp["Database"]
    database.should.have.key("Arn")
    database.should.have.key("KmsKeyId").equal("updatedkey")

    database = ts.describe_database(DatabaseName="mydatabase")["Database"]
    database.should.have.key("KmsKeyId").equal("updatedkey")
