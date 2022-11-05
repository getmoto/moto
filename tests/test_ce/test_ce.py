"""Unit tests for ce-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_ce
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_ce
def test_create_cost_category_definition():
    client = boto3.client("ce", region_name="ap-southeast-1")
    resp = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
    )
    resp.should.have.key("CostCategoryArn").match(
        f"arn:aws:ce::{ACCOUNT_ID}:costcategory/"
    )


@mock_ce
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
    resp.should.have.key("Name").equals("ccd")
    resp.should.have.key("CostCategoryArn").equals(ccd_arn)
    resp.should.have.key("RuleVersion").equals("CostCategoryExpression.v1")
    resp.should.have.key("Rules").length_of(1)
    resp["Rules"][0].should.equal(
        {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
    )


@mock_ce
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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"No Cost Categories found with ID {ccd_id}")


@mock_ce
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
    resp.should.have.key("Name").equals("ccd")
    resp.should.have.key("CostCategoryArn").equals(ccd_arn)
    resp.should.have.key("RuleVersion").equals("CostCategoryExpression.v1")

    resp.should.have.key("Rules").length_of(1)
    resp["Rules"][0].should.equal(
        {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
    )

    resp.should.have.key("SplitChargeRules").length_of(1)
    resp["SplitChargeRules"][0].should.equal(
        {"Source": "s", "Targets": ["t1"], "Method": "EVEN"}
    )
