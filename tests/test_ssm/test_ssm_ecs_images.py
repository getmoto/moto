import os
from unittest import SkipTest, mock

import boto3

from moto import mock_aws, settings


# The default AMIs are not loaded for our test case, to speed things up
# But we do need it for this specific test
@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_aws
def test_ssm_get_latest_ami_by_path():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    ssm = boto3.client("ssm", region_name="us-east-1")
    path = "/aws/service/ecs/optimized-ami"
    params = ssm.get_parameters_by_path(Path=path, Recursive=True)["Parameters"]
    assert len(params) == 10

    ec2 = boto3.client("ec2", region_name="us-east-1")
    for param in params:
        if "Value" in param and isinstance(param["Value"], dict):
            ami = param["Value"]["image_id"]
            assert len(ec2.describe_images(ImageIds=[ami])["Images"]) == 1
