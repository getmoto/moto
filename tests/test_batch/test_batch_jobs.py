from . import _get_clients, _setup

import datetime
import sure  # noqa # pylint: disable=unused-import
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs, mock_logs
import botocore.exceptions
import pytest
import time
from uuid import uuid4


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_submit_job_by_name():
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
    ec2_client, iam_client, _, logs_client, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)
    start_time_milliseconds = time.time() * 1000

    job_def_name = str(uuid4())[0:6]
    commands = ["echo", "hello"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName=str(uuid4())[0:6], jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    # Test that describe_jobs() returns 'createdAt'
    # github.com/spulec/moto/issues/4364
    resp = batch_client.describe_jobs(jobs=[job_id])
    created_at = resp["jobs"][0]["createdAt"]
    created_at.should.be.greater_than(start_time_milliseconds)

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

    # Test that describe_jobs() returns timestamps in milliseconds
    # github.com/spulec/moto/issues/4364
    job = batch_client.describe_jobs(jobs=[job_id])["jobs"][0]
    created_at = job["createdAt"]
    started_at = job["startedAt"]
    stopped_at = job["stoppedAt"]

    created_at.should.be.greater_than(start_time_milliseconds)
    started_at.should.be.greater_than(start_time_milliseconds)
    stopped_at.should.be.greater_than(start_time_milliseconds)

    # Verify we track attempts
    job.should.have.key("attempts").length_of(1)
    attempt = job["attempts"][0]
    attempt.should.have.key("container")
    attempt["container"].should.have.key("containerInstanceArn")
    attempt["container"].should.have.key("logStreamName").equals(
        job["container"]["logStreamName"]
    )
    attempt["container"].should.have.key("networkInterfaces")
    attempt["container"].should.have.key("taskArn")
    attempt.should.have.key("startedAt").equals(started_at)
    attempt.should.have.key("stoppedAt").equals(stopped_at)


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
@pytest.mark.network
def test_list_jobs():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "sleep2"
    commands = ["sleep", "2"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id1 = resp["jobId"]
    resp = batch_client.submit_job(
        jobName="test2", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id2 = resp["jobId"]

    all_jobs = batch_client.list_jobs(jobQueue=queue_arn)["jobSummaryList"]
    all_jobs.should.have.length_of(2)
    for job in all_jobs:
        job.should.have.key("createdAt")
        job.should.have.key("jobDefinition")
        job.should.have.key("jobName")
        # This is async, so we can't be sure where we are in the process
        job.should.have.key("status").within(
            ["SUBMITTED", "PENDING", "STARTING", "RUNNABLE", "RUNNING"]
        )

    batch_client.list_jobs(jobQueue=queue_arn, jobStatus="SUCCEEDED")[
        "jobSummaryList"
    ].should.have.length_of(0)

    # Wait only as long as it takes to run the jobs
    for job_id in [job_id1, job_id2]:
        _wait_for_job_status(batch_client, job_id, "SUCCEEDED")

    succeeded_jobs = batch_client.list_jobs(jobQueue=queue_arn, jobStatus="SUCCEEDED")[
        "jobSummaryList"
    ]
    succeeded_jobs.should.have.length_of(2)
    for job in succeeded_jobs:
        job.should.have.key("createdAt")
        job.should.have.key("jobDefinition")
        job.should.have.key("jobName")
        job.should.have.key("status").equals("SUCCEEDED")
        job.should.have.key("stoppedAt")
        job.should.have.key("container").should.have.key("exitCode").equals(0)


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_terminate_job():
    ec2_client, iam_client, _, logs_client, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = f"echo-sleep-echo-{str(uuid4())[0:6]}"
    commands = ["sh", "-c", "echo start && sleep 30 && echo stop"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    _wait_for_job_status(batch_client, job_id, "RUNNING", seconds_to_wait=120)

    batch_client.terminate_job(jobId=job_id, reason="test_terminate")

    _wait_for_job_status(batch_client, job_id, "FAILED", seconds_to_wait=120)

    resp = batch_client.describe_jobs(jobs=[job_id])
    resp["jobs"][0]["jobName"].should.equal("test1")
    resp["jobs"][0]["status"].should.equal("FAILED")
    resp["jobs"][0]["statusReason"].should.equal("test_terminate")

    ls_name = f"{job_def_name}/default/{job_id}"

    resp = logs_client.get_log_events(
        logGroupName="/aws/batch/job", logStreamName=ls_name
    )
    # Events should only contain 'start' because we interrupted
    # the job before 'stop' was written to the logs.
    resp["events"].should.have.length_of(1)
    resp["events"][0]["message"].should.equal("start")


@mock_batch
def test_terminate_nonexisting_job():
    """
    Test verifies that you get a 200 HTTP status code when terminating a non-existing job.
    """
    _, _, _, _, batch_client = _get_clients()
    resp = batch_client.terminate_job(
        jobId="nonexisting_job", reason="test_terminate_nonexisting_job"
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_batch
def test_terminate_job_empty_argument_strings():
    """
    Test verifies that a `ClientException` is raised if `jobId` or `reason` is a empty string when terminating a job.
    """
    _, _, _, _, batch_client = _get_clients()
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.terminate_job(jobId="", reason="not_a_empty_string")
    assert exc.match("ClientException")

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.terminate_job(jobId="not_a_empty_string", reason="")
    assert exc.match("ClientException")


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_cancel_pending_job():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    # We need to be able to cancel a job that has not been started yet
    # Locally, our jobs start so fast that we can't cancel them in time
    # So delay our job, by letting it depend on a slow-running job
    commands = ["sleep", "10"]
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
    _wait_for_job_status(batch_client, job_id, "FAILED", seconds_to_wait=30)

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
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = "echo-o-o"
    commands = ["echo", "start"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName="test_job_name", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]
    _wait_for_job_statuses(
        batch_client, job_id, statuses=["RUNNABLE", "STARTING", "RUNNING"]
    )

    batch_client.cancel_job(jobId=job_id, reason="test_cancel")
    # We cancelled too late, the job was already running. Now we just wait for it to succeed
    _wait_for_job_status(batch_client, job_id, "SUCCEEDED", seconds_to_wait=30)

    resp = batch_client.describe_jobs(jobs=[job_id])
    resp["jobs"][0]["jobName"].should.equal("test_job_name")
    resp["jobs"][0].shouldnt.have.key("statusReason")


@mock_batch
def test_cancel_nonexisting_job():
    """
    Test verifies that you get a 200 HTTP status code when cancelling a non-existing job.
    """
    _, _, _, _, batch_client = _get_clients()
    resp = batch_client.cancel_job(
        jobId="nonexisting_job", reason="test_cancel_nonexisting_job"
    )
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_batch
def test_cancel_job_empty_argument_strings():
    """
    Test verifies that a `ClientException` is raised if `jobId` or `reason` is a empty string when cancelling a job.
    """
    _, _, _, _, batch_client = _get_clients()
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.cancel_job(jobId="", reason="not_a_empty_string")
    assert exc.match("ClientException")

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.cancel_job(jobId="not_a_empty_string", reason="")
    assert exc.match("ClientException")


def _wait_for_job_status(client, job_id, status, seconds_to_wait=30):
    _wait_for_job_statuses(client, job_id, [status], seconds_to_wait)


def _wait_for_job_statuses(client, job_id, statuses, seconds_to_wait=30):
    wait_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds_to_wait)
    last_job_status = None
    while datetime.datetime.now() < wait_time:
        resp = client.describe_jobs(jobs=[job_id])
        last_job_status = resp["jobs"][0]["status"]
        if last_job_status in statuses:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(
            f"Time out waiting for job status {statuses}!\n Last status: {last_job_status}"
        )


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_failed_job():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

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
    ec2_client, iam_client, _, logs_client, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

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

    log_stream_name = "/aws/batch/job"
    all_streams = retrieve_all_streams(log_stream_name, logs_client)

    nr_logstreams_found = 0
    expected_logstream_names = [
        f"dependencytest/default/{_id}" for _id in [job_id1, job_id2, job_id3]
    ]
    for log_stream in all_streams:
        ls_name = log_stream["logStreamName"]

        if ls_name not in expected_logstream_names:
            continue

        resp = logs_client.get_log_events(
            logGroupName=log_stream_name, logStreamName=ls_name
        )
        [event["message"] for event in resp["events"]].should.equal(["hello"])

        nr_logstreams_found = nr_logstreams_found + 1
    nr_logstreams_found.should.equal(3)


def retrieve_all_streams(log_stream_name, logs_client):
    resp = logs_client.describe_log_streams(logGroupName=log_stream_name)
    all_streams = resp["logStreams"]
    token = resp.get("nextToken")
    while token:
        resp = logs_client.describe_log_streams(
            logGroupName=log_stream_name, nextToken=token
        )
        all_streams.extend(resp["logStreams"])
        token = resp.get("nextToken")
    return all_streams


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_failed_dependencies():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())[0:6]
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4())[0:6],
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
            "command": ["exit", "1"],
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

    ec2_client, iam_client, _, logs_client, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())[0:6]
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4())[0:6],
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    job_definition_name = f"sleep10_{str(uuid4())[0:6]}"

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
    compute_name = str(uuid4())[0:6]
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4())[0:6],
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


