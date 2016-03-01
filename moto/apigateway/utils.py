from __future__ import unicode_literals
import six
import random


def create_rest_api_id():
    size = 10
    chars = list(range(10)) + ['A-Z']
    return ''.join(six.text_type(random.choice(chars)) for x in range(size))
