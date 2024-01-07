import boto3

from moto import mock_aws


@mock_aws
def test_enable_organization_admin_account():
    client = boto3.client("guardduty", region_name="us-east-1")
    resp = client.enable_organization_admin_account(AdminAccountId="")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_list_organization_admin_accounts():
    client = boto3.client("guardduty", region_name="us-east-1")
    client.enable_organization_admin_account(AdminAccountId="someaccount")

    resp = client.list_organization_admin_accounts()
    assert len(resp["AdminAccounts"]) == 1
    assert {"AdminAccountId": "someaccount", "AdminStatus": "ENABLED"} in resp[
        "AdminAccounts"
    ]
