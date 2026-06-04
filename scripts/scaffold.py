#!/usr/bin/env python
"""Generates template code and response body for specified boto3's operation.

To execute:
    cd moto  # top-level directory; script will not work from scripts dir
    ./scripts/scaffold.py

When prompted, select the service and operation that you want to add.
This script will look at the botocore's definition file for the selected
service and operation, then auto-generate the code and responses.

Almost all services are supported, as long as the service's protocol is
`query`, `json`, `rest-xml` or `rest-json`.  Even if aws adds new services, this script
will work if the protocol is known.

TODO:
  - This script doesn't generate functions in `responses.py` for
    `rest-json`.  That logic needs to be added.
  - Some services's operations might cause this script to crash. If that
    should happen, please create an issue for the problem.
"""

import os
import random
import re
import inspect
import importlib
import subprocess

import click
import jinja2
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from botocore import xform_name
from botocore.session import Session
import boto3

from moto.core.responses import BaseResponse
from moto.core.base_backend import BaseBackend
from inflection import singularize
from implementation_coverage import get_moto_implementation

PRIMITIVE_SHAPES = [
    "string",
    "timestamp",
    "integer",
    "boolean",
    "sensitiveStringType",
    "long",
]

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "./template")

INPUT_IGNORED_IN_BACKEND = ["Marker", "PageSize"]
OUTPUT_IGNORED_IN_BACKEND = ["NextMarker"]

root_dir = (
    subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
)


def print_progress(title, body, color):
    """Prints a color-code message describing current state of progress."""
    click.secho(f"\t{title}\t", fg=color, nl=False)
    click.echo(body)


def select_service():
    """Prompt user to select service and operation."""
    service_name = None
    service_names = Session().get_available_services()
    service_completer = WordCompleter(service_names)
    while service_name not in service_names:
        service_name = prompt("Select service: ", completer=service_completer)
        if service_name not in service_names:
            click.secho(f"{service_name} is not valid service", fg="red")
    return service_name


def print_service_status(service_name):
    implemented, operation_names = get_operations(service_name)
    click.echo("==Current Implementation Status==")
    for operation_name in operation_names:
        check = "X" if operation_name in implemented else " "
        click.secho(f"[{check}] {operation_name}")
    click.echo("=================================")


def select_operation(service_name):
    implemented, operation_names = get_operations(service_name)
    operation_completer = WordCompleter(operation_names)

    operation_available = False
    while not operation_available:
        operation_name = prompt("Select Operation: ", completer=operation_completer)
        if operation_name not in operation_names:
            click.secho(f"{operation_name} is not valid operation", fg="red")
        elif operation_name in implemented:
            click.secho(f"{operation_name} is already implemented", fg="red")
        else:
            operation_available = True
    return operation_name


def get_operations(service_name):
    try:
        moto_client, _name = get_moto_implementation(service_name)
    except ModuleNotFoundError:
        moto_client = None
    real_client = boto3.client(service_name, region_name="us-east-1")
    implemented = []
    operation_names = [
        xform_name(op) for op in real_client.meta.service_model.operation_names
    ]
    for operation in operation_names:
        if moto_client and operation in dir(moto_client):
            implemented.append(operation)
    return implemented, operation_names


def get_escaped_service(service):
    """Remove dashes from the service name."""
    return service.replace("-", "")


def get_lib_dir(service):
    """Return moto path for the location of the code supporting the service."""
    return os.path.join("moto", get_escaped_service(service))


def get_test_dir(service):
    """Return moto path for the test directory for the service."""
    return os.path.join("tests", f"test_{get_escaped_service(service)}")


def render_template(tmpl_dir, tmpl_filename, context, service, alt_filename=None):
    """Create specified files from Jinja templates for specified service."""
    is_test = "test" in tmpl_dir
    rendered = (
        jinja2.Environment(loader=jinja2.FileSystemLoader(tmpl_dir))
        .get_template(tmpl_filename)
        .render(context)
    )

    dirname = get_test_dir(service) if is_test else get_lib_dir(service)
    filename = alt_filename or os.path.splitext(tmpl_filename)[0]
    filepath = os.path.join(dirname, filename)

    if os.path.exists(filepath):
        print_progress("skip creating", filepath, "yellow")
    else:
        print_progress("creating", filepath, "green")
        with open(filepath, "w", encoding="utf-8") as fhandle:
            fhandle.write(rendered)


