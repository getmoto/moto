from contextlib import contextmanager
from datetime import datetime
import json
from time import sleep
from unittest import SkipTest

import boto3
import botocore
import pytest

from moto import mock_sagemaker, settings
from moto.s3 import mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.sagemaker.exceptions import ValidationError
from moto.sagemaker.utils import (
    get_pipeline_from_name,
    get_pipeline_execution_from_arn,
    get_pipeline_name_from_execution_arn,
)
from moto.sagemaker.models import FakePipeline, sagemaker_backends
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


def test_utils_get_pipeline_from_name_exists():
    fake_pipeline_names = ["APipelineName", "BPipelineName"]
    pipelines = {
        fake_pipeline_name: FakePipeline(
            pipeline_name="BFakePipeline",
            pipeline_display_name="BFakePipeline",
            pipeline_description=" ",
            tags=[],
            parallelism_configuration={},
            pipeline_definition=" ",
            role_arn=FAKE_ROLE_ARN,
            account_id=ACCOUNT_ID,
            region_name=TEST_REGION_NAME,
        )
        for fake_pipeline_name in fake_pipeline_names
    }
    retrieved_pipeline = get_pipeline_from_name(
        pipelines=pipelines, pipeline_name=fake_pipeline_names[0]
    )
    assert retrieved_pipeline == pipelines[fake_pipeline_names[0]]


def test_utils_get_pipeline_from_name_not_exists():
    with pytest.raises(ValidationError):
        _ = get_pipeline_from_name(pipelines={}, pipeline_name="foo")


def test_utils_get_pipeline_name_from_execution_arn():
    expected_pipeline_name = "some-pipeline-name"
    pipeline_execution_arn = (
        f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}"
        f":pipeline/{expected_pipeline_name}/execution/abc123def456"
    )
    observed_pipeline_name = get_pipeline_name_from_execution_arn(
        pipeline_execution_arn=pipeline_execution_arn
    )
    assert expected_pipeline_name == observed_pipeline_name


def test_utils_get_pipeline_execution_from_arn_not_exists():
    with pytest.raises(ValidationError):
        _ = get_pipeline_execution_from_arn(
            pipelines={},
            pipeline_execution_arn="some/random/non/existent/arn",
        )


def test_utils_arn_formatter():
    expected_arn = (
        f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:pipeline/some-pipeline-name"
    )
    observed_arn = arn_formatter(
        _type="pipeline",
        _id="some-pipeline-name",
        region_name=TEST_REGION_NAME,
        account_id=ACCOUNT_ID,
    )
    assert expected_arn == observed_arn


def test_list_pipeline_executions(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)
    _ = sagemaker_client.start_pipeline_execution(PipelineName=fake_pipeline_names[0])
    _ = sagemaker_client.start_pipeline_execution(PipelineName=fake_pipeline_names[0])
    response = sagemaker_client.list_pipeline_executions(
        PipelineName=fake_pipeline_names[0]
    )
    assert len(response["PipelineExecutionSummaries"]) == 2
    assert (
        fake_pipeline_names[0]
        in response["PipelineExecutionSummaries"][0]["PipelineExecutionArn"]
    )


def test_describe_pipeline_definition_for_execution(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    pipeline_definition = "some-pipeline-definition"
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": pipeline_definition,
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)
    response = sagemaker_client.start_pipeline_execution(
        PipelineName=fake_pipeline_names[0]
    )
    pipeline_execution_arn = response["PipelineExecutionArn"]
    response = sagemaker_client.describe_pipeline_definition_for_execution(
        PipelineExecutionArn=pipeline_execution_arn
    )
    assert set(response.keys()) == {
        "PipelineDefinition",
        "CreationTime",
        "ResponseMetadata",
    }
    assert response["PipelineDefinition"] == pipeline_definition


def test_list_pipeline_parameters_for_execution(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)
    pipeline_execution_arn = sagemaker_client.start_pipeline_execution(
        PipelineName=fake_pipeline_names[0],
        PipelineParameters=[
            {"Name": "foo", "Value": "bar"},
        ],
    )["PipelineExecutionArn"]

    response = sagemaker_client.list_pipeline_parameters_for_execution(
        PipelineExecutionArn=pipeline_execution_arn
    )
    assert isinstance(response["PipelineParameters"], list)
    assert len(response["PipelineParameters"]) == 1
    assert response["PipelineParameters"][0]["Name"] == "foo"
    assert response["PipelineParameters"][0]["Value"] == "bar"


def test_start_pipeline_execution(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)
    pipeline_execution_arn = sagemaker_client.start_pipeline_execution(
        PipelineName=fake_pipeline_names[0]
    )
    assert fake_pipeline_names[0] in pipeline_execution_arn["PipelineExecutionArn"]


def test_start_pipeline_execution_contains_client_request_token(sagemaker_client):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Skipping test in server mode due to lack of access to sagemaker_backends."
        )

    fake_pipeline_names = ["APipelineName"]
    pipelines = [
        {
            "PipelineName": fake_pipeline_names[0],
            "RoleArn": FAKE_ROLE_ARN,
            "PipelineDefinition": " ",
        },
    ]
    _ = create_sagemaker_pipelines(sagemaker_client, pipelines)
    pipeline_execution_arn = sagemaker_client.start_pipeline_execution(
        PipelineName=fake_pipeline_names[0]
    )["PipelineExecutionArn"]

    # Verify that client_request_token is stored in FakePipelineExecution object
    assert (
        sagemaker_backends[ACCOUNT_ID][TEST_REGION_NAME]
        .pipelines[fake_pipeline_names[0]]
        .pipeline_executions[pipeline_execution_arn]
        .client_request_token
        != ""
    )


