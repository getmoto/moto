import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_s3, settings
from moto.core import set_initial_no_auth_action_count
from unittest import SkipTest


@mock_s3
@set_initial_no_auth_action_count(0)
def test_load_unexisting_object_without_auth_should_return_403():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    """Head an S3 object we should have no access to."""
    resource = boto3.resource("s3", region_name="us-east-1")

    obj = resource.Object("myfakebucket", "myfakekey")
    with pytest.raises(ClientError) as ex:
        obj.load()
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidAccessKeyId")
    err["Message"].should.equal(
        "The AWS Access Key Id you provided does not exist in our records."
    )
