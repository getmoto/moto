import json
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

    # The AMI details are a JSON document, returned as a string
    details = [json.loads(p["Value"]) for p in params if p["Value"].startswith("{")]
    assert details

    ec2 = boto3.client("ec2", region_name="us-east-1")
    for detail in details:
        ami = detail["image_id"]
        assert len(ec2.describe_images(ImageIds=[ami])["Images"]) == 1


@mock_aws
def test_ssm_get_recommended_ecs_ami_returns_json_string():
    ssm = boto3.client("ssm", region_name="us-east-1")
    name = "/aws/service/ecs/optimized-ami/amazon-linux-2/recommended"

    value = ssm.get_parameter(Name=name)["Parameter"]["Value"]
    assert isinstance(value, str)
    image_id = json.loads(value)["image_id"]

    by_name = ssm.get_parameter(Name=f"{name}/image_id")["Parameter"]["Value"]
    assert by_name == image_id
