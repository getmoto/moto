"""Unit tests for pipes-supported APIs."""

import boto3
import pytest
from botocore.client import Config
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_pipe():
    client = boto3.client("pipes", region_name="eu-west-1")
    resp = client.create_pipe(
        Name="test-pipe",
        Source="arn:aws:sqs:eu-west-1:123456789012:test-queue",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
    )

    assert resp["Arn"].startswith("arn:aws:pipes:eu-west-1:")
    assert resp["Name"] == "test-pipe"
    assert resp["DesiredState"] == "RUNNING"
    assert resp["CurrentState"] == "RUNNING"


@mock_aws
def test_create_pipe_with_optional_parameters():
    client = boto3.client("pipes", region_name="us-east-1")
    resp = client.create_pipe(
        Name="test-pipe-optional",
        Source="arn:aws:sqs:us-east-1:123456789012:test-queue",
        Target="arn:aws:lambda:us-east-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
        Description="Test pipe description",
        DesiredState="STOPPED",
        SourceParameters={"FilterCriteria": {"Filters": []}},
        Enrichment="arn:aws:lambda:us-east-1:123456789012:function:enrichment",
        TargetParameters={"InputTemplate": '{"key": "<$.key>"}'},
        Tags={"Environment": "test", "Project": "moto"},
    )

    assert resp["Name"] == "test-pipe-optional"
    assert resp["DesiredState"] == "STOPPED"
    assert resp["CurrentState"] == "RUNNING"


@mock_aws
def test_describe_pipe():
    client = boto3.client("pipes", region_name="us-east-2")

    create_resp = client.create_pipe(
        Name="test-pipe",
        Source="arn:aws:sqs:us-east-2:123456789012:test-queue",
        Target="arn:aws:lambda:us-east-2:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
        Description="Test description",
    )

    resp = client.describe_pipe(Name="test-pipe")

    assert resp["Arn"] == create_resp["Arn"]
    assert resp["Name"] == "test-pipe"
    assert resp["Description"] == "Test description"
    assert resp["Source"] == "arn:aws:sqs:us-east-2:123456789012:test-queue"
    assert (
        resp["Target"] == "arn:aws:lambda:us-east-2:123456789012:function:test-function"
    )
    assert resp["RoleArn"] == "arn:aws:iam::123456789012:role/test-role"
    assert resp["DesiredState"] == "RUNNING"
    assert resp["CurrentState"] == "RUNNING"


@mock_aws
def test_delete_pipe():
    client = boto3.client("pipes", region_name="us-east-1")

    create_resp = client.create_pipe(
        Name="test-pipe-delete",
        Source="arn:aws:sqs:us-east-1:123456789012:test-queue",
        Target="arn:aws:lambda:us-east-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
    )

    delete_resp = client.delete_pipe(Name="test-pipe-delete")

    assert delete_resp["Arn"] == create_resp["Arn"]
    assert delete_resp["Name"] == "test-pipe-delete"
    assert delete_resp["DesiredState"] == "DELETED"
    assert delete_resp["CurrentState"] == "DELETING"


@mock_aws
def test_tag_resource():
    client = boto3.client("pipes", region_name="eu-west-1")

    create_resp = client.create_pipe(
        Name="test-pipe-tag",
        Source="arn:aws:sqs:eu-west-1:123456789012:test-queue",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
    )

    tag_resp = client.tag_resource(
        resourceArn=create_resp["Arn"],
        tags={"Environment": "test", "Project": "moto", "Team": "backend"},
    )

    assert {k: v for k, v in tag_resp.items() if k != "ResponseMetadata"} == {}

    describe_resp = client.describe_pipe(Name="test-pipe-tag")
    assert describe_resp["Tags"] == {
        "Environment": "test",
        "Project": "moto",
        "Team": "backend",
    }


@mock_aws
def test_tag_resource_updates_existing_tags():
    client = boto3.client("pipes", region_name="eu-west-1")

    create_resp = client.create_pipe(
        Name="test-pipe-tag-update",
        Source="arn:aws:sqs:eu-west-1:123456789012:test-queue",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
        Tags={"Environment": "dev", "Project": "old-project"},
    )

    client.tag_resource(
        resourceArn=create_resp["Arn"],
        tags={"Environment": "prod", "Team": "backend"},
    )

    describe_resp = client.describe_pipe(Name="test-pipe-tag-update")
    assert describe_resp["Tags"] == {
        "Environment": "prod",
        "Project": "old-project",
        "Team": "backend",
    }


