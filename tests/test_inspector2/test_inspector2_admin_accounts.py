import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_deleted_accounts():
    client = boto3.client("inspector2", region_name="us-east-1")

    assert client.list_delegated_admin_accounts()["delegatedAdminAccounts"] == []

    resp = client.enable_delegated_admin_account(delegatedAdminAccountId="111111111111")
    assert resp["delegatedAdminAccountId"] == "111111111111"

    assert client.list_delegated_admin_accounts()["delegatedAdminAccounts"] == [
        {"accountId": "111111111111", "status": "ENABLED"}
    ]

    resp = client.disable_delegated_admin_account(
        delegatedAdminAccountId="111111111111"
    )
    assert resp["delegatedAdminAccountId"] == "111111111111"

    assert client.list_delegated_admin_accounts()["delegatedAdminAccounts"] == [
        {"accountId": "111111111111", "status": "DISABLED"}
    ]
