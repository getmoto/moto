from . import _get_clients, _setup

from botocore.exceptions import ClientError
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
    resp.should.contain("jobQueues")
    len(resp["jobQueues"]).should.equal(1)
    resp["jobQueues"][0]["jobQueueArn"].should.equal(queue_arn)

    resp = batch_client.describe_job_queues(jobQueues=["test_invalid_queue"])
    resp.should.contain("jobQueues")
    len(resp["jobQueues"]).should.equal(0)

    # Create job queue which already exists
    try:
        resp = batch_client.create_job_queue(
            jobQueueName="test_job_queue",
            state="ENABLED",
            priority=123,
            computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
        )

    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ClientException")

    # Create job queue with incorrect state
    try:
        resp = batch_client.create_job_queue(
            jobQueueName="test_job_queue2",
            state="JUNK",
            priority=123,
            computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
        )

    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ClientException")

    # Create job queue with no compute env
    try:
        resp = batch_client.create_job_queue(
            jobQueueName="test_job_queue3",
            state="JUNK",
            priority=123,
            computeEnvironmentOrder=[],
        )

    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ClientException")


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

    try:
        batch_client.create_job_queue(
            jobQueueName="test_job_queue",
            state="ENABLED",
            priority=123,
            computeEnvironmentOrder=[
                {"order": 123, "computeEnvironment": arn + "LALALA"}
            ],
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ClientException")


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
    resp.should.contain("jobQueues")
    len(resp["jobQueues"]).should.equal(1)
    resp["jobQueues"][0]["priority"].should.equal(5)

    batch_client.update_job_queue(jobQueue="test_job_queue", priority=5)

    resp = batch_client.describe_job_queues()
    resp.should.contain("jobQueues")
    len(resp["jobQueues"]).should.equal(1)
    resp["jobQueues"][0]["priority"].should.equal(5)


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

    batch_client.delete_job_queue(jobQueue=queue_arn)

    resp = batch_client.describe_job_queues()
    resp.should.contain("jobQueues")
    len(resp["jobQueues"]).should.equal(0)