def initialize_service(service, api_protocol):
    """Create lib and test dirs if they don't exist."""
    lib_dir = get_lib_dir(service)
    test_dir = get_test_dir(service)

    print_progress("Initializing service", service, "green")

    client = boto3.client(service)
    service_class = client.__class__.__name__
    endpoint_prefix = client._service_model.endpoint_prefix

    tmpl_context = {
        "service": service,
        "service_class": service_class,
        "endpoint_prefix": endpoint_prefix,
        "api_protocol": api_protocol,
        "escaped_service": get_escaped_service(service),
    }

    # initialize service directory
    if os.path.exists(lib_dir):
        print_progress("skip creating", lib_dir, "yellow")
    else:
        print_progress("creating", lib_dir, "green")
        os.makedirs(lib_dir)

    tmpl_dir = os.path.join(TEMPLATE_DIR, "lib")
    for tmpl_filename in os.listdir(tmpl_dir):
        render_template(tmpl_dir, tmpl_filename, tmpl_context, service)

    # initialize test directory
    if os.path.exists(test_dir):
        print_progress("skip creating", test_dir, "yellow")
    else:
        print_progress("creating", test_dir, "green")
        os.makedirs(test_dir)
    tmpl_dir = os.path.join(TEMPLATE_DIR, "test")
    for tmpl_filename in os.listdir(tmpl_dir):
        alt_filename = (
            f"test_{get_escaped_service(service)}.py"
            if tmpl_filename == "test_service.py.j2"
            else None
        )
        render_template(tmpl_dir, tmpl_filename, tmpl_context, service, alt_filename)


def to_upper_camel_case(string):
    """Convert snake case to camel case."""
    return "".join([_.title() for _ in string.split("_")])


def to_lower_camel_case(string):
    """Convert snake to camel case, but start string with lowercase letter."""
    words = string.split("_")
    return "".join(words[:1] + [_.title() for _ in words[1:]])


def to_snake_case(string):
    """Convert camel case to snake case."""
    new_string = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", string)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", new_string).lower()


def get_operation_name_in_keys(operation_name, operation_keys):
    """Return AWS operation name (service) found in list of client services."""
    index = [_.lower() for _ in operation_keys].index(operation_name.lower())
    return operation_keys[index]


def get_function_in_responses(service, operation, protocol): 
    """refers to definition of API in botocore, and autogenerates function
    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    escaped_service = get_escaped_service(service)
    client = boto3.client(service)

    aws_operation_name = get_operation_name_in_keys(
        to_upper_camel_case(operation),
        list(client._service_model._service_description["operations"].keys()),
    )

    op_model = client._service_model.operation_model(aws_operation_name)
    if not hasattr(op_model.output_shape, "members"):
        outputs = {}
    else:
        outputs = op_model.output_shape.members
    inputs = op_model.input_shape.members
    input_names = [
        to_snake_case(_) for _ in inputs.keys() if _ not in INPUT_IGNORED_IN_BACKEND
    ]
    output_names = [
        to_snake_case(_) for _ in outputs.keys() if _ not in OUTPUT_IGNORED_IN_BACKEND
    ]

    body = ""
    if protocol in ["rest-xml"]:
        body += f"\ndef {operation}(self, request, full_url, headers):\n"
        body += "    self.setup_class(request, full_url, headers)\n"
    else:
        body = f"\ndef {operation}(self):\n"
    body += "    params = self._get_params()\n"

    for input_name, input_type in inputs.items():
        body += f'    {to_snake_case(input_name)} = params.get("{input_name}")\n'
    if output_names:
        body += f"    {', '.join(output_names)} = self.{escaped_service}_backend.{operation}(\n"
    else:
        body += f"    self.{escaped_service}_backend.{operation}(\n"
    for input_name in input_names:
        body += f"        {input_name}={input_name},\n"

    body += "    )\n"
    if protocol in ["query", "rest-xml"]:
        body += get_result_dict_template(service, operation)
        body += f"    return ActionResult(result)\n"
    elif protocol in ["json", "rest-json"]:
        body += "    # TODO: adjust response\n"
        names = ", ".join([f"{to_lower_camel_case(_)}={_}" for _ in output_names])
        body += f"    return json.dumps(dict({names}))\n"
    return body


def get_function_in_models(service, operation):
    """refers to definition of API in botocore, and autogenerates function
    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    client = boto3.client(service)

    aws_operation_name = get_operation_name_in_keys(
        to_upper_camel_case(operation),
        list(client._service_model._service_description["operations"].keys()),
    )
    op_model = client._service_model.operation_model(aws_operation_name)
    inputs = op_model.input_shape.members
    if not hasattr(op_model.output_shape, "members"):
        outputs = {}
    else:
        outputs = op_model.output_shape.members
    input_names = [
        to_snake_case(_) for _ in inputs.keys() if _ not in INPUT_IGNORED_IN_BACKEND
    ]
    output_names = [
        to_snake_case(_) for _ in outputs.keys() if _ not in OUTPUT_IGNORED_IN_BACKEND
    ]
    if input_names:
        body = f"def {operation}(self, {', '.join(input_names)}):\n"
    else:
        body = "def {}(self)\n"
    body += "    # implement here\n"
    body += f"    return {', '.join(output_names)}\n\n"

    return body


