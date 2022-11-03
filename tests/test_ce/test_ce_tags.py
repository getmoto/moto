import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ce

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_ce
def test_list_tags_if_none_exist():
    client = boto3.client("ce", region_name="ap-southeast-1")
    arn = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
    )["CostCategoryArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceTags").equals([])

    client.tag_resource(ResourceArn=arn, ResourceTags=[{"Key": "t1", "Value": "v1"}])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceTags").equals([{"Key": "t1", "Value": "v1"}])


@mock_ce
def test_cost_category_tags_workflow():
    client = boto3.client("ce", region_name="ap-southeast-1")
    arn = client.create_cost_category_definition(
        Name="ccd",
        RuleVersion="CostCategoryExpression.v1",
        Rules=[
            {"Value": "v", "Rule": {"CostCategories": {"Key": "k", "Values": ["v"]}}}
        ],
        ResourceTags=[{"Key": "t1", "Value": "v1"}],
    )["CostCategoryArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceTags").equals([{"Key": "t1", "Value": "v1"}])

    client.tag_resource(ResourceArn=arn, ResourceTags=[{"Key": "t2", "Value": "v2"}])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceTags").equals(
        [{"Key": "t1", "Value": "v1"}, {"Key": "t2", "Value": "v2"}]
    )

    client.untag_resource(ResourceArn=arn, ResourceTagKeys=["t2"])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceTags").equals([{"Key": "t1", "Value": "v1"}])
