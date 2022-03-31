import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from moto import mock_s3
from moto import settings
from unittest import SkipTest


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing this in ServerMode.")
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def test_mock_works_with_client_created_inside(
    aws_credentials,
):  # pylint: disable=unused-argument
    m = mock_s3()
    m.start()
    client = boto3.client("s3", region_name="us-east-1")

    b = client.list_buckets()
    b["Buckets"].should.be.empty
    m.stop()


def test_mock_works_with_client_created_outside(
    aws_credentials,
):  # pylint: disable=unused-argument
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


def test_mock_works_with_resource_created_outside(
    aws_credentials,
):  # pylint: disable=unused-argument
    # Create the boto3 client first
    outside_resource = boto3.resource("s3", region_name="us-east-1")

    # Start the mock afterwards - which does not mock an already created resource
    m = mock_s3()
    m.start()

    # So remind us to mock this client
    from moto.core import patch_resource

    patch_resource(outside_resource)

    b = list(outside_resource.buckets.all())
    b.should.be.empty
    m.stop()


def test_patch_client_does_not_work_for_random_parameters():
    from moto.core import patch_client

    with pytest.raises(Exception, match="Argument sth should be of type boto3.client"):
        patch_client("sth")


def test_patch_resource_does_not_work_for_random_parameters():
    from moto.core import patch_resource

    with pytest.raises(
        Exception, match="Argument sth should be of type boto3.resource"
    ):
        patch_resource("sth")


class ImportantBusinessLogic:
    def __init__(self):
        self._s3 = boto3.client("s3", region_name="us-east-1")

    def do_important_things(self):
        return self._s3.list_buckets()["Buckets"]


def test_mock_works_when_replacing_client(
    aws_credentials,
):  # pylint: disable=unused-argument

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