def get_func_in_tests(service, operation):
    """
    Autogenerates an example unit test
    Throws an exception by default, to remind the user to implement this
    """
    escaped_service = get_escaped_service(service)
    random_region = random.choice(["us-east-2", "eu-west-1", "ap-southeast-1"])
    body = "\n\n"
    body += f"@mock_aws\n"
    body += f"def test_{operation}():\n"
    body += f'    client = boto3.client("{service}", region_name="{random_region}")\n'
    body += f"    resp = client.{operation}()\n"
    body += f"\n"
    body += f'    raise Exception("NotYetImplemented")'
    body += "\n"
    return body


def _get_dict_entry(name, shape, indent, name_prefix=None):
    """Recursively build a Python dict string entry for an output shape member."""
    if not name_prefix:
        name_prefix = []

    class_name = shape.__class__.__name__
    shape_type = shape.type_name
    prefix = " " * indent

    if class_name in ("StringShape", "Shape") or shape_type == "structure":
        if shape_type == "structure" and hasattr(shape, "members") and shape.members:
            # Nested structure - recurse into members
            lines = [f'{prefix}"{name}": {{']
            for member_name, member_shape in shape.members.items():
                lines.append(
                    _get_dict_entry(
                        member_name,
                        member_shape,
                        indent + 4,
                        name_prefix,
                    )
                )
            lines.append(f"{prefix}}},")
            return "\n".join(lines)
        else:
            if name_prefix:
                var = f"{name_prefix[-1]}.{to_snake_case(name)}"
            else:
                var = to_snake_case(name)
            return f'{prefix}"{name}": {var},'

    if class_name in ("ListShape",) or shape_type == "list":
        singular = singularize(name.lower())
        if name_prefix:
            iter_var = f"{name_prefix[-1]}.{to_snake_case(name)}"
        else:
            iter_var = to_snake_case(name)

        if hasattr(shape.member, "members") and shape.member.members:
            lines = [f'{prefix}"{name}": [']
            lines.append(f"{prefix}    {{")
            for member_name, member_shape in shape.member.members.items():
                lines.append(
                    _get_dict_entry(
                        member_name,
                        member_shape,
                        indent + 8,
                        name_prefix + [singular],
                    )
                )
            lines.append(f"{prefix}    }}")
            lines.append(f"{prefix}    for {singular} in {iter_var}")
            lines.append(f"{prefix}],")
            return "\n".join(lines)
        else:
            return f'{prefix}"{name}": {iter_var},'

    raise ValueError(f"Not supported Shape: {shape}")


def get_result_dict_template(service, operation):
    """Refers to definition of API in botocore, and autogenerates a Python
    dict template representing the output model of the boto3 client operation.

    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    client = boto3.client(service)

    aws_operation_name = get_operation_name_in_keys(
        to_upper_camel_case(operation),
        list(client._service_model._service_description["operations"].keys()),
    )

    op_model = client._service_model.operation_model(aws_operation_name)
    if not hasattr(op_model.output_shape, "members"):
        outputs = {}
    else:
        outputs = op_model.output_shape.members

    lines = [f"    result = {{"]
    for output_name, output_shape in outputs.items():
        if output_name in OUTPUT_IGNORED_IN_BACKEND:
            continue
        lines.append(_get_dict_entry(output_name, output_shape, indent=8))
    lines.append("    }\n")
    return "\n".join(lines)


def insert_code_to_class(path, base_class, new_code):
    """Add code for class handling service's response or backend."""
    with open(path, encoding="utf-8") as fhandle:
        lines = [_.replace("\n", "") for _ in fhandle.readlines()]
    mod_path = os.path.splitext(path)[0].replace("/", ".")
    mod = importlib.import_module(mod_path)
    clsmembers = inspect.getmembers(mod, inspect.isclass)
    _response_cls = [
        _[1] for _ in clsmembers if issubclass(_[1], base_class) and _[1] != base_class
    ]
    if len(_response_cls) != 1:
        raise Exception("unknown error, number of clsmembers is not 1")
    response_cls = _response_cls[0]
    code_lines, line_no = inspect.getsourcelines(response_cls)
    end_line_no = line_no + len(code_lines)

    func_lines = [" " * 4 + _ for _ in new_code.splitlines()]

    lines = lines[:end_line_no] + func_lines + lines[end_line_no:]

    body = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as fhandle:
        fhandle.write(body)


