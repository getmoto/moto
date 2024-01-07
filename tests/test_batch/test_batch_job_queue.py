from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from . import _get_clients, _setup


@mock_aws
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
        schedulingPolicyArn="policy_arn",
    )
    assert "jobQueueArn" in resp
    assert "jobQueueName" in resp
    queue_arn = resp["jobQueueArn"]

    all_queues = batch_client.describe_job_queues()["jobQueues"]
    our_queues = [q for q in all_queues if q["jobQueueName"] == jq_name]
    assert len(our_queues) == 1
    assert our_queues[0]["jobQueueArn"] == queue_arn
    assert our_queues[0]["schedulingPolicyArn"] == "policy_arn"


@mock_aws
def test_describe_job_queue_unknown_value():
    batch_client = boto3.client("batch", "us-east-1")

    resp = batch_client.describe_job_queues(jobQueues=["test_invalid_queue"])
    assert len(resp["jobQueues"]) == 0


@mock_aws
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
    assert err["Code"] == "ClientException"
    assert err["Message"] == f"Job queue {jq_name} already exists"


@mock_aws
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
    assert err["Code"] == "ClientException"
    assert err["Message"] == "state JUNK must be one of ENABLED | DISABLED"


@mock_aws
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
    assert err["Code"] == "ClientException"
    assert err["Message"] == "At least 1 compute environment must be provided"


@mock_aws
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
    assert err["Code"] == "ClientException"
    assert err["Message"] == "computeEnvironmentOrder is malformed"


@mock_aws
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
    assert our_queues[0]["priority"] == 5

    batch_client.update_job_queue(jobQueue=jq_name, priority=15)

    all_queues = batch_client.describe_job_queues()["jobQueues"]
    our_queues = [q for q in all_queues if q["jobQueueName"] == jq_name]
    assert len(our_queues) == 1
    assert our_queues[0]["priority"] == 15


@mock_aws
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
    assert jq_name not in [q["jobQueueName"] for q in all_queues]
