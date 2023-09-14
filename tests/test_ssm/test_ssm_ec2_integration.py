import boto3
import os

from moto import mock_ec2, mock_ssm, settings
from unittest import mock, SkipTest


test_ami = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"


# The default AMIs are not loaded for our test case, to speed things up
# But we do need it for this specific test
@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_ec2
@mock_ssm
def test_ssm_get_latest_ami_by_path():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    ssm = boto3.client("ssm", region_name="us-east-1")
    ami = ssm.get_parameter(Name=test_ami)["Parameter"]["Value"]

    ec2 = boto3.client("ec2", region_name="us-east-1")
    assert len(ec2.describe_images(ImageIds=[ami])["Images"]) == 1
