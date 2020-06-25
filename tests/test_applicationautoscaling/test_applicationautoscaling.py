from __future__ import unicode_literals
import boto3
from moto import mock_applicationautoscaling
from botocore.exceptions import ParamValidationError
from boto.exception import JSONResponseError
from nose.tools import assert_raises
import sure  # noqa
from botocore.exceptions import ClientError


DEFAULT_REGION = "us-east-1"
DEFAULT_SERVICE_NAMESPACE = "ecs"
DEFAULT_RESOURCE_ID = "service/default/sample-webapp"
DEFAULT_SCALABLE_DIMENSION = "ecs:service:DesiredCount"
DEFAULT_MIN_CAPACITY = 1
DEFAULT_MAX_CAPACITY = 1
DEFAULT_ROLE_ARN = "test:arn"


@mock_applicationautoscaling
def test_describe_scalable_targets_one_ecs_success():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    __register_scalable_target(client)
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


# TODO Add a test for NextToken


@mock_applicationautoscaling
def test_describe_scalable_targets_only_return_ecs_targets():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    __register_scalable_target(client, ServiceNamespace="ecs", ResourceId="test1")
    __register_scalable_target(client, ServiceNamespace="ecs", ResourceId="test2")
    __register_scalable_target(
        client, ServiceNamespace="elasticmapreduce", ResourceId="test3"
    )
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(2)


def __register_scalable_target(client, **kwargs):
    """ Build a default scalable target object for use in tests. """
    return client.register_scalable_target(
        ServiceNamespace=kwargs.get("ServiceNamespace", DEFAULT_SERVICE_NAMESPACE),
        ResourceId=kwargs.get("ResourceId", DEFAULT_RESOURCE_ID),
        ScalableDimension=kwargs.get("ScalableDimension", DEFAULT_SCALABLE_DIMENSION),
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


@mock_applicationautoscaling
def test_next_token_success():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    for i in range(0, 100):
        __register_scalable_target(client, ServiceNamespace="ecs", ResourceId=str(i))
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(50)
    response["ScalableTargets"][0]["ResourceId"].should.equal("0")
    response["NextToken"].should.equal("49")
    response = client.describe_scalable_targets(
        ServiceNamespace=DEFAULT_SERVICE_NAMESPACE, NextToken=str(response["NextToken"])
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(response["ScalableTargets"]).should.equal(50)
    response["ScalableTargets"][0]["ResourceId"].should.equal("50")
    response.should_not.have.key("NextToken")


@mock_applicationautoscaling
def test_describe_scalable_targets_no_params_should_raise_param_validation_errors():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    with assert_raises(ParamValidationError):
        client.describe_scalable_targets()


@mock_applicationautoscaling
def test_register_scalable_target_no_params_should_raise_param_validation_errors():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    with assert_raises(ParamValidationError):
        client.register_scalable_target()


@mock_applicationautoscaling
def test_register_scalable_target_with_none_service_namespace_should_raise_param_validation_errors():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)
    with assert_raises(ParamValidationError):
        __register_scalable_target(client, ServiceNamespace=None)


@mock_applicationautoscaling
def test_describe_scalable_targets_with_invalid_scalable_dimension_should_return_validation_exception():
    client = boto3.client("application-autoscaling", region_name=DEFAULT_REGION)

    try:
        response = client.describe_scalable_targets(
            ServiceNamespace=DEFAULT_SERVICE_NAMESPACE, ScalableDimension="foo",
        )
        print(response)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ValidationException")
        err.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    else:
        raise RuntimeError("Should have raised ValidationException")
