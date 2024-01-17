import sys
from typing import Any, List
from unittest import SkipTest

import boto3
import pytest

from moto import mock_aws, settings
from moto.utilities.distutils_version import LooseVersion

boto3_version = sys.modules["botocore"].__version__


@pytest.fixture(scope="function", name="aws_credentials")
def fixture_aws_credentials(monkeypatch: Any) -> None:  # type: ignore[misc]
    """Mocked AWS Credentials for moto."""
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing this in ServerMode.")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def test_mock_works_with_client_created_inside(
    aws_credentials: Any,  # pylint: disable=unused-argument
) -> None:
    m = mock_aws()
    m.start()
    client = boto3.client("s3", region_name="us-east-1")

    b = client.list_buckets()
    assert b["Buckets"] == []
    m.stop()


def test_mock_works_with_client_created_outside(
    aws_credentials: Any,  # pylint: disable=unused-argument
) -> None:
    # Create the boto3 client first
    outside_client = boto3.client("s3", region_name="us-east-1")

    # Start the mock afterwards - which does not mock an already created client
    m = mock_aws()
    m.start()

    # So remind us to mock this client
    from moto.core import patch_client

    patch_client(outside_client)

    b = outside_client.list_buckets()
    assert b["Buckets"] == []
    m.stop()


def test_mock_works_with_resource_created_outside(
    aws_credentials: Any,  # pylint: disable=unused-argument
) -> None:
    # Create the boto3 client first
    outside_resource = boto3.resource("s3", region_name="us-east-1")

    # Start the mock afterwards - which does not mock an already created resource
    m = mock_aws()
    m.start()

    # So remind us to mock this resource
    from moto.core import patch_resource

    patch_resource(outside_resource)

    assert not list(outside_resource.buckets.all())
    m.stop()


def test_patch_can_be_called_on_a_mocked_client() -> None:
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Error handling is different in newer versions")
    # start S3 after the mock, ensuring that the client contains our event-handler
    m = mock_aws()
    m.start()
    client = boto3.client("s3", region_name="us-east-1")

    from moto.core import patch_client

    patch_client(client)
    patch_client(client)

    # At this point, our event-handler should only be registered once, by `mock_aws`
    # `patch_client` should not re-register the event-handler
    test_object = b"test_object_text"
    client.create_bucket(Bucket="buck")
    client.put_object(Bucket="buck", Key="to", Body=test_object)
    got_object = client.get_object(Bucket="buck", Key="to")["Body"].read()
    assert got_object == test_object

    m.stop()


def test_patch_client_does_not_work_for_random_parameters() -> None:
    from moto.core import patch_client

    with pytest.raises(Exception, match="Argument sth should be of type boto3.client"):
        patch_client("sth")  # type: ignore[arg-type]


def test_patch_resource_does_not_work_for_random_parameters() -> None:
    from moto.core import patch_resource

    with pytest.raises(
        Exception, match="Argument sth should be of type boto3.resource"
    ):
        patch_resource("sth")


class ImportantBusinessLogic:
    def __init__(self) -> None:
        self._s3 = boto3.client("s3", region_name="us-east-1")

    def do_important_things(self) -> List[str]:
        return self._s3.list_buckets()["Buckets"]


def test_mock_works_when_replacing_client(
    aws_credentials: Any,  # pylint: disable=unused-argument
) -> None:
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Error handling is different in newer versions")
    logic = ImportantBusinessLogic()

    m = mock_aws()
    m.start()

    # This will fail, as the S3 client was created before the mock was initialized
    try:
        logic.do_important_things()
    except Exception as e:
        assert str(e) == "InvalidAccessKeyId"

    client_initialized_after_mock = boto3.client("s3", region_name="us-east-1")
    logic._s3 = client_initialized_after_mock
    # This will work, as we now use a properly mocked client
    assert logic.do_important_things() == []

    m.stop()
