import boto3

from moto import mock_aws
from moto.comprehend.models import comprehend_backends
from tests.test_comprehend.test_comprehend import (
    DOCUMENT_CLASSIFIER_INPUT_DATA_CONFIG,
)


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

    job_id = client.start_document_classification_job(
        JobName="test-job",
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig={
            "S3Uri": "s3://input-bucket/input-prefix/",
            "InputFormat": "ONE_DOC_PER_FILE",
        },
        OutputDataConfig={"S3Uri": "s3://output-bucket/output-prefix/"},
        Tags=[{"Key": "jobkey", "Value": "jobvalue"}],
    )["JobId"]

    resource_groups_client = boto3.client(
        "resourcegroupstaggingapi", region_name="ap-southeast-1"
    )

    tags = resource_groups_client.get_resources(
        TagFilters=[{"Key": "k1", "Values": ["v1"]}],
    )["ResourceTagMappingList"]

    assert tags == [
        {
            "ResourceARN": arn,
            "Tags": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
        }
    ]

    tags = resource_groups_client.get_resources(
        ResourceTypeFilters=["comprehend:document-classification-job"],
    )["ResourceTagMappingList"]

    assert len(tags) == 1
    assert tags == [
        {
            "ResourceARN": f"arn:aws:comprehend:ap-southeast-1:123456789012:document-classification-job/{job_id}",
            "Tags": [{"Key": "jobkey", "Value": "jobvalue"}],
        }
    ]


@mock_aws
def test_tags_from_resourcegroupsapi_no_arn():
    resource_groups_client = boto3.client(
        "resourcegroupstaggingapi", region_name="ap-southeast-1"
    )
    account_id = "123456789012"

    backend = comprehend_backends[account_id]["ap-southeast-1"]

    class DummyResource:
        pass

    backend.jobs["fake-job"] = DummyResource()

    result = resource_groups_client.get_resources(
        ResourceTypeFilters=["comprehend:document-classification-job"]
    )["ResourceTagMappingList"]

    assert result == []
