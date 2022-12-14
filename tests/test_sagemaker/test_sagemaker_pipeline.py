from moto import mock_sagemaker
import boto3
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


def test_create_pipeline(sagemaker_client):
    fake_pipeline_name = "MyPipelineName"
    response = sagemaker_client.create_pipeline(
        PipelineName=fake_pipeline_name,
        RoleArn=FAKE_ROLE_ARN,
    )
    assert isinstance(response, dict)
    assert response["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_none(sagemaker_client):
    response = sagemaker_client.list_pipelines()
    assert isinstance(response, dict)
    assert response["PipelineSummaries"].should.be.empty


def test_list_pipelines_single(sagemaker_client):
    fake_pipeline_name = "APipelineName"
    _ = sagemaker_client.create_pipeline(
        PipelineName=fake_pipeline_name,
        RoleArn=FAKE_ROLE_ARN,
    )
    response = sagemaker_client.list_pipelines()
    assert response["PipelineSummaries"].should.have.length_of(1)
    assert response["PipelineSummaries"][0]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_name, ACCOUNT_ID, TEST_REGION_NAME)
    )


def test_list_pipelines_multiple(sagemaker_client):
    fake_pipeline_names = ["APipelineName", "BPipelineName", "CPipelineName"]
    for fake_pipeline_name in fake_pipeline_names:
        _ = sagemaker_client.create_pipeline(
            PipelineName=f"{fake_pipeline_name}",
            RoleArn=FAKE_ROLE_ARN,
        )
    response = sagemaker_client.list_pipelines(
        SortBy="Name",
        SortOrder="Ascending",
    )
    assert response["PipelineSummaries"].should.have.length_of(len(fake_pipeline_names))
    assert response["PipelineSummaries"][0]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[0], ACCOUNT_ID, TEST_REGION_NAME)
    )
    assert response["PipelineSummaries"][-1]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[-1], ACCOUNT_ID, TEST_REGION_NAME)
    )
    assert response["PipelineSummaries"][1]["PipelineArn"].should.equal(
        arn_formatter("pipeline", fake_pipeline_names[1], ACCOUNT_ID, TEST_REGION_NAME)
    )
