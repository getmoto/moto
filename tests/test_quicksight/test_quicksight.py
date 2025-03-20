import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_describe_account_settings():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.describe_account_settings(AwsAccountId=ACCOUNT_ID)
    assert resp["AccountSettings"]["AccountName"] == "default"
    assert resp["AccountSettings"]["Edition"] == "STANDARD"
    assert resp["AccountSettings"]["PublicSharingEnabled"] is False
    assert resp["AccountSettings"]["TerminationProtectionEnabled"] is False


@mock_aws
def test_update_account_settings():
    client = boto3.client("quicksight", region_name="eu-west-1")
    client.update_account_settings(
        AwsAccountId=ACCOUNT_ID,
        DefaultNamespace="default",
        NotificationEmail="test@moto.com",
        TerminationProtectionEnabled=True,
    )

    resp = client.describe_account_settings(AwsAccountId=ACCOUNT_ID)
    assert resp["AccountSettings"]["TerminationProtectionEnabled"] is True
    assert resp["AccountSettings"]["NotificationEmail"] == "test@moto.com"

    client.update_account_settings(
        AwsAccountId=ACCOUNT_ID,
        DefaultNamespace="default",
        NotificationEmail="test2@moto.com",
    )
    resp = client.describe_account_settings(AwsAccountId=ACCOUNT_ID)
    assert resp["AccountSettings"]["TerminationProtectionEnabled"] is True
    assert resp["AccountSettings"]["NotificationEmail"] == "test2@moto.com"


@mock_aws
def test_update_public_sharing_settings():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.update_public_sharing_settings(
        AwsAccountId=ACCOUNT_ID, PublicSharingEnabled=True
    )
    resp = client.describe_account_settings(AwsAccountId=ACCOUNT_ID)
    assert resp["AccountSettings"]["PublicSharingEnabled"] is True

    client.update_public_sharing_settings(
        AwsAccountId=ACCOUNT_ID, PublicSharingEnabled=False
    )
    resp = client.describe_account_settings(AwsAccountId=ACCOUNT_ID)
    assert resp["AccountSettings"]["PublicSharingEnabled"] is False
