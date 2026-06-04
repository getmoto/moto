import boto3
import pytest

from moto import mock_aws


def _create_tagged_buckets(s3, region):
    create_args = {"Bucket": "rgtapi-bucket-1"}
    if region != "us-east-1":
        create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**create_args)
    s3.put_bucket_tagging(
        Bucket="rgtapi-bucket-1",
        Tagging={
            "TagSet": [
                {"Key": "env", "Value": "prod"},
                {"Key": "team", "Value": "platform"},
            ]
        },
    )

    create_args = {"Bucket": "rgtapi-bucket-2"}
    if region != "us-east-1":
        create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**create_args)
    s3.put_bucket_tagging(
        Bucket="rgtapi-bucket-2",
        Tagging={"TagSet": [{"Key": "env", "Value": "dev"}]},
    )

    # Untagged bucket should not be returned by GetResources.
    create_args = {"Bucket": "rgtapi-bucket-untagged"}
    if region != "us-east-1":
        create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**create_args)


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_get_resources_returns_s3_buckets():
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_buckets(s3, "us-east-1")

    result = rtapi.get_resources(ResourceTypeFilters=["s3:bucket"])
    by_arn = {r["ResourceARN"]: r["Tags"] for r in result["ResourceTagMappingList"]}

    assert len(by_arn) == 2
    assert "arn:aws:s3:::rgtapi-bucket-1" in by_arn
    assert "arn:aws:s3:::rgtapi-bucket-2" in by_arn
    assert {"Key": "env", "Value": "prod"} in by_arn["arn:aws:s3:::rgtapi-bucket-1"]
    assert {"Key": "team", "Value": "platform"} in by_arn[
        "arn:aws:s3:::rgtapi-bucket-1"
    ]
    assert by_arn["arn:aws:s3:::rgtapi-bucket-2"] == [{"Key": "env", "Value": "dev"}]


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_get_resources_service_prefix_matches_s3():
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_buckets(s3, "us-east-1")

    result = rtapi.get_resources(ResourceTypeFilters=["s3"])
    arns = {r["ResourceARN"] for r in result["ResourceTagMappingList"]}
    assert "arn:aws:s3:::rgtapi-bucket-1" in arns
    assert "arn:aws:s3:::rgtapi-bucket-2" in arns


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_get_resources_filters_s3_by_tag_value():
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_buckets(s3, "us-east-1")

    result = rtapi.get_resources(
        ResourceTypeFilters=["s3:bucket"],
        TagFilters=[{"Key": "env", "Values": ["prod"]}],
    )
    arns = [r["ResourceARN"] for r in result["ResourceTagMappingList"]]
    assert arns == ["arn:aws:s3:::rgtapi-bucket-1"]


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_s3_visible_from_other_region():
    # S3 is partition-global; buckets created in us-east-1 must be visible
    # to a rgtapi client in any other region in the same partition.
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-west-1")
    _create_tagged_buckets(s3, "us-east-1")

    result = rtapi.get_resources(ResourceTypeFilters=["s3:bucket"])
    arns = {r["ResourceARN"] for r in result["ResourceTagMappingList"]}
    assert "arn:aws:s3:::rgtapi-bucket-1" in arns
    assert "arn:aws:s3:::rgtapi-bucket-2" in arns


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_get_tag_keys_and_values_include_s3():
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_buckets(s3, "us-east-1")

    keys = rtapi.get_tag_keys()["TagKeys"]
    assert "env" in keys
    assert "team" in keys

    env_values = rtapi.get_tag_values(Key="env")["TagValues"]
    assert set(env_values) >= {"prod", "dev"}


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_tag_resources_updates_s3_bucket():
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_buckets(s3, "us-east-1")
    arn = "arn:aws:s3:::rgtapi-bucket-1"

    response = rtapi.tag_resources(
        ResourceARNList=[arn],
        Tags={"owner": "dataops", "env": "staging"},
    )
    assert response.get("FailedResourcesMap", {}) == {}

    tags = s3.get_bucket_tagging(Bucket="rgtapi-bucket-1")["TagSet"]
    by_key = {t["Key"]: t["Value"] for t in tags}
    # New tag added.
    assert by_key["owner"] == "dataops"
    # Existing key updated.
    assert by_key["env"] == "staging"
    # Pre-existing unrelated tag preserved.
    assert by_key["team"] == "platform"


@mock_aws
@pytest.mark.requires_clean_slate
def test_rgtapi_untag_resources_removes_s3_tags():
    s3 = boto3.client("s3", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_buckets(s3, "us-east-1")
    arn = "arn:aws:s3:::rgtapi-bucket-1"

    response = rtapi.untag_resources(ResourceARNList=[arn], TagKeys=["env"])
    assert response.get("FailedResourcesMap", {}) == {}

    tags = s3.get_bucket_tagging(Bucket="rgtapi-bucket-1")["TagSet"]
    keys = {t["Key"] for t in tags}
    assert "env" not in keys
    assert "team" in keys
