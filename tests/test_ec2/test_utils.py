from moto.ec2 import utils

from .helpers import rsa_check_private_key


def test_random_key_pair():
    key_pair = utils.random_key_pair()
    rsa_check_private_key(key_pair["material"])

    # AWS uses MD5 fingerprints, which are 47 characters long, *not* SHA1
    # fingerprints with 59 characters.
    assert len(key_pair["fingerprint"]) == 47
