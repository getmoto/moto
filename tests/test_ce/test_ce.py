import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_cost_category_definition():
    client = boto3.client("ce", region_name="ap-southeast-1")
    resp = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
    )
    assert resp["CostCategoryArn"].startswith(f"arn:aws:ce::{ACCOUNT_ID}:costcategory/")
    assert "EffectiveStart" in resp


@mock_aws
def test_create_cost_category_definition_with_effective_start():
    client = boto3.client("ce", region_name="ap-southeast-1")
    resp = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
        EffectiveStart="2022-11-01T00:00:00Z",
    )
    assert resp["CostCategoryArn"].startswith(f"arn:aws:ce::{ACCOUNT_ID}:costcategory/")
    assert resp["EffectiveStart"] == "2022-11-01T00:00:00Z"


@mock_aws
def test_describe_cost_category_definition():
    client = boto3.client("ce", region_name="us-east-2")
    ccd_arn = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
    )["CostCategoryArn"]

    resp = client.describe_cost_category_definition(CostCategoryArn=ccd_arn)[
        "CostCategory"
    ]
    assert resp["Name"] == "ccd"
    assert resp["CostCategoryArn"] == ccd_arn
    assert resp["RuleVersion"] == "CostCategoryExpression.v1"
    assert len(resp["Rules"]) == 1
    assert resp["Rules"][0] == {
        "Value": "v",
        "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}},
    }


@mock_aws
def test_delete_cost_category_definition():
    client = boto3.client("ce", region_name="ap-southeast-1")
    ccd_arn = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
    )["CostCategoryArn"]
    ccd_id = ccd_arn.split("/")[-1]

    client.delete_cost_category_definition(CostCategoryArn=ccd_arn)

    with pytest.raises(ClientError) as exc:
        client.describe_cost_category_definition(CostCategoryArn=ccd_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"No Cost Categories found with ID {ccd_id}"


@mock_aws
def test_update_cost_category_definition():
    client = boto3.client("ce", region_name="us-east-2")
    ccd_arn = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
    )["CostCategoryArn"]

    client.update_cost_category_definition(
        CostCategoryArn=ccd_arn,
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
        SplitChargeRules=[{"Source": "s", "Targets": ["t1"], "Method": "EVEN"}],
    )

    resp = client.describe_cost_category_definition(CostCategoryArn=ccd_arn)[
        "CostCategory"
    ]
    assert resp["Name"] == "ccd"
    assert resp["CostCategoryArn"] == ccd_arn
    assert resp["RuleVersion"] == "CostCategoryExpression.v1"

    assert len(resp["Rules"]) == 1
    assert resp["Rules"][0] == {
        "Value": "v",
        "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}},
    }

    assert len(resp["SplitChargeRules"]) == 1
    assert resp["SplitChargeRules"][0] == {
        "Source": "s",
        "Targets": ["t1"],
        "Method": "EVEN",
    }
