import boto3

from moto import mock_aws


@mock_aws
def test_tag_and_untag_resources_acm():
    client = boto3.client("acm", region_name="eu-central-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Create a tagged certificate
    cert_arn = client.request_certificate(
        DomainName="example.com",
        Tags=[{"Key": "Test", "Value": "1"}],
    )["CertificateArn"]

    # Basic test
    resp = rtapi.get_resources(ResourceARNList=[cert_arn])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == cert_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(
        ResourceARNList=[cert_arn],
        Tags={"Test2": "2"},
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceARNList=[cert_arn])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert {"Key": "Test", "Value": "1"} in tags
    assert {"Key": "Test2", "Value": "2"} in tags

    # Filtering on the newly-added tag returns the certificate
    resp = rtapi.get_resources(
        ResourceARNList=[cert_arn],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == cert_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(
        ResourceARNList=[cert_arn],
        TagKeys=["Test"],
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceARNList=[cert_arn])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert tags == [{"Key": "Test2", "Value": "2"}]

    # The removed tag no longer matches
    resp = rtapi.get_resources(
        ResourceARNList=[cert_arn],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
