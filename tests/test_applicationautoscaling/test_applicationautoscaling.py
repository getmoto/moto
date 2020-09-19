from __future__ import unicode_literals
import boto3
from moto import mock_applicationautoscaling, mock_ecs
import sure  # noqa
from nose.tools import with_setup

DEFAULT_REGION = "us-east-1"
DEFAULT_ECS_CLUSTER = "default"
DEFAULT_ECS_TASK = "test_ecs_task"
DEFAULT_ECS_SERVICE = "sample-webapp"
DEFAULT_SERVICE_NAMESPACE = "ecs"
DEFAULT_RESOURCE_ID = "service/{}/{}".format(DEFAULT_ECS_CLUSTER, DEFAULT_ECS_SERVICE)
DEFAULT_SCALABLE_DIMENSION = "ecs:service:DesiredCount"
DEFAULT_MIN_CAPACITY = 1
DEFAULT_MAX_CAPACITY = 1
DEFAULT_ROLE_ARN = "test:arn"
DEFAULT_SUSPENDED_STATE = {
    "DynamicScalingInSuspended": True,
    "DynamicScalingOutSuspended": True,
    "ScheduledScalingSuspended": True,
}


def _create_ecs_defaults(ecs, create_service=True):
    _ = ecs.create_cluster(clusterName=DEFAULT_ECS_CLUSTER)
    _ = ecs.register_task_definition(
        family=DEFAULT_ECS_TASK,
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )
    if create_service:
        _ = ecs.create_service(
            cluster=DEFAULT_ECS_CLUSTER,
            serviceName=DEFAULT_ECS_SERVICE,
            taskDefinition=DEFAULT_ECS_TASK,
            desiredCount=2,
        )


@mock_ecs
@mock_applicationautoscaling
def test_describe_scalable_targets_one_basic_ecs_success():
    ecs = boto3.client("ecs", region_name=DEFAULT_REGION)
    _create_ecs_defaults(ecs)
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    client.register_scalable_target(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE,
        ResourceId=DEFAULT_RESOURCE_ID,
        ScalableDimension=DEFAULT_SCALABLE_DIMENSION,
    )
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(1)
    t = response["ScalableTargets"][0]
    t.should.have.key("ServiceNamespace").which.should.equal(DEFAULT_SERVICE_NAMESPACE)
    t.should.have.key("ResourceId").which.should.equal(DEFAULT_RESOURCE_ID)
    t.should.have.key("ScalableDimension").which.should.equal(
        DEFAULT_SCALABLE_DIMENSION
    )
    t.should.have.key("CreationTime").which.should.be.a("datetime.datetime")


@mock_ecs
@mock_applicationautoscaling
def test_describe_scalable_targets_one_full_ecs_success():
    ecs = boto3.client("ecs", region_name=DEFAULT_REGION)
    _create_ecs_defaults(ecs)
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    register_scalable_target(client)
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(1)
    t = response["ScalableTargets"][0]
    t.should.have.key("ServiceNamespace").which.should.equal(DEFAULT_SERVICE_NAMESPACE)
    t.should.have.key("ResourceId").which.should.equal(DEFAULT_RESOURCE_ID)
    t.should.have.key("ScalableDimension").which.should.equal(
        DEFAULT_SCALABLE_DIMENSION
    )
    t.should.have.key("MinCapacity").which.should.equal(DEFAULT_MIN_CAPACITY)
    t.should.have.key("MaxCapacity").which.should.equal(DEFAULT_MAX_CAPACITY)
    t.should.have.key("RoleARN").which.should.equal(DEFAULT_ROLE_ARN)
    t.should.have.key("CreationTime").which.should.be.a("datetime.datetime")
    t.should.have.key("SuspendedState")
    t["SuspendedState"]["DynamicScalingInSuspended"].should.equal(
        DEFAULT_SUSPENDED_STATE["DynamicScalingInSuspended"]
    )


@mock_ecs
@mock_applicationautoscaling
def test_describe_scalable_targets_only_return_ecs_targets():
    ecs = boto3.client("ecs", region_name=DEFAULT_REGION)
    _create_ecs_defaults(ecs, create_service=False)
    _ = ecs.create_service(
        cluster=DEFAULT_ECS_CLUSTER,
        serviceName="test1",
        taskDefinition=DEFAULT_ECS_TASK,
        desiredCount=2,
    )
    _ = ecs.create_service(
        cluster=DEFAULT_ECS_CLUSTER,
        serviceName="test2",
        taskDefinition=DEFAULT_ECS_TASK,
        desiredCount=2,
    )
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    register_scalable_target(
        client,
        ServiceNamespace="ecs",
        ResourceId="service/{}/test1".format(DEFAULT_ECS_CLUSTER),
    )
    register_scalable_target(
        client,
        ServiceNamespace="ecs",
        ResourceId="service/{}/test2".format(DEFAULT_ECS_CLUSTER),
    )
    register_scalable_target(
        client,
        ServiceNamespace="elasticmapreduce",
        ResourceId="instancegroup/j-2EEZNYKUA1NTV/ig-1791Y4E1L8YI0",
        ScalableDimension="elasticmapreduce:instancegroup:InstanceCount",
    )
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(2)


