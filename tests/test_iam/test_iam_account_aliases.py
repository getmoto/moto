import boto3
from moto import mock_iam


@mock_iam()
def test_account_aliases():
    client = boto3.client("iam", region_name="us-east-1")

    alias = "my-account-name"
    aliases = client.list_account_aliases()
    assert aliases["AccountAliases"] == []

    client.create_account_alias(AccountAlias=alias)
    aliases = client.list_account_aliases()
    assert aliases["AccountAliases"] == [alias]

    client.delete_account_alias(AccountAlias=alias)
    aliases = client.list_account_aliases()
    assert aliases["AccountAliases"] == []
