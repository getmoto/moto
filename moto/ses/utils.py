from __future__ import unicode_literals
import random
import string


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
