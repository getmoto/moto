"""
This test lives on its own as it requires moto to be imported after
setting of MOTO_AMIS_PATH env var, as per ec2 models documentation
"""

import importlib
import json
import os
from pathlib import Path
from unittest import SkipTest, TestCase

import boto3

from moto import ec2, mock_aws, settings

TEST_AMI_PATH = Path(__file__).parent / "test_ami.json"


@mock_aws
class TestEC2CustomAMIs(TestCase):
    def setUpClass(*args):
        # Specify the Custom AMIs to be loaded

        test_ami = [
            {
                "ami_id": "ami-760aaa0f760aaa0fe",
                "name": "infra-eks-20211110080547-bionic",
                "description": "An AMI",
                "owner_id": "123456789012",
                "public": False,
                "virtualization_type": "hvm",
                "architecture": "x86_64",
                "state": "available",
                "platform": None,
                "image_type": "machine",
                "hypervisor": "xen",
                "root_device_name": "/dev/sda1",
                "root_device_type": "ebs",
                "sriov": "simple",
                "creation_date": "2021-11-10T08:13:01.000Z",
                "tags": {
                    "tag1": "value1",
                    "tag2": "value2",
                },
            }
        ]
        with TEST_AMI_PATH.open("w") as fp:
            json.dump(test_ami, fp)

        os.environ["MOTO_AMIS_PATH"] = str(TEST_AMI_PATH)

        # Reload the existing file - if this file has been loaded before this test runs, it will not refresh the loaded AMIs
        importlib.reload(ec2.models.amis)

    def tearDownClass(*args):
        os.remove(TEST_AMI_PATH)
        del os.environ["MOTO_AMIS_PATH"]

        # Reload the file again - whichever test is executed next should not start with our AMIs preloaded
        importlib.reload(ec2.models.amis)

    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("Only test status code in non-ServerMode")

    def test_custom_amis_with_MOTO_AMIS_PATH(self):
        ec2_client = boto3.client("ec2", region_name="us-east-1")

        # Now reload our images with only the custom AMIs loaded
        images = ec2_client.describe_images()["Images"]
        assert len(images) == 1
        image = images[0]
        expected_tags = [
            {"Key": "tag1", "Value": "value1"},
            {"Key": "tag2", "Value": "value2"},
        ]
        assert image["Tags"] == expected_tags

    def test_custom_amis_on_second_reset(self):
        ec2_client = boto3.client("ec2", region_name="us-east-1")

        # Because this is our second test case, the `mock_aws` decorator has reset all data
        # Verify that the AMI are still loaded and reachable
        images = ec2_client.describe_images()["Images"]
        assert len(images) == 1
