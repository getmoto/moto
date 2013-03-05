import random
import string


def random_hex(length):
    return ''.join(random.choice(string.lowercase) for x in range(length))


def get_random_message_id():
    return "{}-{}-{}-{}-{}-{}-{}".format(
           random_hex(16),
           random_hex(8),
           random_hex(4),
           random_hex(4),
           random_hex(4),
           random_hex(12),
           random_hex(6),
    )
