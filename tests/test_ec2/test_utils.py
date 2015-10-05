from moto.ec2 import utils


def test_random_key_pair():
    key_pair = utils.random_key_pair()
    assert len(key_pair['fingerprint']) == 59
    assert key_pair['material'].startswith('---- BEGIN RSA PRIVATE KEY ----')
    assert key_pair['material'].endswith('-----END RSA PRIVATE KEY-----')
