import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core import disable_iam_authentication, enable_iam_authentication

from .test_auth import create_user_with_access_key_and_inline_policy


@mock_aws
def test_enable_iam_authentication__context_manager() -> None:
    # Note: This is the exact same test as 'test_auth.py::test_access_denied_explicitly_on_specific_resource'
    # Just using the `enable/disable_iam_authentication` context managers
    if not settings.TEST_DECORATOR_MODE:
        pytest.skip("ContextManagers can only be tested using decorators")
    user_name = "test-user"
    forbidden_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/forbidden_explicitly"
    allowed_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/allowed_implictly"
    role_session_name = "dummy"
    doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": ["sts:AssumeRole"],
                "Resource": forbidden_role_arn,
            },
            {"Effect": "Allow", "Action": ["sts:AssumeRole"], "Resource": "*"},
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, doc)
    client = boto3.client(
        "sts",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with enable_iam_authentication():
        # Auth is active - AssumeRole-operation is forbidden
        with pytest.raises(ClientError) as ex:
            client.assume_role(
                RoleArn=forbidden_role_arn, RoleSessionName=role_session_name
            )
        assert ex.value.response["Error"]["Code"] == "AccessDenied"

        # Auth is temporarily disabled - operation is allowed
        with disable_iam_authentication():
            client.assume_role(
                RoleArn=allowed_role_arn, RoleSessionName=role_session_name
            )

        ## IAM auth is active again
        with pytest.raises(ClientError) as ex:
            client.assume_role(
                RoleArn=forbidden_role_arn, RoleSessionName=role_session_name
            )
        assert ex.value.response["Error"]["Code"] == "AccessDenied"

    # No authentication outside of context manager
    client.assume_role(RoleArn=allowed_role_arn, RoleSessionName=role_session_name)
