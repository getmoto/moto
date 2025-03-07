import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.utilities.utils import is_valid_uuid


@mock_aws
def test_create_rule_group():
    client = boto3.client("wafv2", region_name="ap-southeast-1")
    resp = client.create_rule_group(
        Capacity=100,
        Name="test-group",
        Scope="REGIONAL",
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "test-group",
        },
    )["Summary"]
    assert resp["ARN"].startswith(
        f"arn:aws:wafv2:ap-southeast-1:{ACCOUNT_ID}:regional/rulegroup/test-group/"
    )
    assert resp["Name"] == "test-group"
    assert resp["Description"] == ""
    assert is_valid_uuid(resp["Id"])
    assert is_valid_uuid(resp["LockToken"])
    assert "VisibilityConfig" not in resp
    assert "Rules" not in resp

    with pytest.raises(ClientError) as e:
        client.create_rule_group(
            Capacity=100,
            Name="test-group",
            Scope="REGIONAL",
            VisibilityConfig={
                "SampledRequestsEnabled": False,
                "CloudWatchMetricsEnabled": False,
                "MetricName": "test-group",
            },
        )
    assert e.value.response["Error"]["Code"] == "WafV2DuplicateItem"


@mock_aws
def test_update_rule_group():
    client = boto3.client("wafv2", region_name="ap-southeast-1")
    group = client.create_rule_group(
        Capacity=100,
        Name="test-group",
        Scope="REGIONAL",
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "test-group",
        },
    )["Summary"]

    test_rule = {
        "Name": "test-rule",
        "Priority": 0,
        "Statement": {
            "LabelMatchStatement": {
                "Scope": "LABEL",
                "Key": "testlabelmatch",
            }
        },
        "Action": {
            "Allow": {},
        },
        "VisibilityConfig": {
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "test-rule",
        },
        "CaptchaConfig": {
            "ImmunityTimeProperty": {
                "ImmunityTime": 60,
            }
        },
        "ChallengeConfig": {
            "ImmunityTimeProperty": {
                "ImmunityTime": 60,
            }
        },
        "OverrideAction": {
            "Count": {},
            "None": {},
        },
        "RuleLabels": [
            {
                "Name": "testlabel",
            },
        ],
    }

    resp = client.update_rule_group(
        Name="test-group",
        Scope="REGIONAL",
        Id=group["Id"],
        Rules=[
            test_rule,
        ],
        LockToken=group["LockToken"],
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "new-metric",
        },
        Description="test",
        CustomResponseBodies={
            "Test": {
                "Content": "ohmylookatthiscontent",
                "ContentType": "TEXT_PLAIN",
            },
        },
    )
    assert (
        is_valid_uuid(resp["NextLockToken"])
        and resp["NextLockToken"] != group["LockToken"]
    )
    updated_group = client.get_rule_group(ARN=group["ARN"])["RuleGroup"]
    assert updated_group["VisibilityConfig"] == {
        "SampledRequestsEnabled": True,
        "CloudWatchMetricsEnabled": True,
        "MetricName": "new-metric",
    }
    assert updated_group["Description"] == "test"
    assert updated_group["CustomResponseBodies"] == {
        "Test": {
            "Content": "ohmylookatthiscontent",
            "ContentType": "TEXT_PLAIN",
        },
    }
    assert updated_group["Rules"][0] == test_rule

    with pytest.raises(ClientError) as e:
        client.update_rule_group(
            Name="test-group",
            Scope="REGIONAL",
            Id=group["Id"],
            LockToken="123",
            VisibilityConfig={
                "SampledRequestsEnabled": False,
                "CloudWatchMetricsEnabled": False,
                "MetricName": "new-metric",
            },
        )
    assert e.value.response["Error"]["Code"] == "WAFOptimisticLockException"

    with pytest.raises(ClientError) as e:
        client.update_rule_group(
            Name="bad-group",
            Scope="REGIONAL",
            Id=group["Id"],
            LockToken=group["LockToken"],
            VisibilityConfig={
                "SampledRequestsEnabled": False,
                "CloudWatchMetricsEnabled": False,
                "MetricName": "new-metric",
            },
        )
    assert e.value.response["Error"]["Code"] == "WAFNonexistentItemException"


@mock_aws
def test_delete_rule_group():
    client = boto3.client("wafv2", region_name="eu-west-1")
    group = client.create_rule_group(
        Capacity=100,
        Name="test-group-1",
        Scope="REGIONAL",
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "test-group-1",
        },
    )["Summary"]
    with pytest.raises(ClientError) as e:
        client.delete_rule_group(
            Name="test-group-1",
            Scope="CLOUDFRONT",
            Id=group["Id"],
            LockToken=group["LockToken"],
        )
    assert e.value.response["Error"]["Code"] == "WAFNonexistentItemException"

    with pytest.raises(ClientError) as e:
        client.delete_rule_group(
            Name="test-group-1",
            Scope="REGIONAL",
            Id=group["Id"],
            LockToken="1234567890",
        )
    assert e.value.response["Error"]["Code"] == "WAFOptimisticLockException"

    assert len(client.list_rule_groups(Scope="REGIONAL")["RuleGroups"]) == 1
    client.delete_rule_group(
        Name="test-group-1",
        Scope="REGIONAL",
        Id=group["Id"],
        LockToken=group["LockToken"],
    )
    assert len(client.list_rule_groups(Scope="REGIONAL")["RuleGroups"]) == 0