@mock_aws
def test_untag_resource():
    client = boto3.client("pipes", region_name="eu-west-1")

    create_resp = client.create_pipe(
        Name="test-pipe-untag",
        Source="arn:aws:sqs:eu-west-1:123456789012:test-queue",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
        Tags={"Environment": "test", "Project": "moto", "Team": "backend"},
    )

    untag_resp = client.untag_resource(
        resourceArn=create_resp["Arn"],
        tagKeys=["Environment", "Team"],
    )

    assert {k: v for k, v in untag_resp.items() if k != "ResponseMetadata"} == {}

    describe_resp = client.describe_pipe(Name="test-pipe-untag")
    assert describe_resp["Tags"] == {"Project": "moto"}


@mock_aws
def test_untag_resource_all_tags():
    client = boto3.client("pipes", region_name="eu-west-1")

    create_resp = client.create_pipe(
        Name="test-pipe-untag-all",
        Source="arn:aws:sqs:eu-west-1:123456789012:test-queue",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:test-function",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
        Tags={"Environment": "test", "Project": "moto"},
    )

    client.untag_resource(
        resourceArn=create_resp["Arn"],
        tagKeys=["Environment", "Project"],
    )

    describe_resp = client.describe_pipe(Name="test-pipe-untag-all")
    assert describe_resp.get("Tags") is None or describe_resp["Tags"] == {}


@mock_aws
def test_list_pipes():
    client = boto3.client("pipes", region_name="eu-west-1")

    pipe1 = client.create_pipe(
        Name="test-pipe-1",
        Source="arn:aws:sqs:eu-west-1:123456789012:queue-1",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:func-1",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
    )
    client.create_pipe(
        Name="test-pipe-2",
        Source="arn:aws:sqs:eu-west-1:123456789012:queue-2",
        Target="arn:aws:lambda:eu-west-1:123456789012:function:func-2",
        RoleArn="arn:aws:iam::123456789012:role/test-role",
    )

    resp = client.list_pipes()

    assert "Pipes" in resp
    assert len(resp["Pipes"]) == 2
    pipe_names = [p["Name"] for p in resp["Pipes"]]
    assert "test-pipe-1" in pipe_names
    assert "test-pipe-2" in pipe_names

    pipe = next(p for p in resp["Pipes"] if p["Name"] == "test-pipe-1")
    assert pipe["Arn"] == pipe1["Arn"]
    assert pipe["Name"] == "test-pipe-1"
    assert pipe["DesiredState"] == "RUNNING"
    assert pipe["CurrentState"] == "RUNNING"
    assert pipe["Source"] == "arn:aws:sqs:eu-west-1:123456789012:queue-1"
    assert pipe["Target"] == "arn:aws:lambda:eu-west-1:123456789012:function:func-1"


@mock_aws
def test_list_pipes_with_pagination():
    client = boto3.client("pipes", region_name="eu-west-1")

    for i in range(5):
        client.create_pipe(
            Name=f"pipe-{i}",
            Source=f"arn:aws:sqs:eu-west-1:123456789012:queue-{i}",
            Target=f"arn:aws:lambda:eu-west-1:123456789012:function:func-{i}",
            RoleArn="arn:aws:iam::123456789012:role/test-role",
        )

    resp = client.list_pipes(Limit=2)

    assert len(resp["Pipes"]) == 2
    assert "NextToken" in resp

    next_resp = client.list_pipes(NextToken=resp["NextToken"], Limit=2)

    assert len(next_resp["Pipes"]) == 2
    first_page_names = {p["Name"] for p in resp["Pipes"]}
    second_page_names = {p["Name"] for p in next_resp["Pipes"]}
    assert first_page_names.isdisjoint(second_page_names)