@mock_batch
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


@mock_batch
def test_register_job_definition_with_timeout():
    _, _, _, _, batch_client = _get_clients()

    container_props = {
        "image": "amazonlinux",
        "memory": 1024,
        "vcpus": 2,
    }

    job_def_name = str(uuid4())[0:6]
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        parameters={},
        containerProperties=container_props,
        timeout={"attemptDurationSeconds": 3},
    )

    resp = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)
    job_def = resp["jobDefinitions"][0]
    job_def.should.have.key("timeout").equals({"attemptDurationSeconds": 3})


@mock_batch
@mock_ec2
@mock_iam
def test_submit_job_with_timeout():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = str(uuid4())[0:6]
    commands = ["sleep", "30"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)

    resp = batch_client.submit_job(
        jobName=str(uuid4())[0:6],
        jobQueue=queue_arn,
        jobDefinition=job_def_arn,
        timeout={"attemptDurationSeconds": 1},
    )
    job_id = resp["jobId"]

    # This should fail, as the job-duration is longer than the attemptDurationSeconds
    _wait_for_job_status(batch_client, job_id, "FAILED")


@mock_batch
@mock_ec2
@mock_iam
def test_submit_job_with_timeout_set_at_definition():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = str(uuid4())[0:6]
    commands = ["sleep", "30"]
    _, queue_arn = prepare_job(batch_client, commands, iam_arn, job_def_name)
    resp = batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        containerProperties={
            "image": "busybox:latest",
            "vcpus": 1,
            "memory": 128,
            "command": commands,
        },
        timeout={"attemptDurationSeconds": 1},
    )
    job_def_arn = resp["jobDefinitionArn"]

    resp = batch_client.submit_job(
        jobName=str(uuid4())[0:6], jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    # This should fail, as the job-duration is longer than the attemptDurationSeconds
    _wait_for_job_status(batch_client, job_id, "FAILED")


@mock_batch
def test_submit_job_invalid_name():
    """
    Test verifies that a `ClientException` is raised if `jobName` isn't valid
    """
    _, _, _, _, batch_client = _get_clients()
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.submit_job(
            jobName="containsinvalidcharacter.",
            jobQueue="arn",
            jobDefinition="job_def_name",
        )
    assert exc.match("ClientException")

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.submit_job(
            jobName="-startswithinvalidcharacter",
            jobQueue="arn",
            jobDefinition="job_def_name",
        )
    assert exc.match("ClientException")

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        too_long_job_name = "a" * 129
        batch_client.submit_job(
            jobName=too_long_job_name, jobQueue="arn", jobDefinition="job_def_name"
        )
    assert exc.match("ClientException")
