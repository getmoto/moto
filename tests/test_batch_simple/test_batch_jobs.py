from ..test_batch import _get_clients, _setup

import sure  # noqa # pylint: disable=unused-import
from moto import mock_iam, mock_ec2, mock_ecs, mock_logs, settings
from moto import mock_batch_simple
from uuid import uuid4
from unittest import SkipTest


# Copy of test_batch/test_batch_jobs
# Except that we verify this behaviour still works without docker


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch_simple
def test_submit_job_by_name():
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

    job_definition_name = f"sleep10_{str(uuid4())[0:6]}"

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

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_definition_name
    )
    job_id = resp["jobId"]

    resp_jobs = batch_client.describe_jobs(jobs=[job_id])

    len(resp_jobs["jobs"]).should.equal(1)
    job = resp_jobs["jobs"][0]

    job["jobId"].should.equal(job_id)
    job["jobQueue"].should.equal(queue_arn)
    job["jobDefinition"].should.equal(job_definition_arn)
    job["status"].should.equal("SUCCEEDED")
    job.should.contain("container")
    job["container"].should.contain("command")
    job["container"].should.contain("logStreamName")


@mock_batch_simple
def test_update_job_definition():
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
    job_defs.should.have.length_of(2)

    job_defs[0]["containerProperties"]["memory"].should.equal(1024)
    job_defs[0]["tags"].should.equal(tags[0])
    job_defs[0].shouldnt.have.key("timeout")

    job_defs[1]["containerProperties"]["memory"].should.equal(2048)
    job_defs[1]["tags"].should.equal(tags[1])
