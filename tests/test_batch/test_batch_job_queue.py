from . import _get_clients, _setup

from botocore.exceptions import ClientError
import pytest
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue():
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
    resp.should.contain("jobQueueArn")
    resp.should.contain("jobQueueName")
    queue_arn = resp["jobQueueArn"]

    resp = batch_client.describe_job_queues()
    resp.should.have.key("jobQueues").being.length_of(1)
    resp["jobQueues"][0]["jobQueueArn"].should.equal(queue_arn)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_job_queue_unknown_value():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()

    resp = batch_client.describe_job_queues(jobQueues=["test_invalid_queue"])
    resp.should.have.key("jobQueues").being.length_of(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue_twice():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    compute_env_arn = resp["computeEnvironmentArn"]

    batch_client.create_job_queue(
        jobQueueName="test_job_queue",
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": compute_env_arn}],
    )
    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName="test_job_queue",
            state="ENABLED",
            priority=123,
            computeEnvironmentOrder=[
                {"order": 123, "computeEnvironment": compute_env_arn}
            ],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ClientException")
    err["Message"].should.equal("Job queue test_job_queue already exists")


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue_incorrect_state():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()

    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName="test_job_queue2",
            state="JUNK",
            priority=123,
            computeEnvironmentOrder=[],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClientException")
    err["Message"].should.equal("state JUNK must be one of ENABLED | DISABLED")


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue_without_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()

    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName="test_job_queue3",
            state="ENABLED",
            priority=123,
            computeEnvironmentOrder=[],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClientException")
    err["Message"].should.equal("At least 1 compute environment must be provided")


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_job_queue_bad_arn():
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

    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName="test_job_queue",
            state="ENABLED",
            priority=123,
            computeEnvironmentOrder=[
                {"order": 123, "computeEnvironment": arn + "LALALA"}
            ],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClientException")
    err["Message"].should.equal("computeEnvironmentOrder is malformed")


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_update_job_queue():
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

    batch_client.update_job_queue(jobQueue=queue_arn, priority=5)

    resp = batch_client.describe_job_queues()
    resp.should.have.key("jobQueues").being.length_of(1)
    resp["jobQueues"][0]["priority"].should.equal(5)

    batch_client.update_job_queue(jobQueue="test_job_queue", priority=5)

    resp = batch_client.describe_job_queues()
    resp.should.have.key("jobQueues").being.length_of(1)
    resp["jobQueues"][0]["priority"].should.equal(5)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_job_queue():
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

    batch_client.delete_job_queue(jobQueue=queue_arn)

    resp = batch_client.describe_job_queues()
    resp.should.have.key("jobQueues").being.length_of(0)
