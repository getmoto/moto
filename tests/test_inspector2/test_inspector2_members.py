import boto3

from moto import mock_inspector2
from tests import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_inspector2
def test_members():
    client = boto3.client("inspector2", region_name="us-east-1")

    assert client.list_members()["members"] == []

    resp = client.associate_member(accountId="111111111111")
    assert resp["accountId"] == "111111111111"

    resp = client.get_member(accountId="111111111111")["member"]
    assert resp["accountId"] == "111111111111"
    assert resp["delegatedAdminAccountId"] == DEFAULT_ACCOUNT_ID
    assert resp["relationshipStatus"] == "ENABLED"
