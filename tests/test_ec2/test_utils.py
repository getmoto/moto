import ipaddress
from unittest.mock import patch

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
