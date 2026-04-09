import boto3

from moto import mock_aws


# Tests for tagging Firehose resources
@mock_aws
def test_firehose():
    client = boto3.client("firehose", region_name="us-east-2")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-2")
    client.create_delivery_stream(
        DeliveryStreamName="my-stream",
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::123456789012:role/my-role",
            "BucketARN": "arn:aws:s3:::my-bucket",
        },
        Tags=[{"Key": "key1", "Value": "val1"}],
    )
    resp = rtapi.get_resources(ResourceTypeFilters=["firehose"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"].startswith(
        "arn:aws:firehose:us-east-2:"
    )
    assert resp["ResourceTagMappingList"][0]["Tags"] == [
        {"Key": "key1", "Value": "val1"}
    ]


# Tests for tagging Firehose resources no tags or tag filters
@mock_aws
def test_firehose_no_tags_or_filters():
    client = boto3.client("firehose", region_name="us-east-2")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-2")
    client.create_delivery_stream(
        DeliveryStreamName="my-stream",
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::123456789012:role/my-role",
            "BucketARN": "arn:aws:s3:::my-bucket",
        },
        Tags=[{"Key": "key1", "Value": "val1"}],
    )

    resp = rtapi.get_resources()
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"].startswith(
        "arn:aws:firehose:us-east-2:"
    )
    assert resp["ResourceTagMappingList"][0]["Tags"] == [
        {"Key": "key1", "Value": "val1"}
    ]
