from . import _get_clients, _setup

import datetime
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs, mock_logs
import pytest
import time


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_submit_job_by_name():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName="test_job_queue",
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    job_definition_name = "sleep10"

    batch_client.register_job_definition(
        jobDefinitionName=job_definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 128,
            "command": ["sleep", "10"],
        },
    )
    batch_client.register_job_definition(
        jobDefinitionName=job_definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 256,
            "command": ["sleep", "10"],
        },
    )
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

    # batch_client.terminate_job(jobId=job_id)

    len(resp_jobs["jobs"]).should.equal(1)
    resp_jobs["jobs"][0]["jobId"].should.equal(job_id)
    resp_jobs["jobs"][0]["jobQueue"].should.equal(queue_arn)
    resp_jobs["jobs"][0]["jobDefinition"].should.equal(job_definition_arn)


# SLOW TESTS


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
@pytest.mark.network
def test_submit_job():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "sayhellotomylittlefriend"
    commands = ["echo", "hello"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    _wait_for_job_status(batch_client, job_id, "SUCCEEDED")

    resp = logs_client.describe_log_streams(
        logGroupName="/aws/batch/job", logStreamNamePrefix=job_def_name
    )
    resp["logStreams"].should.have.length_of(1)
    ls_name = resp["logStreams"][0]["logStreamName"]

    resp = logs_client.get_log_events(
        logGroupName="/aws/batch/job", logStreamName=ls_name
    )
    [event["message"] for event in resp["events"]].should.equal(["hello"])


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
@pytest.mark.network
def test_list_jobs():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "sleep5"
    commands = ["sleep", "5"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id1 = resp["jobId"]
    resp = batch_client.submit_job(
        jobName="test2", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id2 = resp["jobId"]

    batch_client.list_jobs(jobQueue=queue_arn, jobStatus="SUCCEEDED")[
        "jobSummaryList"
    ].should.have.length_of(0)

    # Wait only as long as it takes to run the jobs
    for job_id in [job_id1, job_id2]:
        _wait_for_job_status(batch_client, job_id, "SUCCEEDED")

    batch_client.list_jobs(jobQueue=queue_arn, jobStatus="SUCCEEDED")[
        "jobSummaryList"
    ].should.have.length_of(2)


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_terminate_job():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "echo-sleep-echo"
    commands = ["sh", "-c", "echo start && sleep 30 && echo stop"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    _wait_for_job_status(batch_client, job_id, "RUNNING")

    batch_client.terminate_job(jobId=job_id, reason="test_terminate")

    _wait_for_job_status(batch_client, job_id, "FAILED")

    resp = batch_client.describe_jobs(jobs=[job_id])
    resp["jobs"][0]["jobName"].should.equal("test1")
    resp["jobs"][0]["status"].should.equal("FAILED")
    resp["jobs"][0]["statusReason"].should.equal("test_terminate")

    resp = logs_client.describe_log_streams(
        logGroupName="/aws/batch/job", logStreamNamePrefix=job_def_name
    )
    resp["logStreams"].should.have.length_of(1)
    ls_name = resp["logStreams"][0]["logStreamName"]

    resp = logs_client.get_log_events(
        logGroupName="/aws/batch/job", logStreamName=ls_name
    )
    # Events should only contain 'start' because we interrupted
    # the job before 'stop' was written to the logs.
    resp["events"].should.have.length_of(1)
    resp["events"][0]["message"].should.equal("start")


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_cancel_pending_job():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    # We need to be able to cancel a job that has not been started yet
    # Locally, our jobs start so fast that we can't cancel them in time
    # So delay our job, by letting it depend on a slow-running job
    commands = ["sleep", "1"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, "deptest")

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    delayed_job = resp["jobId"]

    depends_on = [{"jobId": delayed_job, "type": "SEQUENTIAL"}]
    resp = batch_client.submit_job(
        jobName="test_job_name",
        jobQueue=queue_arn,
        jobDefinition=job_def_arn,
        dependsOn=depends_on,
    )
    job_id = resp["jobId"]

    batch_client.cancel_job(jobId=job_id, reason="test_cancel")
    _wait_for_job_status(batch_client, job_id, "FAILED", seconds_to_wait=10)

    resp = batch_client.describe_jobs(jobs=[job_id])
    resp["jobs"][0]["jobName"].should.equal("test_job_name")
    resp["jobs"][0]["statusReason"].should.equal("test_cancel")


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_cancel_running_job():
    """
    Test verifies that the moment the job has started, we can't cancel anymore
    """
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "echo-o-o"
    commands = ["echo", "start"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test_job_name", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]
    _wait_for_job_status(batch_client, job_id, "STARTING")

    batch_client.cancel_job(jobId=job_id, reason="test_cancel")
    # We cancelled too late, the job was already running. Now we just wait for it to succeed
    _wait_for_job_status(batch_client, job_id, "SUCCEEDED", seconds_to_wait=5)

    resp = batch_client.describe_jobs(jobs=[job_id])
    resp["jobs"][0]["jobName"].should.equal("test_job_name")
    resp["jobs"][0].shouldnt.have.key("statusReason")


def _wait_for_job_status(client, job_id, status, seconds_to_wait=30):
    wait_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds_to_wait)
    last_job_status = None
    while datetime.datetime.now() < wait_time:
        resp = client.describe_jobs(jobs=[job_id])
        last_job_status = resp["jobs"][0]["status"]
        if last_job_status == status:
            break
    else:
        raise RuntimeError(
            "Time out waiting for job status {status}!\n Last status: {last_status}".format(
                status=status, last_status=last_job_status
            )
        )


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_failed_job():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "exit-1"
    commands = ["exit", "1"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    future = datetime.datetime.now() + datetime.timedelta(seconds=30)

    while datetime.datetime.now() < future:
        resp = batch_client.describe_jobs(jobs=[job_id])

        if resp["jobs"][0]["status"] == "FAILED":
            break
        if resp["jobs"][0]["status"] == "SUCCEEDED":
            raise RuntimeError("Batch job succeeded even though it had exit code 1")
        time.sleep(0.5)
    else:
        raise RuntimeError("Batch job timed out")


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_dependencies():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    job_def_arn, queue_arn = prepare_job(
        batch_client,
        commands=["echo", "hello"],
        iam_arn=iam_arn,
        job_def_name="dependencytest",
    )

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id1 = resp["jobId"]

    resp = batch_client.submit_job(
        jobName="test2", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id2 = resp["jobId"]

    depends_on = [
        {"jobId": job_id1, "type": "SEQUENTIAL"},
        {"jobId": job_id2, "type": "SEQUENTIAL"},
    ]
    resp = batch_client.submit_job(
        jobName="test3",
        jobQueue=queue_arn,
        jobDefinition=job_def_arn,
        dependsOn=depends_on,
    )
    job_id3 = resp["jobId"]

    future = datetime.datetime.now() + datetime.timedelta(seconds=30)

    while datetime.datetime.now() < future:
        resp = batch_client.describe_jobs(jobs=[job_id1, job_id2, job_id3])

        if any([job["status"] == "FAILED" for job in resp["jobs"]]):
            raise RuntimeError("Batch job failed")
        if all([job["status"] == "SUCCEEDED" for job in resp["jobs"]]):
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Batch job timed out")

    resp = logs_client.describe_log_streams(logGroupName="/aws/batch/job")
    len(resp["logStreams"]).should.equal(3)
    for log_stream in resp["logStreams"]:
        ls_name = log_stream["logStreamName"]

        resp = logs_client.get_log_events(
            logGroupName="/aws/batch/job", logStreamName=ls_name
        )
        [event["message"] for event in resp["events"]].should.equal(["hello"])


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_failed_dependencies():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName="test_job_queue",
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    resp = batch_client.register_job_definition(
        jobDefinitionName="sayhellotomylittlefriend",
        type="container",
        containerProperties={
            "image": "busybox:latest",
            "vcpus": 1,
            "memory": 128,
            "command": ["echo", "hello"],
        },
    )
    job_def_arn_success = resp["jobDefinitionArn"]

    resp = batch_client.register_job_definition(
        jobDefinitionName="sayhellotomylittlefriend_failed",
        type="container",
        containerProperties={
            "image": "busybox:latest",
            "vcpus": 1,
            "memory": 128,
            "command": ["exi1", "1"],
        },
    )
    job_def_arn_failure = resp["jobDefinitionArn"]

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn_success
    )

    job_id1 = resp["jobId"]

    resp = batch_client.submit_job(
        jobName="test2", jobQueue=queue_arn, jobDefinition=job_def_arn_failure
    )
    job_id2 = resp["jobId"]

    depends_on = [
        {"jobId": job_id1, "type": "SEQUENTIAL"},
        {"jobId": job_id2, "type": "SEQUENTIAL"},
    ]
    resp = batch_client.submit_job(
        jobName="test3",
        jobQueue=queue_arn,
        jobDefinition=job_def_arn_success,
        dependsOn=depends_on,
    )
    job_id3 = resp["jobId"]

    future = datetime.datetime.now() + datetime.timedelta(seconds=30)

    # Query batch jobs until all jobs have run.
    # Job 2 is supposed to fail and in consequence Job 3 should never run
    # and status should change directly from PENDING to FAILED
    while datetime.datetime.now() < future:
        resp = batch_client.describe_jobs(jobs=[job_id2, job_id3])

        assert resp["jobs"][0]["status"] != "SUCCEEDED", "Job 2 cannot succeed"
        assert resp["jobs"][1]["status"] != "SUCCEEDED", "Job 3 cannot succeed"

        if resp["jobs"][1]["status"] == "FAILED":
            break

        time.sleep(0.5)
    else:
        raise RuntimeError("Batch job timed out")


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_container_overrides():
    """
    Test if container overrides have any effect.
    Overwrites should be reflected in container description.
    Environment variables should be accessible inside docker container
    """

    # Set up environment

    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName="test_job_queue",
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    job_definition_name = "sleep10"

    # Set up Job Definition
    # We will then override the container properties in the actual job
    resp = batch_client.register_job_definition(
        jobDefinitionName=job_definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 512,
            "command": ["sleep", "10"],
            "environment": [
                {"name": "TEST0", "value": "from job definition"},
                {"name": "TEST1", "value": "from job definition"},
            ],
        },
    )

    job_definition_arn = resp["jobDefinitionArn"]

    # The Job to run, including container overrides
    resp = batch_client.submit_job(
        jobName="test1",
        jobQueue=queue_arn,
        jobDefinition=job_definition_name,
        containerOverrides={
            "vcpus": 2,
            "memory": 1024,
            "command": ["printenv"],
            "environment": [
                {"name": "TEST0", "value": "from job"},
                {"name": "TEST2", "value": "from job"},
            ],
        },
    )

    job_id = resp["jobId"]

    # Wait until Job finishes
    future = datetime.datetime.now() + datetime.timedelta(seconds=30)

    while datetime.datetime.now() < future:
        resp_jobs = batch_client.describe_jobs(jobs=[job_id])

        if resp_jobs["jobs"][0]["status"] == "FAILED":
            raise RuntimeError("Batch job failed")
        if resp_jobs["jobs"][0]["status"] == "SUCCEEDED":
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Batch job timed out")

    # Getting the log stream to read out env variables inside container
    resp = logs_client.describe_log_streams(logGroupName="/aws/batch/job")

    env_var = list()
    for stream in resp["logStreams"]:
        ls_name = stream["logStreamName"]

        stream_resp = logs_client.get_log_events(
            logGroupName="/aws/batch/job", logStreamName=ls_name
        )

        for event in stream_resp["events"]:
            if "TEST" in event["message"] or "AWS" in event["message"]:
                key, value = tuple(event["message"].split("="))
                env_var.append({"name": key, "value": value})

    len(resp_jobs["jobs"]).should.equal(1)
    resp_jobs["jobs"][0]["jobId"].should.equal(job_id)
    resp_jobs["jobs"][0]["jobQueue"].should.equal(queue_arn)
    resp_jobs["jobs"][0]["jobDefinition"].should.equal(job_definition_arn)
    resp_jobs["jobs"][0]["container"]["vcpus"].should.equal(2)
    resp_jobs["jobs"][0]["container"]["memory"].should.equal(1024)
    resp_jobs["jobs"][0]["container"]["command"].should.equal(["printenv"])

    sure.expect(resp_jobs["jobs"][0]["container"]["environment"]).to.contain(
        {"name": "TEST0", "value": "from job"}
    )
    sure.expect(resp_jobs["jobs"][0]["container"]["environment"]).to.contain(
        {"name": "TEST1", "value": "from job definition"}
    )
    sure.expect(resp_jobs["jobs"][0]["container"]["environment"]).to.contain(
        {"name": "TEST2", "value": "from job"}
    )
    sure.expect(resp_jobs["jobs"][0]["container"]["environment"]).to.contain(
        {"name": "AWS_BATCH_JOB_ID", "value": job_id}
    )

    sure.expect(env_var).to.contain({"name": "TEST0", "value": "from job"})
    sure.expect(env_var).to.contain({"name": "TEST1", "value": "from job definition"})
    sure.expect(env_var).to.contain({"name": "TEST2", "value": "from job"})

    sure.expect(env_var).to.contain({"name": "AWS_BATCH_JOB_ID", "value": job_id})


def prepare_job(batch_client, commands, iam_arn, job_def_name):
    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName="test_job_queue",
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]
    resp = batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        containerProperties={
            "image": "busybox:latest",
            "vcpus": 1,
            "memory": 128,
            "command": commands,
        },
    )
    job_def_arn = resp["jobDefinitionArn"]
    return job_def_arn, queue_arn
