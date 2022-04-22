import uuid
import random
import yaml
import os
import string

from moto.core import ACCOUNT_ID


def generate_stack_id(stack_name, region="us-east-1", account=ACCOUNT_ID):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:{}:{}:stack/{}/{}".format(
        region, account, stack_name, random_id
    )


def generate_changeset_id(changeset_name, region_name):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:{0}:{1}:changeSet/{2}/{3}".format(
        region_name, ACCOUNT_ID, changeset_name, random_id
    )


def generate_stackset_id(stackset_name):
    random_id = uuid.uuid4()
    return "{}:{}".format(stackset_name, random_id)


def generate_stackset_arn(stackset_id, region_name):
    return "arn:aws:cloudformation:{}:{}:stackset/{}".format(
        region_name, ACCOUNT_ID, stackset_id
    )


def random_suffix():
    size = 12
    chars = list(range(10)) + list(string.ascii_uppercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def yaml_tag_constructor(loader, tag, node):
    """convert shorthand intrinsic function to full name"""

    def _f(loader, tag, node):
        if tag == "!GetAtt":
            if isinstance(node.value, list):
                return node.value
            return node.value.split(".")
        elif type(node) == yaml.SequenceNode:
            return loader.construct_sequence(node)
        else:
            return node.value

    if tag == "!Ref":
        key = "Ref"
    else:
        key = "Fn::{}".format(tag[1:])

    return {key: _f(loader, tag, node)}


def validate_template_cfn_lint(template):
    # Importing cfnlint adds a significant overhead, so we keep it local
    from cfnlint import decode, core

    # Save the template to a temporary file -- cfn-lint requires a file
    filename = "file.tmp"
    with open(filename, "w") as file:
        file.write(template)
    abs_filename = os.path.abspath(filename)

    # decode handles both yaml and json
    try:
        template, matches = decode.decode(abs_filename, False)
    except TypeError:
        # As of cfn-lint 0.39.0, the second argument (ignore_bad_template) was dropped
        # https://github.com/aws-cloudformation/cfn-python-lint/pull/1580
        template, matches = decode.decode(abs_filename)

    # Set cfn-lint to info
    core.configure_logging(None)

    # Initialize the ruleset to be applied (no overrules, no excludes)
    rules = core.get_rules([], [], [])

    # Use us-east-1 region (spec file) for validation
    regions = ["us-east-1"]

    # Process all the rules and gather the errors
    matches = core.run_checks(abs_filename, template, rules, regions)

    return matches
