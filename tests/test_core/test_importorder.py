import boto3
import pytest
import sure  # noqa
from moto import mock_s3
from os import environ


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    environ["AWS_ACCESS_KEY_ID"] = "testing"
    environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    environ["AWS_SECURITY_TOKEN"] = "testing"
    environ["AWS_SESSION_TOKEN"] = "testing"


def test_mock_works_with_client_created_inside(aws_credentials):
    m = mock_s3()
    m.start()
    client = boto3.client("s3", region_name="us-east-1")

    b = client.list_buckets()
    b["Buckets"].should.be.empty
    m.stop()


def test_mock_works_with_client_created_outside(aws_credentials):
    # Create the boto3 client first
    outside_client = boto3.client("s3", region_name="us-east-1")

    # Start the mock afterwards - which does not mock an already created client
    m = mock_s3()
    m.start()

    # So remind us to mock this client
    from moto.core import patch_client

    patch_client(outside_client)

    b = outside_client.list_buckets()
    b["Buckets"].should.be.empty
    m.stop()


class ImportantBusinessLogic:
    def __init__(self):
        self._s3 = boto3.client("s3", region_name="us-east-1")

    def do_important_things(self):
        return self._s3.list_buckets()["Buckets"]


def test_mock_works_when_replacing_client(aws_credentials):

    logic = ImportantBusinessLogic()

    m = mock_s3()
    m.start()

    # This will fail, as the S3 client was created before the mock was initialized
    try:
        logic.do_important_things()
    except Exception as e:
        str(e).should.contain("InvalidAccessKeyId")

    client_initialized_after_mock = boto3.client("s3", region_name="us-east-1")
    logic._s3 = client_initialized_after_mock
    # This will work, as we now use a properly mocked client
    logic.do_important_things().should.equal([])

    m.stop()
