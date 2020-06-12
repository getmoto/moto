from __future__ import unicode_literals

from botocore.exceptions import ClientError
from nose.tools import assert_raises
import boto3
import sure  # noqa

from moto import mock_athena


@mock_athena
def test_create_work_group():
    client = boto3.client("athena", region_name="us-east-1")

    response = client.create_work_group(
        Name="athena_workgroup",
        Description="Test work group",
        Configuration={
            "ResultConfiguration": {
                "OutputLocation": "s3://bucket-name/prefix/",
                "EncryptionConfiguration": {
                    "EncryptionOption": "SSE_KMS",
                    "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                },
            }
        },
        Tags=[],
    )

    try:
        # The second time should throw an error
        response = client.create_work_group(
            Name="athena_workgroup",
            Description="duplicate",
            Configuration={
                "ResultConfiguration": {
                    "OutputLocation": "s3://bucket-name/prefix/",
                    "EncryptionConfiguration": {
                        "EncryptionOption": "SSE_KMS",
                        "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                    },
                }
            },
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidRequestException")
        err.response["Error"]["Message"].should.equal("WorkGroup already exists")
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")

    # Then test the work group appears in the work group list
    response = client.list_work_groups()

    response["WorkGroups"].should.have.length_of(1)
    work_group = response["WorkGroups"][0]
    work_group["Name"].should.equal("athena_workgroup")
    work_group["Description"].should.equal("Test work group")
    work_group["State"].should.equal("ENABLED")


@mock_athena
def test_create_and_get_workgroup():
    client = boto3.client("athena", region_name="us-east-1")

    create_basic_workgroup(client=client, name="athena_workgroup")

    work_group = client.get_work_group(WorkGroup="athena_workgroup")["WorkGroup"]
    del work_group["CreationTime"]  # Were not testing creationtime atm
    work_group.should.equal(
        {
            "Name": "athena_workgroup",
            "State": "ENABLED",
            "Configuration": {
                "ResultConfiguration": {"OutputLocation": "s3://bucket-name/prefix/"}
            },
            "Description": "Test work group",
        }
    )


@mock_athena
def test_start_query_execution():
    client = boto3.client("athena", region_name="us-east-1")

    create_basic_workgroup(client=client, name="athena_workgroup")
    response = client.start_query_execution(
        QueryString="query1",
        QueryExecutionContext={"Database": "string"},
        ResultConfiguration={"OutputLocation": "string"},
        WorkGroup="athena_workgroup",
    )
    assert "QueryExecutionId" in response

    sec_response = client.start_query_execution(
        QueryString="query2",
        QueryExecutionContext={"Database": "string"},
        ResultConfiguration={"OutputLocation": "string"},
    )
    assert "QueryExecutionId" in sec_response
    response["QueryExecutionId"].shouldnt.equal(sec_response["QueryExecutionId"])


@mock_athena
def test_start_query_validate_workgroup():
    client = boto3.client("athena", region_name="us-east-1")

    with assert_raises(ClientError) as err:
        client.start_query_execution(
            QueryString="query1",
            QueryExecutionContext={"Database": "string"},
            ResultConfiguration={"OutputLocation": "string"},
            WorkGroup="unknown_workgroup",
        )
    err.exception.response["Error"]["Code"].should.equal("InvalidRequestException")
    err.exception.response["Error"]["Message"].should.equal("WorkGroup does not exist")


@mock_athena
def test_get_query_execution():
    client = boto3.client("athena", region_name="us-east-1")

    query = "SELECT stuff"
    location = "s3://bucket-name/prefix/"
    database = "database"
    # Start Query
    exex_id = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": location},
    )["QueryExecutionId"]
    #
    details = client.get_query_execution(QueryExecutionId=exex_id)["QueryExecution"]
    #
    details["QueryExecutionId"].should.equal(exex_id)
    details["Query"].should.equal(query)
    details["StatementType"].should.equal("DDL")
    details["ResultConfiguration"]["OutputLocation"].should.equal(location)
    details["QueryExecutionContext"]["Database"].should.equal(database)
    details["Status"]["State"].should.equal("QUEUED")
    details["Statistics"].should.equal(
        {
            "EngineExecutionTimeInMillis": 0,
            "DataScannedInBytes": 0,
            "TotalExecutionTimeInMillis": 0,
            "QueryQueueTimeInMillis": 0,
            "QueryPlanningTimeInMillis": 0,
            "ServiceProcessingTimeInMillis": 0,
        }
    )
    assert "WorkGroup" not in details


@mock_athena
def test_stop_query_execution():
    client = boto3.client("athena", region_name="us-east-1")

    query = "SELECT stuff"
    location = "s3://bucket-name/prefix/"
    database = "database"
    # Start Query
    exex_id = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": location},
    )["QueryExecutionId"]
    # Stop Query
    client.stop_query_execution(QueryExecutionId=exex_id)
    # Verify status
    details = client.get_query_execution(QueryExecutionId=exex_id)["QueryExecution"]
    #
    details["QueryExecutionId"].should.equal(exex_id)
    details["Status"]["State"].should.equal("CANCELLED")


def create_basic_workgroup(client, name):
    client.create_work_group(
        Name=name,
        Description="Test work group",
        Configuration={
            "ResultConfiguration": {"OutputLocation": "s3://bucket-name/prefix/",}
        },
    )
