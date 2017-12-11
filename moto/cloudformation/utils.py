from __future__ import unicode_literals
import uuid
import six
import random
import yaml


def generate_stack_id(stack_name):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:us-east-1:123456789:stack/{0}/{1}".format(stack_name, random_id)


def generate_changeset_id(changeset_name, region_name):
    random_id = uuid.uuid4()
    return 'arn:aws:cloudformation:{0}:123456789:changeSet/{1}/{2}'.format(region_name, changeset_name, random_id)


def random_suffix():
    size = 12
    chars = list(range(10)) + ['A-Z']
    return ''.join(six.text_type(random.choice(chars)) for x in range(size))


def yaml_tag_constructor(loader, tag, node):
    """convert shorthand intrinsic function to full name
    """
    def _f(loader, tag, node):
        if tag == '!GetAtt':
            return node.value.split('.')
        elif type(node) == yaml.SequenceNode:
            return loader.construct_sequence(node)
        else:
            return node.value

    if tag == '!Ref':
        key = 'Ref'
    else:
        key = 'Fn::{}'.format(tag[1:])

    return {key: _f(loader, tag, node)}
