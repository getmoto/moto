from __future__ import unicode_literals
import random
import string
import six


def random_resource_id():
    size = 20
    chars = list(range(10)) + list(string.ascii_lowercase)

    return ''.join(six.text_type(random.choice(chars)) for x in range(size))
