import hashlib
import ipaddress
from copy import deepcopy
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pytest import raises

from moto.ec2 import utils
from moto.utilities.utils import md5_hash

from .helpers import check_private_key

if TYPE_CHECKING:
    from hashlib import _Hash


def test_random_key_pair():
    key_pair = utils.random_rsa_key_pair()
    check_private_key(key_pair["material"], "rsa")

    # AWS uses SHA1 for created by Amazon fingerprints, which are 59 characters long
    assert len(key_pair["fingerprint"]) == 59

    key_pair = utils.random_ed25519_key_pair()
    check_private_key(key_pair["material"], "ed25519")


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
        "Tags": [
            {"Key": "foo", "Value": "bar"},
            {"Key": "bar", "Value": "baz"},
        ],
    }

    images = []
    images.append(deepcopy(image_with_all_reqd_keys))
    images.append(deepcopy(image_with_all_reqd_keys))

    # make one of the copies of the image miss a key
    images[1].pop("Public")

    # with drop=True, it shouldn't throw but will give us only one AMI in the result
    assert len(images) == 2
    amis = utils.gen_moto_amis(images, drop_images_missing_keys=True)
    assert len(amis) == 1
    expected_tags = {"foo": "bar", "bar": "baz"}
    assert amis[0]["tags"] == expected_tags

    # with drop=False, it should raise KeyError because of the missing key
    with raises(KeyError, match="'Public'"):
        utils.gen_moto_amis(images, drop_images_missing_keys=False)


@pytest.mark.parametrize(
    "is_imported, algorithm", [(True, md5_hash), (False, hashlib.sha1)]
)
def test_select_hash_algorithm__rsa(is_imported: bool, algorithm: "_Hash"):
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()

    selected_algorithm = utils.select_hash_algorithm(public_key, is_imported)

    assert selected_algorithm == algorithm


def test_select_hash_algorithm__ed25519():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    selected_algorithm = utils.select_hash_algorithm(public_key)

    assert selected_algorithm == hashlib.sha256


def test_public_key_fingerprint__ed25519():
    """Checks the function with SHA256.

    Hash algorithm is selected in `select_hash_algorithm`.
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    fingerprint = utils.public_key_fingerprint(
        public_key, hash_constructor=hashlib.sha256
    )

    assert len(fingerprint) == 95
