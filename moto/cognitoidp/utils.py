from __future__ import unicode_literals
import six
import random
import string


def create_id():
    size = 26
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(six.text_type(random.choice(chars)) for x in range(size))
