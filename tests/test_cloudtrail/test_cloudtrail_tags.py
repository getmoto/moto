import boto3

from moto import mock_cloudtrail, mock_s3, mock_sns

from .test_cloudtrail import create_trail_simple, create_trail_advanced


@mock_cloudtrail
@mock_s3
def test_add_tags():
    client = boto3.client("cloudtrail", region_name="ap-southeast-1")
    _, resp, _ = create_trail_simple(region_name="ap-southeast-1")
    trail_arn = resp["TrailARN"]

    client.add_tags(ResourceId=trail_arn, TagsList=[{"Key": "k1", "Value": "v1"}])

    resp = client.list_tags(ResourceIdList=[trail_arn])
    resp.should.have.key("ResourceTagList").length_of(1)
    resp["ResourceTagList"][0].should.equal(
        {"ResourceId": trail_arn, "TagsList": [{"Key": "k1", "Value": "v1"}]}
    )


@mock_cloudtrail
@mock_s3
@mock_sns
def test_remove_tags():
    client = boto3.client("cloudtrail", region_name="ap-southeast-1")
    # Start with two tags
    _, resp, _, _ = create_trail_advanced(region_name="ap-southeast-1")
    trail_arn = resp["TrailARN"]

    # Add a third tag
    client.add_tags(ResourceId=trail_arn, TagsList=[{"Key": "tk3", "Value": "tv3"}])

    # Remove the second tag
    client.remove_tags(ResourceId=trail_arn, TagsList=[{"Key": "tk2", "Value": "tv2"}])

    # Verify the first and third tag are still there
    resp = client.list_tags(ResourceIdList=[trail_arn])
    resp.should.have.key("ResourceTagList").length_of(1)
    resp["ResourceTagList"][0].should.equal(
        {
            "ResourceId": trail_arn,
            "TagsList": [{"Key": "tk", "Value": "tv"}, {"Key": "tk3", "Value": "tv3"}],
        }
    )


@mock_cloudtrail
@mock_s3
def test_create_trail_without_tags_and_list_tags():
    client = boto3.client("cloudtrail", region_name="us-east-2")
    _, resp, _ = create_trail_simple(region_name="us-east-2")
    trail_arn = resp["TrailARN"]

    resp = client.list_tags(ResourceIdList=[trail_arn])
    resp.should.have.key("ResourceTagList").length_of(1)
    resp["ResourceTagList"][0].should.equal({"ResourceId": trail_arn, "TagsList": []})


@mock_cloudtrail
@mock_s3
@mock_sns
def test_create_trail_with_tags_and_list_tags():
    client = boto3.client("cloudtrail", region_name="us-east-2")
    _, resp, _, _ = create_trail_advanced(region_name="us-east-2")
    trail_arn = resp["TrailARN"]

    resp = client.list_tags(ResourceIdList=[trail_arn])
    resp.should.have.key("ResourceTagList").length_of(1)
    resp["ResourceTagList"][0].should.equal(
        {
            "ResourceId": trail_arn,
            "TagsList": [{"Key": "tk", "Value": "tv"}, {"Key": "tk2", "Value": "tv2"}],
        }
    )