def test_describe_pipeline_execution_not_exists(sagemaker_client):
    pipeline_execution_arn = arn_formatter(
        # random ID (execution ID)
        "pipeline-execution",
        "some-pipeline-name",
        ACCOUNT_ID,
        TEST_REGION_NAME,
    )
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.describe_pipeline_execution(
            PipelineExecutionArn=pipeline_execution_arn
        )


def test_describe_pipeline_execution(sagemaker_client):
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
    response = sagemaker_client.start_pipeline_execution(
        PipelineName=fake_pipeline_names[0]
    )
    _ = sagemaker_client.start_pipeline_execution(PipelineName=fake_pipeline_names[1])
    expected_pipeline_execution_arn = response["PipelineExecutionArn"]
    pipeline_execution_summary = sagemaker_client.describe_pipeline_execution(
        PipelineExecutionArn=response["PipelineExecutionArn"]
    )
    observed_pipeline_execution_arn = pipeline_execution_summary["PipelineExecutionArn"]
    assert observed_pipeline_execution_arn == expected_pipeline_execution_arn


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
    assert observed_pipeline_definition == pipeline_definition


def test_create_pipeline(sagemaker_client):
    fake_pipeline_name = "MyPipelineName"
    response = sagemaker_client.create_pipeline(
        PipelineName=fake_pipeline_name,
        RoleArn=FAKE_ROLE_ARN,
        PipelineDefinition=" ",
    )
    assert isinstance(response, dict)
    assert response["PipelineArn"] == (
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
    assert not response["PipelineSummaries"]


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
    assert len(response["PipelineSummaries"]) == 1
    assert response["PipelineSummaries"][0]["PipelineArn"] == (
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
    assert len(response["PipelineSummaries"]) == len(fake_pipeline_names)


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
    assert response["PipelineSummaries"][0]["PipelineArn"] == (
        arn_formatter("pipeline", fake_pipeline_names[0], ACCOUNT_ID, TEST_REGION_NAME)
    )
    assert response["PipelineSummaries"][-1]["PipelineArn"] == (
        arn_formatter("pipeline", fake_pipeline_names[-1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    assert response["PipelineSummaries"][1]["PipelineArn"] == (
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
    assert response["PipelineSummaries"][0]["PipelineArn"] == (
        arn_formatter("pipeline", fake_pipeline_names[-1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    assert response["PipelineSummaries"][1]["PipelineArn"] == (
        arn_formatter("pipeline", fake_pipeline_names[1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    assert response["PipelineSummaries"][2]["PipelineArn"] == (
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
    assert len(response["PipelineSummaries"]) == 2


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
    assert len(response["PipelineSummaries"]) == 1


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
    assert len(response["PipelineSummaries"]) == 1
    assert response["PipelineSummaries"][0]["PipelineName"] == "APipelineName"

    response = sagemaker_client.list_pipelines(PipelineNamePrefix="Pipeline")
    assert len(response["PipelineSummaries"]) == 3


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
    assert not response["PipelineSummaries"]

    created_after_datetime = datetime.strptime(created_after_str, "%Y-%m-%d %H:%M:%S")
    response = sagemaker_client.list_pipelines(CreatedAfter=created_after_datetime)
    assert not response["PipelineSummaries"]

    created_after_timestamp = datetime.timestamp(created_after_datetime)
    response = sagemaker_client.list_pipelines(CreatedAfter=created_after_timestamp)
    assert not response["PipelineSummaries"]


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
    assert not response["PipelineSummaries"]

    created_before_datetime = datetime.strptime(created_before_str, "%Y-%m-%d %H:%M:%S")
    response = sagemaker_client.list_pipelines(CreatedBefore=created_before_datetime)
    assert not response["PipelineSummaries"]

    created_before_timestamp = datetime.timestamp(created_before_datetime)
    response = sagemaker_client.list_pipelines(CreatedBefore=created_before_timestamp)
    assert not response["PipelineSummaries"]


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
    assert not response["PipelineSummaries"]

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
    assert response["PipelineArn"] == (
        arn_formatter("pipeline", pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )
    response = sagemaker_client.list_pipelines()
    assert response["PipelineSummaries"][0]["PipelineName"] == pipeline_name


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
    assert response["PipelineSummaries"][0]["PipelineDisplayName"] == pipeline_name

    _ = sagemaker_client.update_pipeline(
        PipelineName=pipeline_name,
        PipelineDisplayName=pipeline_display_name_update,
    )
    response = sagemaker_client.list_pipelines()
    assert response["PipelineSummaries"][0]["PipelineDisplayName"] == (
        pipeline_display_name_update
    )
    assert len(response["PipelineSummaries"][0]) == 6


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
    assert response["PipelineSummaries"][0]["RoleArn"] == role_arn_update
    assert len(response["PipelineSummaries"][0]) == 6


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
    assert len(response) == expected_response_length