@mock_aws
def test_get_rule_group():
    client = boto3.client("wafv2", region_name="us-east-2")
    test_rule = {
        "Name": "test-rule",
        "Priority": 0,
        "Statement": {
            "LabelMatchStatement": {
                "Scope": "LABEL",
                "Key": "testlabelmatch",
            }
        },
        "Action": {
            "Allow": {},
        },
        "VisibilityConfig": {
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "test-rule",
        },
        "CaptchaConfig": {
            "ImmunityTimeProperty": {
                "ImmunityTime": 60,
            }
        },
        "ChallengeConfig": {
            "ImmunityTimeProperty": {
                "ImmunityTime": 60,
            }
        },
        "OverrideAction": {
            "Count": {},
            "None": {},
        },
        "RuleLabels": [
            {
                "Name": "testlabel",
            },
        ],
    }

    new_group = client.create_rule_group(
        Capacity=100,
        Name="test-group-all-params",
        Description="test",
        Scope="CLOUDFRONT",
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "test-group",
        },
        Rules=[
            test_rule,
        ],
        CustomResponseBodies={
            "Test": {
                "Content": "ohmylookatthiscontent",
                "ContentType": "TEXT_PLAIN",
            },
        },
        Tags=[
            {
                "Key": "test-key",
                "Value": "test-value",
            },
        ],
    )["Summary"]
    resp = client.get_rule_group(
        Id=new_group["Id"], Scope="CLOUDFRONT", Name="test-group-all-params"
    )
    group = resp["RuleGroup"]
    assert is_valid_uuid(resp["LockToken"])
    assert is_valid_uuid(group["Id"])
    assert group["ARN"] == new_group["ARN"]
    assert group["Capacity"] == 100
    assert group["CustomResponseBodies"] == {
        "Test": {
            "Content": "ohmylookatthiscontent",
            "ContentType": "TEXT_PLAIN",
        },
    }
    assert group["Description"] == "test"
    assert group["Id"] == new_group["Id"]
    assert group["Name"] == "test-group-all-params"
    assert (
        group["LabelNamespace"] == f"awswaf:{ACCOUNT_ID}:rulegroup:{new_group['Name']}:"
    )
    assert group["AvailableLabels"] == [{"Name": f"{group['LabelNamespace']}testlabel"}]
    assert group["ConsumedLabels"] == [
        {"Name": f"{group['LabelNamespace']}testlabelmatch"}
    ]
    assert group["Name"] == "test-group-all-params"
    assert group["Rules"][0] == test_rule
    assert group["VisibilityConfig"] == {
        "SampledRequestsEnabled": True,
        "CloudWatchMetricsEnabled": True,
        "MetricName": "test-group",
    }

    with pytest.raises(ClientError) as e:
        client.get_rule_group(
            ARN=f"arn:aws:wafv2:ap-southeast-1:{ACCOUNT_ID}:regional/rulegroup/test-group/1234567890)"
        )
    assert e.value.response["Error"]["Code"] == "WAFNonexistentItemException"

    with pytest.raises(ClientError) as e:
        client.get_rule_group(Name="test-group")
    assert e.value.response["Error"]["Code"] == "AcessDeniedException"
    assert (
        e.value.response["Error"]["Message"]
        == "Critical information is missing in your request: GetRuleGroupRequest(name=test-group, scope=null, id=null, aRN=null)."
    )


@mock_aws
def test_list_rule_groups():
    client = boto3.client("wafv2", region_name="us-east-2")
    assert len(client.list_rule_groups(Scope="REGIONAL")["RuleGroups"]) == 0
    regional_group = client.create_rule_group(
        Capacity=100,
        Name="test-group-1",
        Scope="REGIONAL",
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "test-group-1",
        },
    )["Summary"]
    for idx in range(2, 10):
        client.create_rule_group(
            Capacity=100,
            Name=f"test-group-{idx}",
            Scope="CLOUDFRONT",
            VisibilityConfig={
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": "test-group-2",
            },
        )["Summary"]

    reg_groups = client.list_rule_groups(Scope="REGIONAL")["RuleGroups"]
    assert len(reg_groups) == 1
    regional = reg_groups[0]
    assert regional["ARN"] == regional_group["ARN"]
    assert regional["Name"] == "test-group-1"
    assert "Scope" not in regional
    assert is_valid_uuid(regional["LockToken"])
    assert is_valid_uuid(regional["Id"]) and regional["Id"] == regional_group["Id"]
    assert "VisibilityConfig" not in regional

    cf_groups = client.list_rule_groups(Scope="CLOUDFRONT")["RuleGroups"]
    assert len(cf_groups) == 8
    assert cf_groups[0]["ARN"].startswith(
        f"arn:aws:wafv2:us-east-1:{ACCOUNT_ID}:global/rulegroup/test-group-2/"
    )

    page1 = client.list_rule_groups(Scope="CLOUDFRONT", Limit=2)
    assert len(page1["RuleGroups"]) == 2

    page2 = client.list_rule_groups(
        Scope="CLOUDFRONT", Limit=1, NextMarker=page1["NextMarker"]
    )
    assert len(page2["RuleGroups"]) == 1

    page3 = client.list_rule_groups(Scope="CLOUDFRONT", NextMarker=page2["NextMarker"])
    assert len(page3["RuleGroups"]) == 5
