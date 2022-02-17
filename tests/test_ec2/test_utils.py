from copy import deepcopy
import ipaddress
import sure  # noqa # pylint: disable=unused-import
from unittest.mock import patch
from pytest import raises

from moto.ec2 import utils

from .helpers import rsa_check_private_key


def test_random_key_pair():
    key_pair = utils.random_key_pair()
    rsa_check_private_key(key_pair["material"])

    # AWS uses MD5 fingerprints, which are 47 characters long, *not* SHA1
    # fingerprints with 59 characters.
    assert len(key_pair["fingerprint"]) == 47


def test_random_ipv6_cidr():
    def mocked_random_resource_id(chars: int):
        return "a" * chars

    with patch("moto.ec2.utils.random_resource_id", mocked_random_resource_id):
        cidr_address = utils.random_ipv6_cidr()
        # this will throw value error if host bits are set
        ipaddress.ip_network(cidr_address)


def test_gen_moto_amis():
    image_with_all_reqd_keys = {
        "ImageId": "ami-03cf127a",
        "State": "available",
        "Public": True,
        "OwnerId": "801119661308",
        "RootDeviceType": "ebs",
        "RootDeviceName": "/dev/sda1",
        "Description": "Microsoft Windows Server 2016 Nano Locale English AMI provided by Amazon",
        "ImageType": "machine",
        "Architecture": "x86_64",
        "Name": "Windows_Server-2016-English-Nano-Base-2017.10.13",
        "VirtualizationType": "hvm",
        "Hypervisor": "xen",
    }

    images = []
    images.append(deepcopy(image_with_all_reqd_keys))
    images.append(deepcopy(image_with_all_reqd_keys))

    # make one of the copies of the image miss a key
    images[1].pop("Public")

    # with drop=True, it shouldn't throw but will give us only one AMI in the result
    images.should.have.length_of(2)
    amis = utils.gen_moto_amis(images, drop_images_missing_keys=True)
    amis.should.have.length_of(1)

    # with drop=False, it should raise KeyError because of the missing key
    with raises(KeyError, match="'Public'"):
        utils.gen_moto_amis(images, drop_images_missing_keys=False)
