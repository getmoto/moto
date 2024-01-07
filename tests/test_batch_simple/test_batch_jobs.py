import os
from typing import Any, Tuple
from unittest import SkipTest, mock
from uuid import uuid4

from moto import mock_aws, settings

from ..test_batch import _get_clients, _setup

# Copy of test_batch/test_batch_jobs
# Except that we verify this behaviour still works without docker


@mock_aws(config={"batch": {"use_docker": False}})
def test_submit_job_by_name() -> None:
    job_definition_name = f"sleep10_{str(uuid4())[0:6]}"
    batch_client, job_definition_arn, queue_arn = setup_common_batch_simple(
        job_definition_name
    )

    resp = batch_client.submit_job(
        jobName="test1",
        jobQueue=queue_arn,
        jobDefinition=job_definition_name,
    )
    job_id = resp["jobId"]

    resp_jobs = batch_client.describe_jobs(jobs=[job_id])
    assert len(resp_jobs["jobs"]) == 1

    job = resp_jobs["jobs"][0]

    assert job["jobId"] == job_id
    assert job["jobQueue"] == queue_arn
    assert job["jobDefinition"] == job_definition_arn
    assert job["status"] == "SUCCEEDED"
    assert "container" in job
    assert "command" in job["container"]
    assert "logStreamName" in job["container"]


@mock_aws(config={"batch": {"use_docker": False}})
def test_submit_job_array_size() -> None:
    # Setup
    job_definition_name = f"sleep10_{str(uuid4())[0:6]}"
    batch_client, _, queue_arn = setup_common_batch_simple(job_definition_name)

    # Execute
    resp = batch_client.submit_job(
        jobName="test1",
        jobQueue=queue_arn,
        jobDefinition=job_definition_name,
        arrayProperties={"size": 2},
    )

    # Verify
    job_id = resp["jobId"]
    child_job_1_id = f"{job_id}:0"

    job = batch_client.describe_jobs(jobs=[job_id])["jobs"][0]

    assert job["arrayProperties"]["size"] == 2
    assert job["attempts"] == []

    # If the main job is successful, that means that all child jobs are successful
    assert job["arrayProperties"]["size"] == 2
    assert job["arrayProperties"]["statusSummary"]["SUCCEEDED"] == 2
    # Main job still has no attempts - because only the child jobs are executed
    assert job["attempts"] == []

    child_job_1 = batch_client.describe_jobs(jobs=[child_job_1_id])["jobs"][0]
    assert child_job_1["status"] == "SUCCEEDED"
    # Child job was executed
    assert len(child_job_1["attempts"]) == 1


@mock_aws(config={"batch": {"use_docker": False}})
def test_update_job_definition() -> None:
    _, _, _, _, batch_client = _get_clients()

    tags = [
        {"Foo1": "bar1", "Baz1": "buzz1"},
        {"Foo2": "bar2", "Baz2": "buzz2"},
    ]

    container_props = {
        "image": "amazonlinux",
        "memory": 1024,
        "vcpus": 2,
    }

    job_def_name = str(uuid4())[0:6]
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        tags=tags[0],
        parameters={},
        containerProperties=container_props,
    )

    container_props["memory"] = 2048
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        tags=tags[1],
        parameters={},
        containerProperties=container_props,
    )

    job_defs = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)[
        "jobDefinitions"
    ]
    assert len(job_defs) == 2

    assert job_defs[0]["containerProperties"]["memory"] == 1024
    assert job_defs[0]["tags"] == tags[0]
    assert "timeout" not in job_defs[0]

    assert job_defs[1]["containerProperties"]["memory"] == 2048
    assert job_defs[1]["tags"] == tags[1]


@mock_aws(config={"batch": {"use_docker": False}})
def test_submit_job_fail() -> None:
    job_definition_name = "test_job_moto_fail"

    with mock.patch.dict(os.environ, {"MOTO_SIMPLE_BATCH_FAIL_AFTER": "0"}):
        batch_client, _, queue_arn = setup_common_batch_simple(job_definition_name)

        resp = batch_client.submit_job(
            jobName=job_definition_name,
            jobQueue=queue_arn,
            jobDefinition=job_definition_name,
        )
        job_id = resp["jobId"]

        resp_jobs = batch_client.describe_jobs(jobs=[job_id])
        assert len(resp_jobs["jobs"]) == 1

        job = resp_jobs["jobs"][0]

        assert job["jobId"] == job_id
        assert job["status"] == "FAILED"


@mock_aws(config={"batch": {"use_docker": False}})
def test_submit_job_fail_after_1_secs() -> None:
    job_definition_name = "test_job_moto_fail"

    with mock.patch.dict(os.environ, {"MOTO_SIMPLE_BATCH_FAIL_AFTER": "1"}):
        batch_client, _, queue_arn = setup_common_batch_simple(job_definition_name)

        resp = batch_client.submit_job(
            jobName=job_definition_name,
            jobQueue=queue_arn,
            jobDefinition=job_definition_name,
        )
        job_id = resp["jobId"]

        resp_jobs = batch_client.describe_jobs(jobs=[job_id])
        assert len(resp_jobs["jobs"]) == 1

        job = resp_jobs["jobs"][0]

        assert job["jobId"] == job_id
        assert job["status"] == "FAILED"


@mock_aws(config={"batch": {"use_docker": False}})
def test_submit_job_fail_bad_int() -> None:
    job_definition_name = "test_job_moto_fail"

    with mock.patch.dict(
        os.environ, {"MOTO_SIMPLE_BATCH_FAIL_AFTER": "CANT_PARSE_AS_INT"}
    ):
        batch_client, _, queue_arn = setup_common_batch_simple(job_definition_name)

        resp = batch_client.submit_job(
            jobName=job_definition_name,
            jobQueue=queue_arn,
            jobDefinition=job_definition_name,
        )
        job_id = resp["jobId"]

        resp_jobs = batch_client.describe_jobs(jobs=[job_id])
        assert len(resp_jobs["jobs"]) == 1

        job = resp_jobs["jobs"][0]

        assert job["jobId"] == job_id
        assert job["status"] == "FAILED"


def setup_common_batch_simple(job_definition_name: str) -> Tuple[Any, str, str]:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No point in testing batch_simple in ServerMode")

    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4()),
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    resp = batch_client.register_job_definition(
        jobDefinitionName=job_definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 512,
            "command": ["sleep", "10"],
        },
    )
    job_definition_arn = resp["jobDefinitionArn"]

    return batch_client, job_definition_arn, queue_arn
