import boto3
import moto
import pytest


@pytest.fixture(scope="function", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3():
    with moto.mock_s3():
        session = boto3.Session(region_name="us-east-1")
        yield session.client("s3")


@pytest.fixture
def logs():
    with moto.mock_logs():
        session = boto3.Session(region_name="us-east-1")
        yield session.client("logs")


def test_create_export_task(logs, s3):
    lg1 = "/aws/codebuild/blah1"
    lg2 = "/aws/codebuild/blah2"
    destination = "mybucket"
    logs.create_log_group(logGroupName=lg1)
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=destination)
    print("printing destination...")
    print(destination)
    print("END")
    fromTime = 1611316574
    to = 1642852574
    task_id = logs.create_export_task(
        logGroupName=lg1, fromTime=fromTime, to=to, destination=destination
    )
    print(task_id)
