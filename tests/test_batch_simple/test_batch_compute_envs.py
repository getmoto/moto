from ..test_batch import _get_clients, _setup
import sure  # noqa # pylint: disable=unused-import
from moto import mock_batch_simple, mock_iam, mock_ec2, mock_ecs, settings
from uuid import uuid4


# Copy of test_batch/test_batch_cloudformation
# Except that we verify this behaviour still works without docker


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch_simple
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
@mock_batch_simple
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
    our_env["computeResources"]["instanceTypes"].should.equal(["t2"])
