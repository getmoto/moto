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
