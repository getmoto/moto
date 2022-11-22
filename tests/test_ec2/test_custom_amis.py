"""
This test lives on its own as it requires moto to be imported after
setting of MOTO_AMIS_PATH env var, as per ec2 models documentation
"""
import json
import os
from pathlib import Path

import boto3


def setup_amis():
    test_ami_path = Path(__file__).parent / "test_ami.json"
    os.environ["MOTO_AMIS_PATH"] = str(test_ami_path)
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


ami_path = setup_amis()
from moto import mock_ec2  # noqa: E402


@mock_ec2
def test_custom_amis_with_MOTO_AMIS_PATH():

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    images = ec2_client.describe_images()["Images"]
    assert len(images) == 1

    os.remove(ami_path)
