from __future__ import unicode_literals
import uuid
import six
import random
import yaml
import os
import string

from cfnlint import decode, core


def generate_stack_id(stack_name, region="us-east-1", account="123456789"):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:{}:{}:stack/{}/{}".format(region, account, stack_name, random_id)


def generate_changeset_id(changeset_name, region_name):
    random_id = uuid.uuid4()
    return 'arn:aws:cloudformation:{0}:123456789:changeSet/{1}/{2}'.format(region_name, changeset_name, random_id)


def generate_stackset_id(stackset_name):
    random_id = uuid.uuid4()
    return '{}:{}'.format(stackset_name, random_id)


def generate_stackset_arn(stackset_id, region_name):
    return 'arn:aws:cloudformation:{}:123456789012:stackset/{}'.format(region_name, stackset_id)


def random_suffix():
    size = 12
    chars = list(range(10)) + list(string.ascii_uppercase)
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


def validate_template_cfn_lint(template):

    # Save the template to a temporary file -- cfn-lint requires a file
    filename = "file.tmp"
    with open(filename, "w") as file:
        file.write(template)
    abs_filename = os.path.abspath(filename)

    # decode handles both yaml and json
    template, matches = decode.decode(abs_filename, False)

    # Set cfn-lint to info
    core.configure_logging(None)

    # Initialize the ruleset to be applied (no overrules, no excludes)
    rules = core.get_rules([], [], [])

    # Use us-east-1 region (spec file) for validation
    regions = ['us-east-1']

    # Process all the rules and gather the errors
    matches = core.run_checks(
        abs_filename,
        template,
        rules,
        regions)

    return matches
