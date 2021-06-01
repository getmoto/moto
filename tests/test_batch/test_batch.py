from __future__ import unicode_literals

import time
import datetime
import boto3
from botocore.exceptions import ClientError
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs, mock_logs
import pytest

DEFAULT_REGION = "eu-central-1"


def _get_clients():
    return (
        boto3.client("ec2", region_name=DEFAULT_REGION),
        boto3.client("iam", region_name=DEFAULT_REGION),
        boto3.client("ecs", region_name=DEFAULT_REGION),
        boto3.client("logs", region_name=DEFAULT_REGION),
        boto3.client("batch", region_name=DEFAULT_REGION),
    )


def _setup(ec2_client, iam_client):
    """
    Do prerequisite setup
    :return: VPC ID, Subnet ID, Security group ID, IAM Role ARN
    :rtype: tuple
    """
    resp = ec2_client.create_vpc(CidrBlock="172.30.0.0/24")
    vpc_id = resp["Vpc"]["VpcId"]
    resp = ec2_client.create_subnet(
        AvailabilityZone="eu-central-1a", CidrBlock="172.30.0.0/25", VpcId=vpc_id
    )
    subnet_id = resp["Subnet"]["SubnetId"]
    resp = ec2_client.create_security_group(
        Description="test_sg_desc", GroupName="test_sg", VpcId=vpc_id
    )
    sg_id = resp["GroupId"]

    resp = iam_client.create_role(
        RoleName="TestRole", AssumeRolePolicyDocument="some_policy"
    )
    iam_arn = resp["Role"]["Arn"]
    iam_client.create_instance_profile(InstanceProfileName="TestRole")
    iam_client.add_role_to_instance_profile(
        InstanceProfileName="TestRole", RoleName="TestRole"
    )

    return vpc_id, subnet_id, sg_id, iam_arn


# Yes, yes it talks to all the things
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_managed_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="MANAGED",
        state="ENABLED",
        computeResources={
            "type": "EC2",
            "minvCpus": 5,
            "maxvCpus": 10,
            "desiredvCpus": 5,
            "instanceTypes": ["t2.small", "t2.medium"],
            "imageId": "some_image_id",
            "subnets": [subnet_id],
            "securityGroupIds": [sg_id],
            "ec2KeyPair": "string",
            "instanceRole": iam_arn.replace("role", "instance-profile"),
            "tags": {"string": "string"},
            "bidPercentage": 123,
            "spotIamFleetRole": "string",
        },
        serviceRole=iam_arn,
    )
    resp.should.contain("computeEnvironmentArn")
    resp["computeEnvironmentName"].should.equal(compute_name)

    # Given a t2.medium is 2 vcpu and t2.small is 1, therefore 2 mediums and 1 small should be created
    resp = ec2_client.describe_instances()
    resp.should.contain("Reservations")
    len(resp["Reservations"]).should.equal(3)

    # Should have created 1 ECS cluster
    resp = ecs_client.list_clusters()
    resp.should.contain("clusterArns")
    len(resp["clusterArns"]).should.equal(1)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    resp.should.contain("computeEnvironmentArn")
    resp["computeEnvironmentName"].should.equal(compute_name)

    # Its unmanaged so no instances should be created
    resp = ec2_client.describe_instances()
    resp.should.contain("Reservations")
    len(resp["Reservations"]).should.equal(0)

    # Should have created 1 ECS cluster
    resp = ecs_client.list_clusters()
    resp.should.contain("clusterArns")
    len(resp["clusterArns"]).should.equal(1)


