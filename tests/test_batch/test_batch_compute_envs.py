from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings

from . import _get_clients, _setup


@mock_aws
def test_create_managed_compute_environment():
    ec2_client, iam_client, ecs_client, _, batch_client = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

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
    assert "computeEnvironmentArn" in resp
    assert resp["computeEnvironmentName"] == compute_name

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]

    # Given a t2.medium is 2 vcpu and t2.small is 1, therefore 2 mediums and 1 small should be created
    if not settings.TEST_SERVER_MODE:
        # Can't verify this in ServerMode, as other tests may have created instances
        resp = ec2_client.describe_instances()
        assert "Reservations" in resp
        assert len(resp["Reservations"]) == 3

    # Should have created 1 ECS cluster
    all_clusters = ecs_client.list_clusters()["clusterArns"]
    assert our_env["ecsClusterArn"] in all_clusters


@mock_aws
def test_create_managed_compute_environment_with_instance_family():
    """
    The InstanceType parameter can have multiple values:
    instance_type     t2.small
    instance_family   t2       <-- What we're testing here
    'optimal'
    unknown value
    """
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

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
            "instanceTypes": ["t2"],
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
    assert our_env["computeResources"]["instanceTypes"] == ["t2"]


@mock_aws
def test_create_managed_compute_environment_with_unknown_instance_type():
    """
    The InstanceType parameter can have multiple values:
    instance_type     t2.small
    instance_family   t2
    'optimal'
    unknown value              <-- What we're testing here
    """
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    with pytest.raises(ClientError) as exc:
        batch_client.create_compute_environment(
            computeEnvironmentName=compute_name,
            type="MANAGED",
            state="ENABLED",
            computeResources={
                "type": "EC2",
                "minvCpus": 5,
                "maxvCpus": 10,
                "desiredvCpus": 5,
                "instanceTypes": ["unknown"],
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
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Instance type unknown does not exist"


@mock_aws
def test_create_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    assert "computeEnvironmentArn" in resp
    assert resp["computeEnvironmentName"] == compute_name

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]
    assert "ecsClusterArn" in our_env

    # Its unmanaged so no instances should be created
    if not settings.TEST_SERVER_MODE:
        # Can't verify this in ServerMode, as other tests may have created instances
        resp = ec2_client.describe_instances()
        assert "Reservations" in resp
        assert len(resp["Reservations"]) == 0

    # Should have created 1 ECS cluster
    all_clusters = ecs_client.list_clusters()["clusterArns"]
    assert our_env["ecsClusterArn"] in all_clusters


# TODO create 1000s of tests to test complex option combinations of create environment


@mock_aws
def test_describe_compute_environment():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

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
    assert len(our_envs) == 1
    assert our_envs[0]["computeEnvironmentName"] == compute_name
    assert our_envs[0]["computeEnvironmentArn"] == compute_arn
    assert "ecsClusterArn" in our_envs[0]
    assert our_envs[0]["state"] == "ENABLED"
    assert our_envs[0]["status"] == "VALID"

    # Test filtering
    resp = batch_client.describe_compute_environments(computeEnvironments=["test1"])
    assert len(resp["computeEnvironments"]) == 0


@mock_aws
def test_delete_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

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
    assert compute_name not in all_names

    cluster = ecs_client.describe_clusters(clusters=[our_env["ecsClusterArn"]])[
        "clusters"
    ][0]
    assert cluster["status"] == "INACTIVE"


@mock_aws
def test_delete_managed_compute_environment():
    ec2_client, iam_client, ecs_client, _, batch_client = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

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
    assert compute_name not in all_names

    if not settings.TEST_SERVER_MODE:
        # Too many instances to know which one is ours in ServerMode
        resp = ec2_client.describe_instances()
        assert "Reservations" in resp
        assert len(resp["Reservations"]) == 3
        for reservation in resp["Reservations"]:
            assert reservation["Instances"][0]["State"]["Name"] == "terminated"

    cluster = ecs_client.describe_clusters(clusters=[our_env["ecsClusterArn"]])[
        "clusters"
    ][0]
    assert cluster["status"] == "INACTIVE"


@mock_aws
def test_update_unmanaged_compute_environment_state():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

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
    assert len(our_envs) == 1
    assert our_envs[0]["state"] == "DISABLED"


@mock_aws
def test_update_iam_role():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)
    iam_arn2 = iam_client.create_role(RoleName="r", AssumeRolePolicyDocument="sp")[
        "Role"
    ]["Arn"]

    compute_name = str(uuid4())
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )

    batch_client.update_compute_environment(
        computeEnvironment=compute_name, serviceRole=iam_arn2
    )

    all_envs = batch_client.describe_compute_environments()["computeEnvironments"]
    our_envs = [e for e in all_envs if e["computeEnvironmentName"] == compute_name]
    assert len(our_envs) == 1
    assert our_envs[0]["serviceRole"] == iam_arn2

    with pytest.raises(ClientError) as exc:
        batch_client.update_compute_environment(
            computeEnvironment=compute_name, serviceRole="unknown"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"


@pytest.mark.parametrize("compute_env_type", ["FARGATE", "FARGATE_SPOT"])
@mock_aws
def test_create_fargate_managed_compute_environment(compute_env_type):
    ec2_client, iam_client, ecs_client, _, batch_client = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="MANAGED",
        state="ENABLED",
        computeResources={
            "type": compute_env_type,
            "maxvCpus": 10,
            "subnets": [subnet_id],
            "securityGroupIds": [sg_id],
        },
        serviceRole=iam_arn,
    )
    assert "computeEnvironmentArn" in resp
    assert resp["computeEnvironmentName"] == compute_name

    our_env = batch_client.describe_compute_environments(
        computeEnvironments=[compute_name]
    )["computeEnvironments"][0]

    assert our_env["computeResources"]["type"] == compute_env_type
    # Should have created 1 ECS cluster
    all_clusters = ecs_client.list_clusters()["clusterArns"]
    assert our_env["ecsClusterArn"] in all_clusters


@mock_aws
def test_create_ec2_managed_compute_environment__without_required_params():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    env_name = "ec2-env"

    with pytest.raises(ClientError) as exc:
        batch_client.create_compute_environment(
            computeEnvironmentName=env_name,
            type="MANAGED",
            state="ENABLED",
            computeResources={"type": "EC2", "maxvCpus": 1, "subnets": [subnet_id]},
            serviceRole=iam_arn,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert (
        "Error executing request, Exception : Instance role is required."
        in err["Message"]
    )

    with pytest.raises(ClientError) as exc:
        batch_client.create_compute_environment(
            computeEnvironmentName=env_name,
            type="MANAGED",
            state="ENABLED",
            computeResources={
                "type": "EC2",
                "maxvCpus": 1,
                "subnets": [subnet_id],
                "instanceRole": iam_arn.replace("role", "instance-profile"),
            },
            serviceRole=iam_arn,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert (
        "Error executing request, Exception : Resource minvCpus is required."
        in err["Message"]
    )

    with pytest.raises(ClientError) as exc:
        batch_client.create_compute_environment(
            computeEnvironmentName=env_name,
            type="UNMANGED",
            state="ENABLED",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert (
        "Error executing request, Exception : ServiceRole is required.,"
        in err["Message"]
    )
