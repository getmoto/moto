import boto3

from moto import mock_aws
from tests.test_comprehend.test_comprehend import DOCUMENT_CLASSIFIER_INPUT_DATA_CONFIG


@mock_aws
def test_tags_from_resourcegroupsapi():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=DOCUMENT_CLASSIFIER_INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="tf-acc-test-1726651689102157637",
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )["DocumentClassifierArn"]

    resource_groups_client = boto3.client(
        "resourcegroupstaggingapi", region_name="ap-southeast-1"
    )
    tags = resource_groups_client.get_resources(
        ResourceARNList=[arn],
    )["ResourceTagMappingList"]
    assert tags == [
        {
            "ResourceARN": arn,
            "Tags": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
        }
    ]