@mock_aws
def test_list_pipes_with_invalid_limit():
    config = Config(parameter_validation=False)
    client = boto3.client("pipes", region_name="eu-west-1", config=config)

    for i in range(3):
        client.create_pipe(
            Name=f"pipe-{i}",
            Source=f"arn:aws:sqs:eu-west-1:123456789012:queue-{i}",
            Target=f"arn:aws:lambda:eu-west-1:123456789012:function:func-{i}",
            RoleArn="arn:aws:iam::123456789012:role/test-role",
        )

    resp = client.list_pipes(Limit="invalid")

    assert "Pipes" in resp
    assert len(resp["Pipes"]) == 3


@mock_aws
def test_create_pipe_missing_source():
    config = Config(parameter_validation=False)
    client = boto3.client("pipes", region_name="us-east-1", config=config)
    with pytest.raises(ClientError) as exc_info:
        client.create_pipe(
            Name="test-pipe",
            Target="arn:aws:lambda:us-east-1:123456789012:function:test-function",
            RoleArn="arn:aws:iam::123456789012:role/test-role",
        )
    error = exc_info.value.response["Error"]
    assert error["Code"] == "ValidationException"
    assert "Source is a required parameter" in error["Message"]


@mock_aws
def test_create_pipe_missing_target():
    config = Config(parameter_validation=False)
    client = boto3.client("pipes", region_name="us-east-1", config=config)
    with pytest.raises(ClientError) as exc_info:
        client.create_pipe(
            Name="test-pipe",
            Source="arn:aws:sqs:us-east-1:123456789012:test-queue",
            RoleArn="arn:aws:iam::123456789012:role/test-role",
        )
    error = exc_info.value.response["Error"]
    assert error["Code"] == "ValidationException"
    assert "Target is a required parameter" in error["Message"]


@mock_aws
def test_create_pipe_missing_role_arn():
    config = Config(parameter_validation=False)
    client = boto3.client("pipes", region_name="us-east-1", config=config)
    with pytest.raises(ClientError) as exc_info:
        client.create_pipe(
            Name="test-pipe",
            Source="arn:aws:sqs:us-east-1:123456789012:test-queue",
            Target="arn:aws:lambda:us-east-1:123456789012:function:test-function",
        )
    error = exc_info.value.response["Error"]
    assert error["Code"] == "ValidationException"
    assert "RoleArn is a required parameter" in error["Message"]


def test_conflict_exception_with_all_parameters():
    from moto.pipes.exceptions import ConflictException

    exc = ConflictException(
        "Resource already exists",
        resource_id="test-pipe",
        resource_type="pipe",
    )
    assert exc.code == 409
    assert "Resource already exists" in exc.message
    import json

    body = json.loads(exc.description)
    assert body["resourceId"] == "test-pipe"
    assert body["resourceType"] == "pipe"


def test_internal_exception_with_retry_after():
    from moto.pipes.exceptions import InternalException

    exc = InternalException("Internal error", retry_after_seconds=30)
    assert exc.code == 500
    assert "Internal error" in exc.message
    import json

    body = json.loads(exc.description)
    assert body["retryAfterSeconds"] == 30


def test_service_quota_exceeded_exception_with_all_parameters():
    from moto.pipes.exceptions import ServiceQuotaExceededException

    exc = ServiceQuotaExceededException(
        "Quota exceeded",
        quota_code="L-12345678",
        resource_id="test-pipe",
        resource_type="pipe",
        service_code="pipes",
    )
    assert exc.code == 402
    assert "Quota exceeded" in exc.message
    import json

    body = json.loads(exc.description)
    assert body["quotaCode"] == "L-12345678"
    assert body["resourceId"] == "test-pipe"
    assert body["resourceType"] == "pipe"
    assert body["serviceCode"] == "pipes"


def test_throttling_exception_with_all_parameters():
    from moto.pipes.exceptions import ThrottlingException

    exc = ThrottlingException(
        "Rate limit exceeded",
        quota_code="L-12345678",
        retry_after_seconds=60,
        service_code="pipes",
    )
    assert exc.code == 429
    assert "Rate limit exceeded" in exc.message
    import json

    body = json.loads(exc.description)
    assert body["quotaCode"] == "L-12345678"
    assert body["retryAfterSeconds"] == 60
    assert body["serviceCode"] == "pipes"
