import string
from email.utils import parseaddr
from moto.moto_api._internal import mock_random as random


def random_hex(length):
    return "".join(random.choice(string.ascii_lowercase) for x in range(length))


def get_random_message_id():
    return "{0}-{1}-{2}-{3}-{4}-{5}-{6}".format(
        random_hex(16),
        random_hex(8),
        random_hex(4),
        random_hex(4),
        random_hex(4),
        random_hex(12),
        random_hex(6),
    )


def is_valid_address(addr):
    _, address = parseaddr(addr)
    address = address.split("@")
    if len(address) != 2 or not address[1]:
        return False, "Missing domain"
    return True, None
