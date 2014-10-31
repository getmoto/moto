from __future__ import unicode_literals
import uuid
import six
import random


def generate_stack_id(stack_name):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:us-east-1:123456789:stack/{0}/{1}".format(stack_name, random_id)


def random_suffix():
    size = 12
    chars = list(range(10)) + ['A-Z']
    return ''.join(six.text_type(random.choice(chars)) for x in range(size))
