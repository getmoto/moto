import boto3

from moto import mock_aws
from moto.comprehend.models import comprehend_backends
from tests.test_comprehend.test_comprehend import (
    DOCUMENT_CLASSIFIER_INPUT_DATA_CONFIG,
    INPUT_DATA_CONFIG,
)

REGION = "ap-southeast-1"


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


def _assert_rgtapi_tag_untag(arn, resource_type):
    """Exercise get_resources + tag_resources + untag_resources for a single ARN."""
    rtapi = boto3.client("resourcegroupstaggingapi", region_name=REGION)

    # GetResources returns the resource
    resp = rtapi.get_resources(ResourceTypeFilters=[resource_type])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi.tag_resources(ResourceARNList=[arn], Tags={"Test2": "2"})
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(
        ResourceTypeFilters=[resource_type],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi.untag_resources(ResourceARNList=[arn], TagKeys=["Test"])
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi.get_resources(ResourceTypeFilters=[resource_type])
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test2", "Value": "2"}]


@mock_aws
def test_rgtapi_entity_recognizer():
    client = boto3.client("comprehend", region_name=REGION)
    arn = client.create_entity_recognizer(
        RecognizerName="test-recognizer",
        VersionName="v1",
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        Tags=[{"Key": "Test", "Value": "1"}],
    )["EntityRecognizerArn"]

    _assert_rgtapi_tag_untag(arn, "comprehend:entity-recognizer")


@mock_aws
def test_rgtapi_endpoint():
    client = boto3.client("comprehend", region_name=REGION)
    model_arn = (
        f"arn:aws:comprehend:{REGION}:123456789012:document-classifier/test-classifier"
    )
    arn = client.create_endpoint(
        EndpointName="test-endpoint",
        ModelArn=model_arn,
        DesiredInferenceUnits=1,
        Tags=[{"Key": "Test", "Value": "1"}],
    )["EndpointArn"]

    _assert_rgtapi_tag_untag(arn, "comprehend:endpoint")


@mock_aws
def test_rgtapi_flywheel():
    client = boto3.client("comprehend", region_name=REGION)
    model_arn = (
        f"arn:aws:comprehend:{REGION}:123456789012:document-classifier/test-classifier"
    )
    arn = client.create_flywheel(
        FlywheelName="test-flywheel",
        ActiveModelArn=model_arn,
        DataAccessRoleArn="iam_role_with_20_chars",
        TaskConfig={
            "LanguageCode": "en",
            "DocumentClassificationConfig": {
                "Mode": "MULTI_CLASS",
                "Labels": ["Label1", "Label2"],
            },
        },
        ModelType="DOCUMENT_CLASSIFIER",
        DataLakeS3Uri=f"s3://{REGION}-bucket/documents.txt",
        Tags=[{"Key": "Test", "Value": "1"}],
    )["FlywheelArn"]

    _assert_rgtapi_tag_untag(arn, "comprehend:flywheel")
