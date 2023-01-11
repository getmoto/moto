from contextlib import contextmanager
from moto import mock_sagemaker, settings
from time import sleep
from datetime import datetime
import boto3
import botocore
import json
import pytest
from unittest import SkipTest

from moto.s3 import mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.sagemaker.utils import arn_formatter, load_pipeline_definition_from_s3

FAKE_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
TEST_REGION_NAME = "us-west-1"


@contextmanager
def setup_s3_pipeline_definition(bucket_name, object_key, pipeline_definition):
    client = boto3.client("s3")
    client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": TEST_REGION_NAME},
    )
    client.put_object(
        Body=json.dumps(pipeline_definition),
        Bucket=bucket_name,
        Key=object_key,
    )
    yield

    client.delete_object(Bucket=bucket_name, Key=object_key)
    client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(name="sagemaker_client")
def fixture_sagemaker_client():
    with mock_sagemaker():
        yield boto3.client("sagemaker", region_name=TEST_REGION_NAME)


def create_sagemaker_pipelines(sagemaker_client, pipelines, wait_seconds=0.0):
    responses = []
    for pipeline in pipelines:
        responses += sagemaker_client.create_pipeline(**pipeline)
        sleep(wait_seconds)
    return responses


def test_load_pipeline_definition_from_s3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Skipping test in server mode due to lack of access to s3_backend."
        )

    bucket_name = "some-bucket-1"
    object_key = "some/object/key.json"
    pipeline_definition = {"key": "value"}

    with mock_s3():
        with setup_s3_pipeline_definition(
            bucket_name,
            object_key,
            pipeline_definition,
        ):
            observed_pipeline_definition = load_pipeline_definition_from_s3(
                pipeline_definition_s3_location={
                    "Bucket": bucket_name,
                    "ObjectKey": object_key,
                },
                account_id=ACCOUNT_ID,
            )
    observed_pipeline_definition.should.equal(pipeline_definition)


