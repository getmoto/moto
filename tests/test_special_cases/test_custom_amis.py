"""
This test lives on its own as it requires moto to be imported after
setting of MOTO_AMIS_PATH env var, as per ec2 models documentation
"""
import boto3
import json
import os
import importlib
from unittest import SkipTest, TestCase
from pathlib import Path

import moto
from moto import settings, mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID
from moto.ec2.models import ec2_backends


@mock_ec2
class TestEC2CustomAMIs(TestCase):
    def setup_amis(self):
        test_ami_path = Path(__file__).parent / "test_ami.json"
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
            }
        ]
        with test_ami_path.open("w") as fp:
            json.dump(test_ami, fp)

        return test_ami_path

    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("Only test status code in non-ServerMode")
        self.test_ami_path = self.setup_amis()
        os.environ["MOTO_AMIS_PATH"] = str(self.test_ami_path)

        # Reload the backend, and remove any existing AMIs
        importlib.reload(moto.ec2.models.amis)
        ec2_backends[DEFAULT_ACCOUNT_ID].reset()

    def tearDown(self) -> None:
        os.remove(self.test_ami_path)
        del os.environ["MOTO_AMIS_PATH"]

        # Reload the backend, and remove our custom AMI
        importlib.reload(moto.ec2.models.amis)
        ec2_backends[DEFAULT_ACCOUNT_ID].reset()

    def test_custom_amis_with_MOTO_AMIS_PATH(self):
        ec2_client = boto3.client("ec2", region_name="us-east-1")

        # Now reload our images with only the custom AMIs loaded
        images = ec2_client.describe_images()["Images"]
        assert len(images) == 1
