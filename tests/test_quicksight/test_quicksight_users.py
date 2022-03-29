"""Unit tests for quicksight-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_quicksight
from moto.core import ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_quicksight
def test_register_user__quicksight():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="tfacctestm9hpsr970z",
        UserRole="READER",
    )

    resp.should.have.key("UserInvitationUrl")
    resp.should.have.key("User")

    resp["User"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/tfacctestm9hpsr970z"
    )
    resp["User"].should.have.key("UserName").equals("tfacctestm9hpsr970z")
    resp["User"].should.have.key("Email").equals("fakeemail@example.com")
    resp["User"].should.have.key("Role").equals("READER")
    resp["User"].should.have.key("IdentityType").equals("QUICKSIGHT")
    resp["User"].should.have.key("Active").equals(False)


@mock_quicksight
def test_describe_user__quicksight():
    client = boto3.client("quicksight", region_name="us-east-1")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="tfacctestm9hpsr970z",
        UserRole="READER",
    )

    resp = client.describe_user(
        UserName="tfacctestm9hpsr970z", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    resp.should.have.key("User")

    resp["User"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:user/default/tfacctestm9hpsr970z"
    )
    resp["User"].should.have.key("UserName").equals("tfacctestm9hpsr970z")
    resp["User"].should.have.key("Email").equals("fakeemail@example.com")
    resp["User"].should.have.key("Role").equals("READER")
    resp["User"].should.have.key("IdentityType").equals("QUICKSIGHT")
    resp["User"].should.have.key("Active").equals(False)


@mock_quicksight
def test_delete_user__quicksight():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="tfacctestm9hpsr970z",
        UserRole="READER",
    )

    client.delete_user(
        UserName="tfacctestm9hpsr970z", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    with pytest.raises(ClientError) as exc:
        client.describe_user(
            UserName="tfacctestm9hpsr970z", AwsAccountId=ACCOUNT_ID, Namespace="default"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
