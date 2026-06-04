import boto3

from moto import mock_aws


@mock_aws
def test_get_tag_and_untag_resources_firehose():
    client = boto3.client("firehose", region_name="us-east-2")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-2")

    # Create a tagged delivery stream
    stream_arn = client.create_delivery_stream(
        DeliveryStreamName="my-stream",
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::123456789012:role/my-role",
            "BucketARN": "arn:aws:s3:::my-bucket",
        },
        Tags=[{"Key": "Test", "Value": "1"}],
    )["DeliveryStreamARN"]

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["firehose"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == stream_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(
        ResourceARNList=[stream_arn],
        Tags={"Test2": "2"},
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["firehose"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert {"Key": "Test", "Value": "1"} in tags
    assert {"Key": "Test2", "Value": "2"} in tags

    # Filtering on the newly-added tag returns the stream
    resp = rtapi.get_resources(
        ResourceTypeFilters=["firehose"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == stream_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(
        ResourceARNList=[stream_arn],
        TagKeys=["Test"],
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["firehose"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert tags == [{"Key": "Test2", "Value": "2"}]

    # The removed tag no longer matches
    resp = rtapi.get_resources(
        ResourceTypeFilters=["firehose"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
