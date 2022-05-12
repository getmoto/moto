import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_iam


@mock_iam()
def test_account_aliases():
    client = boto3.client("iam", region_name="us-east-1")

    alias = "my-account-name"
    aliases = client.list_account_aliases()
    aliases.should.have.key("AccountAliases").which.should.equal([])

    client.create_account_alias(AccountAlias=alias)
    aliases = client.list_account_aliases()
    aliases.should.have.key("AccountAliases").which.should.equal([alias])

    client.delete_account_alias(AccountAlias=alias)
    aliases = client.list_account_aliases()
    aliases.should.have.key("AccountAliases").which.should.equal([])