def insert_url(service, operation, api_protocol):
    """Create urls.py with appropriate URL bases and paths."""
    client = boto3.client(service)
    service_class = client.__class__.__name__

    aws_operation_name = get_operation_name_in_keys(
        to_upper_camel_case(operation),
        list(client._service_model._service_description["operations"].keys()),
    )
    uri = client._service_model.operation_model(aws_operation_name).http["requestUri"]
    if "?" in uri:
        uri = uri.split("?")[0]

    path = os.path.join(
        os.path.dirname(__file__), "..", "moto", get_escaped_service(service), "urls.py"
    )
    with open(path, encoding="utf-8") as fhandle:
        lines = [_.replace("\n", "") for _ in fhandle.readlines()]

    if any(_ for _ in lines if re.match(uri, _)):
        return
    uri = BaseResponse.uri_to_regexp(uri)[1:-1]

    url_paths_found = False
    last_elem_line_index = -1
    for i, line in enumerate(lines):
        if line.startswith("url_paths"):
            url_paths_found = True
        if url_paths_found and line.startswith("}"):
            last_elem_line_index = i - 1

    prev_line = lines[last_elem_line_index]
    if not prev_line.endswith("{") and not prev_line.endswith(","):
        lines[last_elem_line_index] += ","

    # generate url pattern
    if api_protocol == "rest-json":
        new_line = f'    "{{0}}{uri}$": {service_class}Response.dispatch,'
    elif api_protocol == "rest-xml":
        new_line = f'    "{{0}}{uri}$": {service_class}Response.{operation},'
    else:
        new_line = f'    "{{0}}{uri}$": {service_class}Response.dispatch,'
    if new_line in lines:
        return
    lines.insert(last_elem_line_index + 1, new_line)

    body = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as fhandle:
        fhandle.write(body)


def insert_codes(service, operation, api_protocol):
    """Create the responses.py and models.py for the service and operation."""
    escaped_service = get_escaped_service(service)
    func_in_responses = get_function_in_responses(service, operation, api_protocol)
    func_in_models = get_function_in_models(service, operation)
    func_in_tests = get_func_in_tests(service, operation)
    # edit responses.py
    responses_path = f"moto/{escaped_service}/responses.py"
    print_progress("inserting code", responses_path, "green")
    insert_code_to_class(responses_path, BaseResponse, func_in_responses)

    # edit models.py
    models_path = f"moto/{escaped_service}/models.py"
    print_progress("inserting code", models_path, "green")
    insert_code_to_class(models_path, BaseBackend, func_in_models)

    # edit urls.py
    insert_url(service, operation, api_protocol)

    # Edit tests
    tests_path = f"tests/test_{escaped_service}/test_{escaped_service}.py"
    print_progress("inserting code", tests_path, "green")
    with open(tests_path, "a", encoding="utf-8") as fhandle:
        fhandle.write(func_in_tests)


@click.command()
def main():
    click.echo("This script uses the click-module.\n")
    click.echo(
        " - Start typing the name of the service you want to extend\n"
        " - Use Tab to auto-complete the first suggest service\n"
        " - Use the up and down-arrows on the keyboard to select something from the dropdown\n"
        " - Press enter to continue\n"
    )

    """Create basic files needed for the user's choice of service and op."""
    service = select_service()
    print_service_status(service)

    while True:
        operation = select_operation(service)

        api_protocol = boto3.client(service)._service_model.metadata["protocol"]
        initialize_service(service, api_protocol)

        if api_protocol in ["query", "json", "rest-json", "rest-xml"]:
            insert_codes(service, operation, api_protocol)
        else:
            print_progress(
                "skip inserting code",
                f'api protocol "{api_protocol}" is not supported',
                "yellow",
            )

        click.echo("Updating backend index...")
        subprocess.check_output(
            [f"{root_dir}/scripts/update_backend_index.py"]
        ).decode().strip()

        click.echo(
            "\n"
            "Please select another operation, or Ctrl-X/Ctrl-C to cancel."
            "\n\n"
            "Remaining steps after development is complete:\n"
            "- Run scripts/implementation_coverage.py,\n"
            "\n"
        )


if __name__ == "__main__":
    main()
