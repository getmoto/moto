import boto3

from moto import mock_aws


@mock_aws
def test_list_rule_groups():
    client = boto3.client("wafv2", region_name="us-east-2")
    resp = client.list_rule_groups(Scope="CLOUDFRONT")
    assert resp["RuleGroups"] == []