def test_create_pipeline(sagemaker_client):
    fake_pipeline_name = "MyPipelineName"
    response = sagemaker_client.create_pipeline(
        PipelineName=fake_pipeline_name,
        RoleArn=FAKE_ROLE_ARN,
        PipelineDefinition=" ",
    )
    assert isinstance(response, dict)
    response["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )


@pytest.mark.parametrize(
    "create_pipeline_kwargs",
    [
        {"PipelineName": "MyPipelineName", "RoleArn": FAKE_ROLE_ARN},
        {"RoleArn": FAKE_ROLE_ARN, "PipelineDefinition": " "},
        {"PipelineName": "MyPipelineName", "PipelineDefinition": " "},
        {
            "PipelineName": "MyPipelineName",
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
            "PipelineDefinitionS3Location": {"key": "value"},
        },
    ],
)
def test_create_pipeline_invalid_required_kwargs(
    sagemaker_client, create_pipeline_kwargs
):
    with pytest.raises(
        (
            botocore.exceptions.ParamValidationError,
            botocore.exceptions.ClientError,
        )
    ):
        _ = sagemaker_client.create_pipeline(
            **create_pipeline_kwargs,
        )


def test_create_pipeline_duplicate_pipeline_name(sagemaker_client):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.create_pipeline(
            PipelineName="APipelineName",
            RoleArn=FAKE_ROLE_ARN,
            PipelineDefinition=" ",
        )
        _ = sagemaker_client.create_pipeline(
            PipelineName="APipelineName",
            RoleArn=FAKE_ROLE_ARN,
            PipelineDefinition=" ",
        )


def test_list_pipelines_none(sagemaker_client):
    response = sagemaker_client.list_pipelines()
    assert isinstance(response, dict)
    assert response["PipelineSummaries"].should.be.empty


def test_list_pipelines_single(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"].should.have.length_of(1)
    response["PipelineSummaries"][0]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[0], ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_multiple(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    response = sagemaker_client.list_pipelines(
        SortBy="Name",
        SortOrder="Ascending",
    )
    response["PipelineSummaries"].should.have.length_of(len(fake_pipeline_names))


def test_list_pipelines_sort_name_ascending(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    response = sagemaker_client.list_pipelines(
        SortBy="Name",
        SortOrder="Ascending",
    )
    response["PipelineSummaries"][0]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[0], ACCOUNT_ID, TEST_REGION_NAME)
    )
    response["PipelineSummaries"][-1]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[-1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    response["PipelineSummaries"][1]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[1], ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_sort_creation_time_descending(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines, 1.0)

    response = sagemaker_client.list_pipelines(
        SortBy="CreationTime",
        SortOrder="Descending",
    )
    response["PipelineSummaries"][0]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[-1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    response["PipelineSummaries"][1]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    response["PipelineSummaries"][2]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[0], ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_max_results(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    response = sagemaker_client.list_pipelines(MaxResults=2)
    response["PipelineSummaries"].should.have.length_of(2)


def test_list_pipelines_next_token(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    response = sagemaker_client.list_pipelines(NextToken="0")
    response["PipelineSummaries"].should.have.length_of(1)


def test_list_pipelines_pipeline_name_prefix(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    response = sagemaker_client.list_pipelines(PipelineNamePrefix="APipe")
    response["PipelineSummaries"].should.have.length_of(1)
    response["PipelineSummaries"][0]["PipelineName"].should.equal("APipelineName")

    response = sagemaker_client.list_pipelines(PipelineNamePrefix="Pipeline")
    response["PipelineSummaries"].should.have.length_of(3)


def test_list_pipelines_created_after(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    created_after_str = "2099-12-31 23:59:59"
    response = sagemaker_client.list_pipelines(CreatedAfter=created_after_str)
    assert response["PipelineSummaries"].should.be.empty

    created_after_datetime = datetime.strptime(created_after_str, "%Y-%m-%d %H:%M:%S")
    response = sagemaker_client.list_pipelines(CreatedAfter=created_after_datetime)
    assert response["PipelineSummaries"].should.be.empty

    created_after_timestamp = datetime.timestamp(created_after_datetime)
    response = sagemaker_client.list_pipelines(CreatedAfter=created_after_timestamp)
    assert response["PipelineSummaries"].should.be.empty


def test_list_pipelines_created_before(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)

    created_before_str = "2000-12-31 23:59:59"
    response = sagemaker_client.list_pipelines(CreatedBefore=created_before_str)
    assert response["PipelineSummaries"].should.be.empty

    created_before_datetime = datetime.strptime(created_before_str, "%Y-%m-%d %H:%M:%S")
    response = sagemaker_client.list_pipelines(CreatedBefore=created_before_datetime)
    assert response["PipelineSummaries"].should.be.empty

    created_before_timestamp = datetime.timestamp(created_before_datetime)
    response = sagemaker_client.list_pipelines(CreatedBefore=created_before_timestamp)
    assert response["PipelineSummaries"].should.be.empty


@pytest.mark.parametrize(
    "list_pipelines_kwargs",
    [
        {"MaxResults": 200},
        {"NextToken": "some-invalid-next-token"},
        {"SortOrder": "some-invalid-sort-order"},
        {"SortBy": "some-invalid-sort-by"},
    ],
)
def test_list_pipelines_invalid_values(sagemaker_client, list_pipelines_kwargs):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.list_pipelines(**list_pipelines_kwargs)


def test_delete_pipeline_exists(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_name,
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        }
        for fake_pipeline_name in fake_pipeline_names
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)
    pipeline_name_delete, pipeline_names_remain = (
        fake_pipeline_names[0],
        fake_pipeline_names[1:],
    )

    response = sagemaker_client.delete_pipeline(PipelineName=pipeline_name_delete)
    assert response["PipelineArn"].endswith(pipeline_name_delete)

    response = sagemaker_client.list_pipelines(PipelineNamePrefix=pipeline_name_delete)
    assert response["PipelineSummaries"].should.be.empty

    response = sagemaker_client.list_pipelines()
    pipeline_names_exist = [
        pipeline["PipelineName"] for pipeline in response["PipelineSummaries"]
    ]
    assert set(pipeline_names_remain) == set(pipeline_names_exist)


def test_delete_pipeline_not_exists(sagemaker_client):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.delete_pipeline(PipelineName="some-pipeline-name")


def test_update_pipeline_not_exists(sagemaker_client):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.update_pipeline(PipelineName="some-pipeline-name")


def test_update_pipeline_invalid_kwargs(sagemaker_client):
    pipeline_name = "APipelineName"
    pipeline = {
        "PipelineName": pipeline_name,
        "RoleArn": FAKE_ROLE_ARN,
        "PipelineDefinition": " ",
    }
    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline])

    with pytest.raises(botocore.exceptions.ParamValidationError):
        sagemaker_client.update_pipeline(
            PipelineName=pipeline_name,
            **{"InvalidKwarg": "some-value"},
        )


def test_update_pipeline_no_update(sagemaker_client):
    pipeline_name = "APipelineName"
    pipeline = {
        "PipelineName": pipeline_name,
        "RoleArn": FAKE_ROLE_ARN,
        "PipelineDefinition": " ",
    }
    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline])

    response = sagemaker_client.update_pipeline(PipelineName=pipeline_name)
    response["PipelineArn"].should.equal(
        arn_formatter("pipeline", pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["PipelineName"].should.equal(pipeline_name)


def test_update_pipeline_add_attribute(sagemaker_client):
    pipeline_name = "APipelineName"
    pipeline_display_name_update = "APipelineDisplayName"

    pipeline = {
        "PipelineName": pipeline_name,
        "RoleArn": FAKE_ROLE_ARN,
        "PipelineDefinition": " ",
    }
    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline])
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["PipelineDisplayName"].should.equal(pipeline_name)

    _ = sagemaker_client.update_pipeline(
        PipelineName=pipeline_name,
        PipelineDisplayName=pipeline_display_name_update,
    )
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["PipelineDisplayName"].should.equal(
        pipeline_display_name_update
    )
    response["PipelineSummaries"][0].should.have.length_of(6)


def test_update_pipeline_update_change_attribute(sagemaker_client):
    pipeline_name = "APipelineName"
    role_arn_update = f"{FAKE_ROLE_ARN}Test"
    pipeline = {
        "PipelineName": pipeline_name,
        "RoleArn": FAKE_ROLE_ARN,
        "PipelineDefinition": " ",
    }
    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline])

    _ = sagemaker_client.update_pipeline(
        PipelineName=pipeline_name,
        RoleArn=role_arn_update,
    )
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["RoleArn"].should.equal(role_arn_update)
    response["PipelineSummaries"][0].should.have.length_of(6)


def test_describe_pipeline_not_exists(sagemaker_client):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.describe_pipeline(PipelineName="some-pipeline-name")


@pytest.mark.parametrize(
    "pipeline,expected_response_length",
    [
        (
            {
                "PipelineName": "APipelineName",
                "RoleArn": FAKE_ROLE_ARN,
                "PipelineDefinition": " ",
            },
            11,
        ),
        (
            {
                "PipelineName": "BPipelineName",
                "RoleArn": FAKE_ROLE_ARN,
                "PipelineDefinition": " ",
                "PipelineDescription": "some pipeline description",
            },
            12,
        ),
    ],
)
def test_describe_pipeline_exists(sagemaker_client, pipeline, expected_response_length):
    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline])
    response = sagemaker_client.describe_pipeline(PipelineName=pipeline["PipelineName"])
    response.should.have.length_of(expected_response_length)
