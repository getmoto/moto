import re

import boto3
import pytest
from moto import mock_applicationautoscaling, mock_ecs
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

DEFAULT_REGION = "us-east-1"
DEFAULT_ECS_CLUSTER = "default"
DEFAULT_ECS_TASK = "test_ecs_task"
DEFAULT_ECS_SERVICE = "sample-webapp"
DEFAULT_SERVICE_NAMESPACE = "ecs"
DEFAULT_RESOURCE_ID = f"service/{DEFAULT_ECS_CLUSTER}/{DEFAULT_ECS_SERVICE}"
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["ScalableTargets"]) == 1
    t = response["ScalableTargets"][0]
    assert t["ServiceNamespace"] == DEFAULT_SERVICE_NAMESPACE
    assert t["ResourceId"] == DEFAULT_RESOURCE_ID
    assert t["ScalableDimension"] == DEFAULT_SCALABLE_DIMENSION
    assert "CreationTime" in t


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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["ScalableTargets"]) == 1
    t = response["ScalableTargets"][0]
    assert t["ServiceNamespace"] == DEFAULT_SERVICE_NAMESPACE
    assert t["ResourceId"] == DEFAULT_RESOURCE_ID
    assert t["ScalableDimension"] == DEFAULT_SCALABLE_DIMENSION
    assert t["MinCapacity"] == DEFAULT_MIN_CAPACITY
    assert t["MaxCapacity"] == DEFAULT_MAX_CAPACITY
    assert t["RoleARN"] == DEFAULT_ROLE_ARN
    assert "CreationTime" in t
    assert (
        t["SuspendedState"]["DynamicScalingInSuspended"]
        == DEFAULT_SUSPENDED_STATE["DynamicScalingInSuspended"]
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
        ResourceId=f"service/{DEFAULT_ECS_CLUSTER}/test1",
    )
    register_scalable_target(
        client,
        ServiceNamespace="ecs",
        ResourceId=f"service/{DEFAULT_ECS_CLUSTER}/test2",
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["ScalableTargets"]) == 2


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
            ResourceId=f"service/{DEFAULT_ECS_CLUSTER}/{i}",
        )
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["ScalableTargets"]) == 50
    assert response["ScalableTargets"][0]["ResourceId"] == "service/default/0"
    assert response["NextToken"] == "49"
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE, NextToken=str(response["NextToken"])
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["ScalableTargets"]) == 50
    assert response["ScalableTargets"][0]["ResourceId"] == "service/default/50"
    assert "NextToken" not in response


def register_scalable_target(client, **kwargs):
    """Build a default scalable target object for use in tests."""
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
        (
            "custom-resource",
            "https://test-endpoint.amazon.com/ScalableDimension/test-resource",
            "custom-resource:ResourceType:Property",
        ),
    ]

    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    for namespace, resource_id, scalable_dimension in resource_id_variations:
        client.register_scalable_target(
            ServiceNamespace=namespace,
            ResourceId=resource_id,
            ScalableDimension=scalable_dimension,
            MinCapacity=1,
            MaxCapacity=8,
        )
        response = client.describe_scalable_targets(ServiceNamespace=namespace)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        num_targets = 2 if namespace == "dynamodb" and "index" in resource_id else 1
        assert len(response["ScalableTargets"]) == num_targets
        t = response["ScalableTargets"][-1]
        assert t["ServiceNamespace"] == namespace
        assert t["ResourceId"] == resource_id
        assert t["ScalableDimension"] == scalable_dimension
        assert "CreationTime" in t


@mock_ecs
@mock_applicationautoscaling
def test_register_scalable_target_updates_existing_target():
    ecs = boto3.client("ecs", region_name=DEFAULT_REGION)
    _create_ecs_defaults(ecs)
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    register_scalable_target(client)

    updated_min_capacity = 3
    updated_max_capacity = 10
    updated_suspended_state = {
        "DynamicScalingInSuspended": False,
        "DynamicScalingOutSuspended": False,
        "ScheduledScalingSuspended": False,
    }

    client.register_scalable_target(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE,
        ResourceId=DEFAULT_RESOURCE_ID,
        ScalableDimension=DEFAULT_SCALABLE_DIMENSION,
        MinCapacity=updated_min_capacity,
        MaxCapacity=updated_max_capacity,
        SuspendedState=updated_suspended_state,
    )
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )

    assert len(response["ScalableTargets"]) == 1
    t = response["ScalableTargets"][0]
    assert t["MinCapacity"] == updated_min_capacity
    assert t["MaxCapacity"] == updated_max_capacity
    assert (
        t["SuspendedState"]["DynamicScalingInSuspended"]
        == updated_suspended_state["DynamicScalingInSuspended"]
    )
    assert (
        t["SuspendedState"]["DynamicScalingOutSuspended"]
        == updated_suspended_state["DynamicScalingOutSuspended"]
    )
    assert (
        t["SuspendedState"]["ScheduledScalingSuspended"]
        == updated_suspended_state["ScheduledScalingSuspended"]
    )


