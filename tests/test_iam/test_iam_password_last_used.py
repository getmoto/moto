from unittest import SkipTest

import boto3

from moto import mock_aws, settings
from moto.backends import get_backend
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import utcnow


@mock_aws
def test_password_last_used():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set password_last_used in ServerMode")
    client = boto3.client("iam", "us-east-1")
    username = "test.user"
    client.create_user(Path="/staff/", UserName=username)["User"]
    client.create_login_profile(
        UserName=username, Password="Password1", PasswordResetRequired=False
    )

    access_key = client.create_access_key(UserName=username)["AccessKey"]

    as_new_user = boto3.resource(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )

    # Username is set, but password not yet
    assert as_new_user.CurrentUser().user_name == username
    assert not as_new_user.CurrentUser().password_last_used

    iam_backend = get_backend("iam")[ACCOUNT_ID]["global"]
    iam_backend.users[username].password_last_used = utcnow()

    # Password is returned now
    assert as_new_user.CurrentUser().password_last_used
