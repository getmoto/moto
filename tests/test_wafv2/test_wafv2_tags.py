import boto3

from moto import mock_aws

from .test_helper_functions import CREATE_WEB_ACL_BODY


@mock_aws
def test_list_tags_for_resource__none_supplied():
    conn = boto3.client("wafv2", region_name="us-east-1")
    arn = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))["Summary"][
        "ARN"
    ]

    tag_info = conn.list_tags_for_resource(ResourceARN=arn)["TagInfoForResource"]
    assert tag_info["TagList"] == []


@mock_aws
def test_list_tags_for_resource():
    conn = boto3.client("wafv2", region_name="us-east-1")
    arn = conn.create_web_acl(
        Name="test",
        Scope="CLOUDFRONT",
        DefaultAction={"Allow": {}},
        Tags=[{"Key": f"k{idx}", "Value": "v1"} for idx in range(10)],
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "idk",
        },
    )["Summary"]["ARN"]

    tag_info = conn.list_tags_for_resource(ResourceARN=arn)["TagInfoForResource"]
    assert len(tag_info["TagList"]) == 10

    page1 = conn.list_tags_for_resource(ResourceARN=arn, Limit=2)
    assert len(page1["TagInfoForResource"]["TagList"]) == 2

    page2 = conn.list_tags_for_resource(
        ResourceARN=arn, Limit=3, NextMarker=page1["NextMarker"]
    )
    assert len(page2["TagInfoForResource"]["TagList"]) == 3

    page3 = conn.list_tags_for_resource(ResourceARN=arn, NextMarker=page2["NextMarker"])
    assert len(page3["TagInfoForResource"]["TagList"]) == 5


@mock_aws
def test_tag_resource():
    conn = boto3.client("wafv2", region_name="us-east-1")
    arn = conn.create_web_acl(
        Name="test",
        Scope="CLOUDFRONT",
        DefaultAction={"Allow": {}},
        Tags=[{"Key": "k1", "Value": "v1"}],
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "idk",
        },
    )["Summary"]["ARN"]

    conn.tag_resource(
        ResourceARN=arn,
        Tags=[
            {"Key": "k2", "Value": "v2"},
        ],
    )

    tag_info = conn.list_tags_for_resource(ResourceARN=arn)["TagInfoForResource"]
    assert tag_info["TagList"] == [
        {"Key": "k1", "Value": "v1"},
        {"Key": "k2", "Value": "v2"},
    ]


@mock_aws
def test_untag_resource():
    conn = boto3.client("wafv2", region_name="us-east-1")
    arn = conn.create_web_acl(
        Name="test",
        Scope="CLOUDFRONT",
        DefaultAction={"Allow": {}},
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "idk",
        },
    )["Summary"]["ARN"]

    conn.untag_resource(ResourceARN=arn, TagKeys=["k1"])

    tag_info = conn.list_tags_for_resource(ResourceARN=arn)["TagInfoForResource"]
    assert tag_info["TagList"] == [{"Key": "k2", "Value": "v2"}]