@pytest.mark.parametrize(
    ["policy_type", "policy_body_kwargs"],
    [
        [
            "TargetTrackingScaling",
            {
                "TargetTrackingScalingPolicyConfiguration": {
                    "TargetValue": 70.0,
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
                    },
                }
            },
        ],
        [
            "TargetTrackingScaling",
            {
                "StepScalingPolicyConfiguration": {
                    "AdjustmentType": "ChangeCapacity",
                    "StepAdjustments": [{"ScalingAdjustment": 10}],
                    "MinAdjustmentMagnitude": 2,
                },
            },
        ],
    ],
)
@mock_applicationautoscaling
def test_put_scaling_policy(policy_type, policy_body_kwargs):
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    namespace = "sagemaker"
    resource_id = "endpoint/MyEndPoint/variant/MyVariant"
    scalable_dimension = "sagemaker:variant:DesiredInstanceCount"

    client.register_scalable_target(
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        MinCapacity=1,
        MaxCapacity=8,
    )

    policy_name = "MyPolicy"

    with pytest.raises(client.exceptions.ValidationException) as e:
        client.put_scaling_policy(
            PolicyName=policy_name,
            ServiceNamespace=namespace,
            ResourceId=resource_id,
            ScalableDimension=scalable_dimension,
            PolicyType="ABCDEFG",
            **policy_body_kwargs,
        )
    assert (
        e.value.response["Error"]["Message"] == "Unknown policy type ABCDEFG specified."
    )

    response = client.put_scaling_policy(
        PolicyName=policy_name,
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        PolicyType=policy_type,
        **policy_body_kwargs,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert (
        re.match(
            pattern=rf"arn:aws:autoscaling:{DEFAULT_REGION}:{ACCOUNT_ID}:scalingPolicy:.*:resource/{namespace}/{resource_id}:policyName/{policy_name}",
            string=response["PolicyARN"],
        )
        is not None
    )


@mock_applicationautoscaling
def test_describe_scaling_policies():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    namespace = "sagemaker"
    resource_id = "endpoint/MyEndPoint/variant/MyVariant"
    scalable_dimension = "sagemaker:variant:DesiredInstanceCount"

    client.register_scalable_target(
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        MinCapacity=1,
        MaxCapacity=8,
    )

    policy_name = "MyPolicy"
    policy_type = "TargetTrackingScaling"
    policy_body = {
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
        },
    }

    response = client.put_scaling_policy(
        PolicyName=policy_name,
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        PolicyType=policy_type,
        TargetTrackingScalingPolicyConfiguration=policy_body,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.describe_scaling_policies(
        PolicyNames=[policy_name],
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    policy = response["ScalingPolicies"][0]
    assert policy["PolicyName"] == policy_name
    assert policy["ServiceNamespace"] == namespace
    assert policy["ResourceId"] == resource_id
    assert policy["ScalableDimension"] == scalable_dimension
    assert policy["PolicyType"] == policy_type
    assert policy["TargetTrackingScalingPolicyConfiguration"] == policy_body
    assert (
        re.match(
            pattern=rf"arn:aws:autoscaling:{DEFAULT_REGION}:{ACCOUNT_ID}:scalingPolicy:.*:resource/{namespace}/{resource_id}:policyName/{policy_name}",
            string=policy["PolicyARN"],
        )
        is not None
    )
    assert "CreationTime" in policy


@mock_applicationautoscaling
def test_delete_scaling_policies():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    namespace = "sagemaker"
    resource_id = "endpoint/MyEndPoint/variant/MyVariant"
    scalable_dimension = "sagemaker:variant:DesiredInstanceCount"

    client.register_scalable_target(
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        MinCapacity=1,
        MaxCapacity=8,
    )

    policy_name = "MyPolicy"
    policy_type = "TargetTrackingScaling"
    policy_body = {
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
        },
    }

    with pytest.raises(client.exceptions.ValidationException) as e:
        client.delete_scaling_policy(
            PolicyName=policy_name,
            ServiceNamespace=namespace,
            ResourceId=resource_id,
            ScalableDimension=scalable_dimension,
        )
    assert "No scaling policy found" in e.value.response["Error"]["Message"]

    response = client.put_scaling_policy(
        PolicyName=policy_name,
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        PolicyType=policy_type,
        TargetTrackingScalingPolicyConfiguration=policy_body,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.delete_scaling_policy(
        PolicyName=policy_name,
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.describe_scaling_policies(
        PolicyNames=[policy_name],
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["ScalingPolicies"]) == 0


@mock_applicationautoscaling
def test_deregister_scalable_target():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    namespace = "sagemaker"
    resource_id = "endpoint/MyEndPoint/variant/MyVariant"
    scalable_dimension = "sagemaker:variant:DesiredInstanceCount"

    client.register_scalable_target(
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
        MinCapacity=1,
        MaxCapacity=8,
    )

    response = client.describe_scalable_targets(ServiceNamespace=namespace)
    assert len(response["ScalableTargets"]) == 1

    client.deregister_scalable_target(
        ServiceNamespace=namespace,
        ResourceId=resource_id,
        ScalableDimension=scalable_dimension,
    )

    response = client.describe_scalable_targets(ServiceNamespace=namespace)
    assert len(response["ScalableTargets"]) == 0

    with pytest.raises(client.exceptions.ValidationException) as e:
        client.deregister_scalable_target(
            ServiceNamespace=namespace,
            ResourceId=resource_id,
            ScalableDimension=scalable_dimension,
        )
    assert "No scalable target found" in e.value.response["Error"]["Message"]


@mock_applicationautoscaling
def test_delete_scheduled_action():
    client = boto3.client("application-autoscaling", region_name="eu-west-1")
    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 0

    for i in range(3):
        client.put_scheduled_action(
            ServiceNamespace="ecs",
            ScheduledActionName=f"ecs_action_{i}",
            ResourceId=f"ecs:cluster:{i}",
            ScalableDimension="ecs:service:DesiredCount",
        )

    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 3

    client.delete_scheduled_action(
        ServiceNamespace="ecs",
        ScheduledActionName="ecs_action_0",
        ResourceId="ecs:cluster:0",
        ScalableDimension="ecs:service:DesiredCount",
    )

    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 2


@mock_applicationautoscaling
def test_describe_scheduled_actions():
    client = boto3.client("application-autoscaling", region_name="eu-west-1")
    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 0

    for i in range(3):
        client.put_scheduled_action(
            ServiceNamespace="ecs",
            ScheduledActionName=f"ecs_action_{i}",
            ResourceId=f"ecs:cluster:{i}",
            ScalableDimension="ecs:service:DesiredCount",
        )
        client.put_scheduled_action(
            ServiceNamespace="dynamodb",
            ScheduledActionName=f"ddb_action_{i}",
            ResourceId=f"table/table_{i}",
            ScalableDimension="dynamodb:table:ReadCapacityUnits",
        )

    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 3

    resp = client.describe_scheduled_actions(ServiceNamespace="ec2")
    assert len(resp["ScheduledActions"]) == 0

    resp = client.describe_scheduled_actions(
        ServiceNamespace="dynamodb", ScheduledActionNames=["ddb_action_0"]
    )
    assert len(resp["ScheduledActions"]) == 1

    resp = client.describe_scheduled_actions(
        ServiceNamespace="dynamodb",
        ResourceId="table/table_0",
        ScalableDimension="dynamodb:table:ReadCapacityUnits",
    )
    assert len(resp["ScheduledActions"]) == 1

    resp = client.describe_scheduled_actions(
        ServiceNamespace="dynamodb",
        ResourceId="table/table_0",
        ScalableDimension="dynamodb:table:WriteCapacityUnits",
    )
    assert len(resp["ScheduledActions"]) == 0


@mock_applicationautoscaling
def test_put_scheduled_action():
    client = boto3.client("application-autoscaling", region_name="ap-southeast-1")
    client.put_scheduled_action(
        ServiceNamespace="ecs",
        ScheduledActionName="action_name",
        ResourceId="ecs:cluster:x",
        ScalableDimension="ecs:service:DesiredCount",
    )

    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 1

    action = resp["ScheduledActions"][0]
    assert action["ScheduledActionName"] == "action_name"
    assert (
        action["ScheduledActionARN"]
        == f"arn:aws:autoscaling:ap-southeast-1:{ACCOUNT_ID}:scheduledAction:ecs:scheduledActionName/action_name"
    )
    assert action["ServiceNamespace"] == "ecs"
    assert action["ResourceId"] == "ecs:cluster:x"
    assert action["ScalableDimension"] == "ecs:service:DesiredCount"
    assert "CreationTime" in action
    assert "ScalableTargetAction" not in action


@mock_applicationautoscaling
def test_put_scheduled_action__use_update():
    client = boto3.client("application-autoscaling", region_name="ap-southeast-1")
    client.put_scheduled_action(
        ServiceNamespace="ecs",
        ScheduledActionName="action_name",
        ResourceId="ecs:cluster:x",
        ScalableDimension="ecs:service:DesiredCount",
    )
    client.put_scheduled_action(
        ServiceNamespace="ecs",
        ScheduledActionName="action_name_updated",
        ResourceId="ecs:cluster:x",
        ScalableDimension="ecs:service:DesiredCount",
        ScalableTargetAction={
            "MinCapacity": 12,
            "MaxCapacity": 23,
        },
    )

    resp = client.describe_scheduled_actions(ServiceNamespace="ecs")
    assert len(resp["ScheduledActions"]) == 1

    action = resp["ScheduledActions"][0]
    assert action["ScheduledActionName"] == "action_name_updated"
    assert (
        action["ScheduledActionARN"]
        == f"arn:aws:autoscaling:ap-southeast-1:{ACCOUNT_ID}:scheduledAction:ecs:scheduledActionName/action_name"
    )
    assert action["ServiceNamespace"] == "ecs"
    assert action["ResourceId"] == "ecs:cluster:x"
    assert action["ScalableDimension"] == "ecs:service:DesiredCount"
    assert "CreationTime" in action
    assert action["ScalableTargetAction"] == {"MaxCapacity": 23, "MinCapacity": 12}
