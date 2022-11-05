import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_guardduty


@mock_guardduty
def test_enable_organization_admin_account():
    client = boto3.client("guardduty", region_name="us-east-1")
    resp = client.enable_organization_admin_account(AdminAccountId="")
    resp.should.have.key("ResponseMetadata")
    resp["ResponseMetadata"].should.have.key("HTTPStatusCode").equals(200)


@mock_guardduty
def test_list_organization_admin_accounts():
    client = boto3.client("guardduty", region_name="us-east-1")
    client.enable_organization_admin_account(AdminAccountId="someaccount")

    resp = client.list_organization_admin_accounts()
    resp.should.have.key("AdminAccounts").length_of(1)
    resp["AdminAccounts"].should.contain(
        {"AdminAccountId": "someaccount", "AdminStatus": "ENABLED"}
    )
