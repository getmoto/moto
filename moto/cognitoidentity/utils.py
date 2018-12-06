from moto.core.utils import get_random_hex


def get_random_identity_id(region):
    return "{0}:{1}".format(region, get_random_hex(length=19))
