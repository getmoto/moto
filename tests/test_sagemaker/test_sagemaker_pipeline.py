from moto import mock_sagemaker
from time import sleep
from datetime import datetime
import boto3
import botocore
import pytest

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

FAKE_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
TEST_REGION_NAME = "us-east-1"


def arn_formatter(_type, _id, account_id, region_name):
    return f"arn:aws:sagemaker:{region_name}:{account_id}:{_type}/{_id}"


@pytest.fixture(name="sagemaker_client")
def fixture_sagemaker_client():
    with mock_sagemaker():
        yield boto3.client("sagemaker", region_name=TEST_REGION_NAME)


def create_sagemaker_pipelines(sagemaker_client, pipeline_names, wait_seconds=0.0):
    responses = []
    for pipeline_name in pipeline_names:
        responses += sagemaker_client.create_pipeline(
            PipelineName=pipeline_name,
            RoleArn=FAKE_ROLE_ARN,
        )
        sleep(wait_seconds)
    return responses


def test_create_pipeline(sagemaker_client):
    fake_pipeline_name = "MyPipelineName"
    response = sagemaker_client.create_pipeline(
        PipelineName=fake_pipeline_name,
        RoleArn=FAKE_ROLE_ARN,
    )
    assert isinstance(response, dict)
    response["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_none(sagemaker_client):
    response = sagemaker_client.list_pipelines()
    assert isinstance(response, dict)
    assert response["PipelineSummaries"].should.be.empty


def test_list_pipelines_single(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names)
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"].should.have.length_of(1)
    response["PipelineSummaries"][0]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[0], ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_multiple(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName"]
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names)
    response = sagemaker_client.list_pipelines(
        SortBy="Name",
        SortOrder="Ascending",
    )
    response["PipelineSummaries"].should.have.length_of(len(fake_pipeline_names))


def test_list_pipelines_sort_name_ascending(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names)
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
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 1)
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
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 0.0)
    response = sagemaker_client.list_pipelines(MaxResults=2)
    response["PipelineSummaries"].should.have.length_of(2)


def test_list_pipelines_next_token(sagemaker_client):
    fake_pipeline_names = ["APipelineName"]
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 0.0)

    response = sagemaker_client.list_pipelines(NextToken="0")
    response["PipelineSummaries"].should.have.length_of(1)


def test_list_pipelines_pipeline_name_prefix(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 0.0)
    response = sagemaker_client.list_pipelines(PipelineNamePrefix="APipe")
    response["PipelineSummaries"].should.have.length_of(1)
    response["PipelineSummaries"][0]["PipelineName"].should.equal("APipelineName")

    response = sagemaker_client.list_pipelines(PipelineNamePrefix="Pipeline")
    response["PipelineSummaries"].should.have.length_of(3)


def test_list_pipelines_created_after(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 0.0)

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
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 0.0)

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
    _ = create_sagemaker_pipelines(sagemaker_client, fake_pipeline_names, 0.0)
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
    assert pipeline_names_remain == pipeline_names_exist


def test_delete_pipeline_not_exists(sagemaker_client):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.delete_pipeline(PipelineName="some-pipeline-name")


def test_update_pipeline(sagemaker_client):
    with pytest.raises(botocore.exceptions.ClientError):
        _ = sagemaker_client.update_pipeline(PipelineName="some-pipeline-name")


def test_update_pipeline_no_update(sagemaker_client):
    pipeline_name = "APipelineName"
    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline_name])
    response = sagemaker_client.update_pipeline(PipelineName=pipeline_name)
    response["PipelineArn"].should.equal(
        arn_formatter("pipeline", pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["PipelineName"].should.equal(pipeline_name)


def test_update_pipeline_add_attribute(sagemaker_client):
    pipeline_name = "APipelineName"
    pipeline_display_name_update = "APipelineDisplayName"

    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline_name])
    response = sagemaker_client.list_pipelines()
    assert "PipelineDisplayName" not in response["PipelineSummaries"][0]

    _ = sagemaker_client.update_pipeline(
        PipelineName=pipeline_name,
        PipelineDisplayName=pipeline_display_name_update,
    )
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["PipelineDisplayName"].should.equal(
        pipeline_display_name_update
    )
    response["PipelineSummaries"][0].should.have.length_of(7)


def test_update_pipeline_update_change_attribute(sagemaker_client):
    pipeline_name = "APipelineName"
    role_arn_update = f"{FAKE_ROLE_ARN}Test"

    _ = create_sagemaker_pipelines(sagemaker_client, [pipeline_name])
    _ = sagemaker_client.update_pipeline(
        PipelineName=pipeline_name,
        RoleArn=role_arn_update,
    )
    response = sagemaker_client.list_pipelines()
    response["PipelineSummaries"][0]["RoleArn"].should.equal(role_arn_update)
    response["PipelineSummaries"][0].should.have.length_of(6)