@mock_ecs
@mock_applicationautoscaling
def test_describe_scalable_targets_next_token_success():
    ecs = boto3.client("ecs", region_name=DEFAULT_REGION)
    _create_ecs_defaults(ecs, create_service=False)
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    for i in range(0, 100):
        _ = ecs.create_service(
            cluster=DEFAULT_ECS_CLUSTER,
            serviceName=str(i),
            taskDefinition=DEFAULT_ECS_TASK,
            desiredCount=2,
        )
        register_scalable_target(
            client,
            ServiceNamespace="ecs",
            ResourceId="service/{}/{}".format(DEFAULT_ECS_CLUSTER, i),
        )
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(50)
    response["ScalableTargets"][0]["ResourceId"].should.equal("service/default/0")
    response.should.have.key("NextToken").which.should.equal("49")
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE, NextToken=str(response["NextToken"])
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(50)
    response["ScalableTargets"][0]["ResourceId"].should.equal("service/default/50")
    response.should_not.have.key("NextToken")


def register_scalable_target(client, **kwargs):
    """ Build a default scalable target object for use in tests. """
    return client.register_scalable_target(
        ServiceNamespace=kwargs.get("ServiceNamespace", DEFAULT_SERVICE_NAMESPACE),
        ResourceId=kwargs.get("ResourceId", DEFAULT_RESOURCE_ID),
        ScalableDimension=kwargs.get("ScalableDimension", DEFAULT_SCALABLE_DIMENSION),
        MinCapacity=kwargs.get("MinCapacity", DEFAULT_MIN_CAPACITY),
        MaxCapacity=kwargs.get("MaxCapacity", DEFAULT_MAX_CAPACITY),
        RoleARN=kwargs.get("RoleARN", DEFAULT_ROLE_ARN),
        SuspendedState=kwargs.get("SuspendedState", DEFAULT_SUSPENDED_STATE),
    )


@mock_ecs
@mock_applicationautoscaling
def test_register_scalable_target_resource_id_variations():

    # Required to register an ECS target in moto
    ecs = boto3.client("ecs", region_name=DEFAULT_REGION)
    _create_ecs_defaults(ecs)

    # See https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationautoscaling-scalabletarget.html
    resource_id_variations = [
        (
            DEFAULT_SERVICE_NAMESPACE,
            DEFAULT_RESOURCE_ID,
            DEFAULT_SCALABLE_DIMENSION,
        ),  # ECS
        (
            "ec2",
            "spot-fleet-request/sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE",
            "ec2:spot-fleet-request:TargetCapacity",
        ),
        (
            "elasticmapreduce",
            "instancegroup/j-2EEZNYKUA1NTV/ig-1791Y4E1L8YI0",
            "elasticmapreduce:instancegroup:InstanceCount",
        ),
        ("appstream", "fleet/sample-fleet", "appstream:fleet:DesiredCapacity"),
        ("dynamodb", "table/my-table", "dynamodb:table:ReadCapacityUnits"),
        (
            "dynamodb",
            "table/my-table/index/my-table-index",
            "dynamodb:index:ReadCapacityUnits",
        ),
        ("rds", "cluster:my-db-cluster", "rds:cluster:ReadReplicaCount"),
        (
            "sagemaker",
            "endpoint/MyEndPoint/variant/MyVariant",
            "sagemaker:variant:DesiredInstanceCount",
        ),
        (
            "comprehend",
            "arn:aws:comprehend:us-west-2:123456789012:document-classifier-endpoint/EXAMPLE",
            "comprehend:document-classifier-endpoint:DesiredInferenceUnits",
        ),
        (
            "lambda",
            "function:my-function:prod",
            "lambda:function:ProvisionedConcurrency",
        ),
        (
            "cassandra",
            "keyspace/mykeyspace/table/mytable",
            "cassandra:table:ReadCapacityUnits",
        ),
    ]

    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    for namespace, resource_id, scalable_dimension in resource_id_variations:
        client.register_scalable_target(
            ServiceNamespace=namespace,
            ResourceId=resource_id,
            ScalableDimension=scalable_dimension,
        )
        response = client.describe_scalable_targets(ServiceNamespace=namespace)
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
        num_targets = 2 if namespace == "dynamodb" and "index" in resource_id else 1
        len(response["ScalableTargets"]).should.equal(num_targets)
        t = response["ScalableTargets"][-1]
        t.should.have.key("ServiceNamespace").which.should.equal(namespace)
        t.should.have.key("ResourceId").which.should.equal(resource_id)
        t.should.have.key("ScalableDimension").which.should.equal(scalable_dimension)
        t.should.have.key("CreationTime").which.should.be.a("datetime.datetime")
