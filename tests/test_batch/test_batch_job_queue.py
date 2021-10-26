from . import _get_clients, _setup

from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs
from uuid import uuid4


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue():
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

    jq_name = str(uuid4())[0:6]
    resp = batch_client.create_job_queue(
        jobQueueName=jq_name,
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    resp.should.contain("jobQueueArn")
    resp.should.contain("jobQueueName")
    queue_arn = resp["jobQueueArn"]

    all_queues = batch_client.describe_job_queues()["jobQueues"]
    our_queues = [q for q in all_queues if q["jobQueueName"] == jq_name]
    our_queues.should.have.length_of(1)
    our_queues[0]["jobQueueArn"].should.equal(queue_arn)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_job_queue_unknown_value():
    _, _, _, _, batch_client = _get_clients()

    resp = batch_client.describe_job_queues(jobQueues=["test_invalid_queue"])
    resp.should.have.key("jobQueues").being.length_of(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue_twice():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    compute_env_arn = resp["computeEnvironmentArn"]

    jq_name = str(uuid4())[0:6]
    batch_client.create_job_queue(
        jobQueueName=jq_name,
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": compute_env_arn}],
    )
    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName=jq_name,
            state="ENABLED",
            priority=123,
            computeEnvironmentOrder=[
                {"order": 123, "computeEnvironment": compute_env_arn}
            ],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ClientException")
    err["Message"].should.equal(f"Job queue {jq_name} already exists")


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue_incorrect_state():
    _, _, _, _, batch_client = _get_clients()

    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName=str(uuid4()),
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
    _, _, _, _, batch_client = _get_clients()

    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName=str(uuid4()),
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

    with pytest.raises(ClientError) as ex:
        batch_client.create_job_queue(
            jobQueueName=str(uuid4()),
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

    jq_name = str(uuid4())
    resp = batch_client.create_job_queue(
        jobQueueName=jq_name,
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    batch_client.update_job_queue(jobQueue=queue_arn, priority=5)

    all_queues = batch_client.describe_job_queues()["jobQueues"]
    our_queues = [q for q in all_queues if q["jobQueueName"] == jq_name]
    our_queues[0]["priority"].should.equal(5)

    batch_client.update_job_queue(jobQueue=jq_name, priority=15)

    all_queues = batch_client.describe_job_queues()["jobQueues"]
    our_queues = [q for q in all_queues if q["jobQueueName"] == jq_name]
    our_queues.should.have.length_of(1)
    our_queues[0]["priority"].should.equal(15)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_job_queue():
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

    jq_name = str(uuid4())
    resp = batch_client.create_job_queue(
        jobQueueName=jq_name,
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    batch_client.delete_job_queue(jobQueue=queue_arn)

    all_queues = batch_client.describe_job_queues()["jobQueues"]
    [q["jobQueueName"] for q in all_queues].shouldnt.contain(jq_name)
