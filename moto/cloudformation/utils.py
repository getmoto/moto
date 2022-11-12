import yaml
import os
import string
from moto.moto_api._internal import mock_random as random
from typing import Any, List


def generate_stack_id(stack_name: str, region: str, account: str) -> str:
    random_id = random.uuid4()
    return f"arn:aws:cloudformation:{region}:{account}:stack/{stack_name}/{random_id}"


def generate_changeset_id(
    changeset_name: str, region_name: str, account_id: str
) -> str:
    random_id = random.uuid4()
    return f"arn:aws:cloudformation:{region_name}:{account_id}:changeSet/{changeset_name}/{random_id}"


def generate_stackset_id(stackset_name: str) -> str:
    random_id = random.uuid4()
    return f"{stackset_name}:{random_id}"


def generate_stackset_arn(stackset_id: str, region_name: str, account_id: str) -> str:
    return f"arn:aws:cloudformation:{region_name}:{account_id}:stackset/{stackset_id}"


def random_suffix() -> str:
    size = 12
    chars = list(range(10)) + list(string.ascii_uppercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def yaml_tag_constructor(loader: Any, tag: Any, node: Any) -> Any:
    """convert shorthand intrinsic function to full name"""

    def _f(loader: Any, tag: Any, node: Any) -> Any:
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
        key = f"Fn::{tag[1:]}"

    return {key: _f(loader, tag, node)}


def validate_template_cfn_lint(template: str) -> List[Any]:
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
