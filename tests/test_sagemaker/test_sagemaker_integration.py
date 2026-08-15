import boto3

from moto import mock_aws

TEST_REGION_NAME = "us-east-1"
TEST_ROLE_ARN = "arn:aws:iam::123456789012:role/FooRole"


@mock_aws
def test_tag_and_untag_resources_sagemaker():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    rtapi = boto3.client("resourcegroupstaggingapi", region_name=TEST_REGION_NAME)

    # Create a tagged model
    model_arn = client.create_model(
        ModelName="my-model",
        ExecutionRoleArn=TEST_ROLE_ARN,
        Tags=[{"Key": "Test", "Value": "1"}],
    )["ModelArn"]

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["sagemaker:model"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == model_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(
        ResourceARNList=[model_arn],
        Tags={"Test2": "2"},
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["sagemaker:model"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert {"Key": "Test", "Value": "1"} in tags
    assert {"Key": "Test2", "Value": "2"} in tags

    # Filtering on the newly-added tag returns the model
    resp = rtapi.get_resources(
        ResourceTypeFilters=["sagemaker:model"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == model_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(
        ResourceARNList=[model_arn],
        TagKeys=["Test"],
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=["sagemaker:model"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert tags == [{"Key": "Test2", "Value": "2"}]

    # The removed tag no longer matches
    resp = rtapi.get_resources(
        ResourceTypeFilters=["sagemaker:model"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
