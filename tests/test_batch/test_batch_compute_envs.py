from __future__ import unicode_literals

from . import _get_clients, _setup
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs, settings
from uuid import uuid4


# Yes, yes it talks to all the things
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_managed_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
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

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]

    # Given a t2.medium is 2 vcpu and t2.small is 1, therefore 2 mediums and 1 small should be created
    if not settings.TEST_SERVER_MODE:
        # Can't verify this in ServerMode, as other tests may have created instances
        resp = ec2_client.describe_instances()
        resp.should.contain("Reservations")
        len(resp["Reservations"]).should.equal(3)

    # Should have created 1 ECS cluster
    all_clusters = ecs_client.list_clusters()["clusterArns"]
    all_clusters.should.contain(our_env["ecsClusterArn"])


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    resp.should.contain("computeEnvironmentArn")
    resp["computeEnvironmentName"].should.equal(compute_name)

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]
    our_env.should.have.key("ecsClusterArn")

    # Its unmanaged so no instances should be created
    if not settings.TEST_SERVER_MODE:
        # Can't verify this in ServerMode, as other tests may have created instances
        resp = ec2_client.describe_instances()
        resp.should.contain("Reservations")
        len(resp["Reservations"]).should.equal(0)

    # Should have created 1 ECS cluster
    all_clusters = ecs_client.list_clusters()["clusterArns"]
    all_clusters.should.contain(our_env["ecsClusterArn"])


# TODO create 1000s of tests to test complex option combinations of create environment


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    compute_arn = (
        f"arn:aws:batch:eu-central-1:123456789012:compute-environment/{compute_name}"
    )
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    all_envs = batch_client.describe_compute_environments()["computeEnvironments"]
    our_envs = [e for e in all_envs if e["computeEnvironmentName"] == compute_name]
    our_envs.should.have.length_of(1)
    our_envs[0]["computeEnvironmentName"].should.equal(compute_name)
    our_envs[0]["computeEnvironmentArn"].should.equal(compute_arn)
    our_envs[0].should.have.key("ecsClusterArn")
    our_envs[0].should.have.key("state").equal("ENABLED")
    our_envs[0].should.have.key("status").equal("VALID")

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

    compute_name = str(uuid4())
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]

    batch_client.delete_compute_environment(computeEnvironment=compute_name)

    all_envs = batch_client.describe_compute_environments()["computeEnvironments"]
    all_names = [e["computeEnvironmentName"] for e in all_envs]
    all_names.shouldnt.contain(compute_name)

    all_clusters = ecs_client.list_clusters()["clusterArns"]
    all_clusters.shouldnt.contain(our_env["ecsClusterArn"])


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_managed_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
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

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]

    batch_client.delete_compute_environment(computeEnvironment=compute_name)

    all_envs = batch_client.describe_compute_environments()["computeEnvironments"]
    all_names = [e["computeEnvironmentName"] for e in all_envs]
    all_names.shouldnt.contain(compute_name)

    if not settings.TEST_SERVER_MODE:
        # Too many instances to know which one is ours in ServerMode
        resp = ec2_client.describe_instances()
        resp.should.contain("Reservations")
        len(resp["Reservations"]).should.equal(3)
        for reservation in resp["Reservations"]:
            reservation["Instances"][0]["State"]["Name"].should.equal("terminated")

    all_clusters = ecs_client.list_clusters()["clusterArns"]
    all_clusters.shouldnt.contain(our_env["ecsClusterArn"])


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_update_unmanaged_compute_environment_state():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    batch_client.update_compute_environment(
        computeEnvironment=compute_name, state="DISABLED"
    )

    all_envs = batch_client.describe_compute_environments()["computeEnvironments"]
    our_envs = [e for e in all_envs if e["computeEnvironmentName"] == compute_name]
    our_envs.should.have.length_of(1)
    our_envs[0]["state"].should.equal("DISABLED")
