import os
from unittest import SkipTest, mock

import boto3

from moto import mock_aws, settings
from tests import EXAMPLE_AMI_PARAVIRTUAL, EXAMPLE_AMI_WINDOWS


# The default AMIs are not loaded for our test case, to speed things up
# But we do need it for this specific test (and others in this file..)
@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_get_password_data():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    client = boto3.client("ec2", region_name="us-east-1")

    # Ensure non-windows instances return empty password data
    instance_id = client.run_instances(
        ImageId=EXAMPLE_AMI_PARAVIRTUAL, MinCount=1, MaxCount=1
    )["Instances"][0]["InstanceId"]
    resp = client.get_password_data(InstanceId=instance_id)
    assert resp["InstanceId"] == instance_id
    assert resp["PasswordData"] == ""

    # Ensure Windows instances
    instance_id = client.run_instances(
        ImageId=EXAMPLE_AMI_WINDOWS, MinCount=1, MaxCount=1
    )["Instances"][0]["InstanceId"]
    resp = client.get_password_data(InstanceId=instance_id)
    assert resp["InstanceId"] == instance_id
    assert len(resp["PasswordData"]) == 128