# TODO create 1000s of tests to test complex option combinations of create environment


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    resp = batch_client.describe_compute_environments()
    len(resp["computeEnvironments"]).should.equal(1)
    resp["computeEnvironments"][0]["computeEnvironmentName"].should.equal(compute_name)

    # Test filtering
    resp = batch_client.describe_compute_environments(computeEnvironments=["test1"])
    len(resp["computeEnvironments"]).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    batch_client.delete_compute_environment(computeEnvironment=compute_name)

    resp = batch_client.describe_compute_environments()
    len(resp["computeEnvironments"]).should.equal(0)

    resp = ecs_client.list_clusters()
    len(resp.get("clusterArns", [])).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_managed_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="MANAGED",
        state="ENABLED",
        computeResources={
            "type": "EC2",
            "minvCpus": 5,
            "maxvCpus": 10,
            "desiredvCpus": 5,
            "instanceTypes": ["t2.small", "t2.medium"],
            "imageId": "some_image_id",
            "subnets": [subnet_id],
            "securityGroupIds": [sg_id],
            "ec2KeyPair": "string",
            "instanceRole": iam_arn.replace("role", "instance-profile"),
            "tags": {"string": "string"},
            "bidPercentage": 123,
            "spotIamFleetRole": "string",
        },
        serviceRole=iam_arn,
    )

    batch_client.delete_compute_environment(computeEnvironment=compute_name)

    resp = batch_client.describe_compute_environments()
    len(resp["computeEnvironments"]).should.equal(0)

    resp = ec2_client.describe_instances()
    resp.should.contain("Reservations")
    len(resp["Reservations"]).should.equal(3)
    for reservation in resp["Reservations"]:
        reservation["Instances"][0]["State"]["Name"].should.equal("terminated")

    resp = ecs_client.list_clusters()
    len(resp.get("clusterArns", [])).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_update_unmanaged_compute_environment_state():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = "test_compute_env"
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    batch_client.update_compute_environment(
        computeEnvironment=compute_name, state="DISABLED"
    )

    resp = batch_client.describe_compute_environments()
    len(resp["computeEnvironments"]).should.equal(1)
    resp["computeEnvironments"][0]["state"].should.equal("DISABLED")


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


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_register_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp = batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 128,
            "command": ["sleep", "10"],
        },
    )

    resp.should.contain("jobDefinitionArn")
    resp.should.contain("jobDefinitionName")
    resp.should.contain("revision")

    assert resp["jobDefinitionArn"].endswith(
        "{0}:{1}".format(resp["jobDefinitionName"], resp["revision"])
    )


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_reregister_task_definition():
    # Reregistering task with the same name bumps the revision number
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp1 = batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 128,
            "command": ["sleep", "10"],
        },
    )

    resp1.should.contain("jobDefinitionArn")
    resp1.should.contain("jobDefinitionName")
    resp1.should.contain("revision")

    assert resp1["jobDefinitionArn"].endswith(
        "{0}:{1}".format(resp1["jobDefinitionName"], resp1["revision"])
    )
    resp1["revision"].should.equal(1)

    resp2 = batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 68,
            "command": ["sleep", "10"],
        },
    )
    resp2["revision"].should.equal(2)

    resp2["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])

    resp3 = batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 42,
            "command": ["sleep", "10"],
        },
    )
    resp3["revision"].should.equal(3)

    resp3["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])
    resp3["jobDefinitionArn"].should_not.equal(resp2["jobDefinitionArn"])

    resp4 = batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 41,
            "command": ["sleep", "10"],
        },
    )
    resp4["revision"].should.equal(4)

    resp4["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])
    resp4["jobDefinitionArn"].should_not.equal(resp2["jobDefinitionArn"])
    resp4["jobDefinitionArn"].should_not.equal(resp3["jobDefinitionArn"])


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp = batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 128,
            "command": ["sleep", "10"],
        },
    )

    batch_client.deregister_job_definition(jobDefinition=resp["jobDefinitionArn"])

    resp = batch_client.describe_job_definitions()
    len(resp["jobDefinitions"]).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 128,
            "command": ["sleep", "10"],
        },
    )
    batch_client.register_job_definition(
        jobDefinitionName="sleep10",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 64,
            "command": ["sleep", "10"],
        },
    )
    batch_client.register_job_definition(
        jobDefinitionName="test1",
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 64,
            "command": ["sleep", "10"],
        },
    )

    resp = batch_client.describe_job_definitions(jobDefinitionName="sleep10")
    len(resp["jobDefinitions"]).should.equal(2)

    resp = batch_client.describe_job_definitions()
    len(resp["jobDefinitions"]).should.equal(3)

    resp = batch_client.describe_job_definitions(jobDefinitions=["sleep10", "test1"])
    len(resp["jobDefinitions"]).should.equal(3)

    for job_definition in resp["jobDefinitions"]:
        job_definition["status"].should.equal("ACTIVE")


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
    job_def_arn = resp["jobDefinitionArn"]

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id = resp["jobId"]

    _wait_for_job_status(batch_client, job_id, "SUCCEEDED")

    resp = logs_client.describe_log_streams(
        logGroupName="/aws/batch/job", logStreamNamePrefix="sayhellotomylittlefriend"
    )
    len(resp["logStreams"]).should.equal(1)
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
        jobDefinitionName="sleep5",
        type="container",
        containerProperties={
            "image": "busybox:latest",
            "vcpus": 1,
            "memory": 128,
            "command": ["sleep", "5"],
        },
    )
    job_def_arn = resp["jobDefinitionArn"]

    resp = batch_client.submit_job(
        jobName="test1", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id1 = resp["jobId"]
    resp = batch_client.submit_job(
        jobName="test2", jobQueue=queue_arn, jobDefinition=job_def_arn
    )
    job_id2 = resp["jobId"]

    resp_finished_jobs = batch_client.list_jobs(
        jobQueue=queue_arn, jobStatus="SUCCEEDED"
    )

    # Wait only as long as it takes to run the jobs
    for job_id in [job_id1, job_id2]:
        _wait_for_job_status(batch_client, job_id, "SUCCEEDED")

    resp_finished_jobs2 = batch_client.list_jobs(
        jobQueue=queue_arn, jobStatus="SUCCEEDED"
    )

    len(resp_finished_jobs["jobSummaryList"]).should.equal(0)
    len(resp_finished_jobs2["jobSummaryList"]).should.equal(2)


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_terminate_job():
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
        jobDefinitionName="echo-sleep-echo",
        type="container",
        containerProperties={
            "image": "busybox:latest",
            "vcpus": 1,
            "memory": 128,
            "command": ["sh", "-c", "echo start && sleep 30 && echo stop"],
        },
    )
    job_def_arn = resp["jobDefinitionArn"]

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
        logGroupName="/aws/batch/job", logStreamNamePrefix="echo-sleep-echo"
    )
    len(resp["logStreams"]).should.equal(1)
    ls_name = resp["logStreams"][0]["logStreamName"]

    resp = logs_client.get_log_events(
        logGroupName="/aws/batch/job", logStreamName=ls_name
    )
    # Events should only contain 'start' because we interrupted
    # the job before 'stop' was written to the logs.
    resp["events"].should.have.length_of(1)
    resp["events"][0]["message"].should.equal("start")


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
            "command": ["exit", "1"],
        },
    )
    job_def_arn = resp["jobDefinitionArn"]

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
    job_def_arn = resp["jobDefinitionArn"]

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
