from __future__ import unicode_literals
import boto3
from moto import mock_applicationautoscaling
import sure  # noqa


@mock_applicationautoscaling
def test_describe_scalable_targets_ecs():
    client = boto3.client("application-autoscaling", region_name="us-east-1")
    response = client.describe_scalable_targets(ServiceNamespace="ecs")
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert False
