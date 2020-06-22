from __future__ import unicode_literals
import boto3
from moto import mock_applicationautoscaling
import sure  # noqa

DEFAULT_REGION = "us-east-1"
DEFAULT_SERVICE_NAMESPACE = "ecs"
DEFAULT_RESOURCE_ID = "test"
DEFAULT_SCALABLE_DIMENSION = "ecs:service:DesiredCount"
DEFAULT_MIN_CAPACITY = 1
DEFAULT_MAX_CAPACITY = 1
DEFAULT_ROLE_ARN = "test:arn"


@mock_applicationautoscaling
def test_describe_scalable_targets_one_ecs_success():
    __register_default_scalable_target()
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    response = client.describe_scalable_targets(ServiceNamespace=DEFAULT_SERVICE_NAMESPACE)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(1)
    t = response["ScalableTargets"][0]
    t.should.have.key("ServiceNamespace").which.should.equal(DEFAULT_SERVICE_NAMESPACE)
    t.should.have.key("ResourceId").which.should.equal(DEFAULT_RESOURCE_ID)
    t.should.have.key("ScalableDimension").which.should.equal(DEFAULT_SCALABLE_DIMENSION)
    t.should.have.key("MinCapacity").which.should.equal(DEFAULT_MIN_CAPACITY)
    t.should.have.key("MaxCapacity").which.should.equal(DEFAULT_MAX_CAPACITY)
    t.should.have.key("RoleARN").which.should.equal(DEFAULT_ROLE_ARN)


@mock_applicationautoscaling
def __register_default_scalable_target():
    """ Build a default scalable target object for use in tests. """
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    client.register_scalable_target(
        ServiceNamespace="ecs",
        ResourceId="test",
        ScalableDimension="ecs:service:DesiredCount",
        MinCapacity=1,
        MaxCapacity=1,
        RoleARN="test:arn",
        # TODO Implement SuspendedState
        # SuspendedState={
        #     "DynamicScalingInSuspended": True,
        #     "DynamicScalingOutSuspended": True,
        #     "ScheduledScalingSuspended": True,
        # }
    )
