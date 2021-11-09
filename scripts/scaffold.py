#!/usr/bin/env python
"""Generates template code and response body for specified boto3's operation.

To execute:
    cd moto  # top-level directory; script will not work from scripts dir
    ./scripts/scaffold.py

When prompted, select the service and operation that you want to add.
This script will look at the botocore's definition file for the selected
service and operation, then auto-generate the code and responses.

Almost all services are supported, as long as the service's protocol is
`query`, `json` or `rest-json`.  Even if aws adds new services, this script
will work if the protocol is known.

TODO:
  - This script doesn't generate functions in `responses.py` for
    `rest-json`.  That logic needs to be added.
  - Some services's operations might cause this script to crash. If that
    should happen, please create an issue for the problem.
"""
import os
import re
import inspect
import importlib
from lxml import etree

import click
import jinja2
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from botocore import xform_name
from botocore.session import Session
import boto3

from moto.core.responses import BaseResponse
from moto.core import BaseBackend
from inflection import singularize
from implementation_coverage import get_moto_implementation

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "./template")

INPUT_IGNORED_IN_BACKEND = ["Marker", "PageSize"]
OUTPUT_IGNORED_IN_BACKEND = ["NextMarker"]


def print_progress(title, body, color):
    """Prints a color-code message describing current state of progress."""
    click.secho(f"\t{title}\t", fg=color, nl=False)
    click.echo(body)


def select_service_and_operation():
    """Prompt user to select service and operation."""
    service_names = Session().get_available_services()
    service_completer = WordCompleter(service_names)
    service_name = prompt("Select service: ", completer=service_completer)
    if service_name not in service_names:
        click.secho(f"{service_name} is not valid service", fg="red")
        raise click.Abort()
    moto_client = get_moto_implementation(service_name)
    real_client = boto3.client(service_name, region_name="us-east-1")
    implemented = []
    not_implemented = []

    operation_names = [
        xform_name(op) for op in real_client.meta.service_model.operation_names
    ]
    for operation in operation_names:
        if moto_client and operation in dir(moto_client):
            implemented.append(operation)
        else:
            not_implemented.append(operation)
    operation_completer = WordCompleter(operation_names)

    click.echo("==Current Implementation Status==")
    for operation_name in operation_names:
        check = "X" if operation_name in implemented else " "
        click.secho(f"[{check}] {operation_name}")
    click.echo("=================================")
    operation_name = prompt("Select Operation: ", completer=operation_completer)

    if operation_name not in operation_names:
        click.secho(f"{operation_name} is not valid operation", fg="red")
        raise click.Abort()

    if operation_name in implemented:
        click.secho(f"{operation_name} is already implemented", fg="red")
        raise click.Abort()
    return service_name, operation_name


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


def append_mock_to_init_py(service):
    """Update __init_.py to add line to load the mock service."""
    path = os.path.join(os.path.dirname(__file__), "..", "moto", "__init__.py")
    with open(path, encoding="utf-8") as fhandle:
        lines = [_.replace("\n", "") for _ in fhandle.readlines()]

    if any(_ for _ in lines if re.match(f"^mock_{service}.*lazy_load(.*)$", _)):
        return
    filtered_lines = [_ for _ in lines if re.match("^mock_.*lazy_load(.*)$", _)]
    last_import_line_index = lines.index(filtered_lines[-1])

    escaped_service = get_escaped_service(service)
    new_line = (
        f"mock_{escaped_service} = lazy_load("
        f'".{escaped_service}", "mock_{escaped_service}", boto3_name="{service}")'
    )
    lines.insert(last_import_line_index + 1, new_line)

    body = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as fhandle:
        fhandle.write(body)


def initialize_service(service, api_protocol):
    """Create lib and test dirs if they don't exist."""
    lib_dir = get_lib_dir(service)
    test_dir = get_test_dir(service)

    print_progress("Initializing service", service, "green")

    client = boto3.client(service)
    service_class = client.__class__.__name__
    endpoint_prefix = (
        # pylint: disable=protected-access
        client._service_model.endpoint_prefix
    )

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
    # append mock to initi files
    append_mock_to_init_py(service)


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


def get_function_in_responses(
    service, operation, protocol
):  # pylint: disable=too-many-locals
    """refers to definition of API in botocore, and autogenerates function
    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    escaped_service = get_escaped_service(service)
    client = boto3.client(service)

    # pylint: disable=protected-access
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
    body = f"\ndef {operation}(self):\n"

    for input_name, input_type in inputs.items():
        type_name = input_type.type_name
        if type_name == "integer":
            arg_line_tmpl = '    {}=self._get_int_param("{}")\n'
        elif type_name == "list":
            arg_line_tmpl = '    {}=self._get_list_prefix("{}.member")\n'
        else:
            arg_line_tmpl = '    {}=self._get_param("{}")\n'
        body += arg_line_tmpl.format(to_snake_case(input_name), input_name)
    if output_names:
        body += f"    {', '.join(output_names)} = self.{escaped_service}_backend.{operation}(\n"
    else:
        body += f"    self.{escaped_service}_backend.{operation}(\n"
    for input_name in input_names:
        body += f"        {input_name}={input_name},\n"

    body += "    )\n"
    if protocol == "query":
        body += f"    template = self.response_template({operation.upper()}_TEMPLATE)\n"
        names = ", ".join([f"{n}={n}" for n in output_names])
        body += f"    return template.render({names})\n"
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

    # pylint: disable=protected-access
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


def _get_subtree(name, shape, replace_list, name_prefix=None):
    if not name_prefix:
        name_prefix = []

    class_name = shape.__class__.__name__
    if class_name in ("StringShape", "Shape"):
        tree = etree.Element(name)  # pylint: disable=c-extension-no-member
        if name_prefix:
            tree.text = f"{{{{ {name_prefix[-1]}.{to_snake_case(name)} }}}}"
        else:
            tree.text = f"{{{{ {to_snake_case(name)} }}}}"
        return tree

    if class_name in ("ListShape",):
        # pylint: disable=c-extension-no-member
        replace_list.append((name, name_prefix))
        tree = etree.Element(name)
        t_member = etree.Element("member")
        tree.append(t_member)
        for nested_name, nested_shape in shape.member.members.items():
            t_member.append(
                _get_subtree(
                    nested_name,
                    nested_shape,
                    replace_list,
                    name_prefix + [singularize(name.lower())],
                )
            )
        return tree
    raise ValueError("Not supported Shape")


def get_response_query_template(service, operation):  # pylint: disable=too-many-locals
    """refers to definition of API in botocore, and autogenerates template
    Assume that response format is xml when protocol is query

    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    client = boto3.client(service)

    # pylint: disable=protected-access
    aws_operation_name = get_operation_name_in_keys(
        to_upper_camel_case(operation),
        list(client._service_model._service_description["operations"].keys()),
    )

    op_model = client._service_model.operation_model(aws_operation_name)
    result_wrapper = op_model.output_shape.serialization["resultWrapper"]
    response_wrapper = result_wrapper.replace("Result", "Response")
    metadata = op_model.metadata
    xml_namespace = metadata["xmlNamespace"]

    # build xml tree
    # pylint: disable=c-extension-no-member
    t_root = etree.Element(response_wrapper, xmlns=xml_namespace)

    # build metadata
    t_metadata = etree.Element("ResponseMetadata")
    t_request_id = etree.Element("RequestId")
    t_request_id.text = "1549581b-12b7-11e3-895e-1334aEXAMPLE"
    t_metadata.append(t_request_id)
    t_root.append(t_metadata)

    # build result
    t_result = etree.Element(result_wrapper)
    outputs = op_model.output_shape.members
    replace_list = []
    for output_name, output_shape in outputs.items():
        t_result.append(_get_subtree(output_name, output_shape, replace_list))
    t_root.append(t_result)
    xml_body = etree.tostring(t_root, pretty_print=True).decode("utf-8")
    xml_body_lines = xml_body.splitlines()
    for replace in replace_list:
        name = replace[0]
        prefix = replace[1]
        singular_name = singularize(name)

        start_tag = f"<{name}>"
        iter_name = f"{prefix[-1]}.{name.lower()}" if prefix else name.lower()
        loop_start = f"{{%% for {singular_name.lower()} in {iter_name} %%}}"
        end_tag = f"</{name}>"
        loop_end = "{{ endfor }}"

        start_tag_indexes = [i for i, l in enumerate(xml_body_lines) if start_tag in l]
        if len(start_tag_indexes) != 1:
            raise Exception(f"tag {start_tag} not found in response body")
        start_tag_index = start_tag_indexes[0]
        xml_body_lines.insert(start_tag_index + 1, loop_start)

        end_tag_indexes = [i for i, l in enumerate(xml_body_lines) if end_tag in l]
        if len(end_tag_indexes) != 1:
            raise Exception(f"tag {end_tag} not found in response body")
        end_tag_index = end_tag_indexes[0]
        xml_body_lines.insert(end_tag_index, loop_end)
    xml_body = "\n".join(xml_body_lines)
    body = f'\n{operation.upper()}_TEMPLATE = """{xml_body}"""'
    return body


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


def insert_url(service, operation, api_protocol):  # pylint: disable=too-many-locals
    """Create urls.py with appropriate URL bases and paths."""
    client = boto3.client(service)
    service_class = client.__class__.__name__

    # pylint: disable=protected-access
    aws_operation_name = get_operation_name_in_keys(
        to_upper_camel_case(operation),
        list(client._service_model._service_description["operations"].keys()),
    )
    uri = client._service_model.operation_model(aws_operation_name).http["requestUri"]

    path = os.path.join(
        os.path.dirname(__file__), "..", "moto", get_escaped_service(service), "urls.py"
    )
    with open(path, encoding="utf-8") as fhandle:
        lines = [_.replace("\n", "") for _ in fhandle.readlines()]

    if any(_ for _ in lines if re.match(uri, _)):
        return

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
        new_line = '    "{0}/.*$": response.dispatch,'
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
    # edit responses.py
    responses_path = f"moto/{escaped_service}/responses.py"
    print_progress("inserting code", responses_path, "green")
    insert_code_to_class(responses_path, BaseResponse, func_in_responses)

    # insert template
    if api_protocol == "query":
        template = get_response_query_template(service, operation)
        with open(responses_path, encoding="utf-8") as fhandle:
            lines = [_[:-1] for _ in fhandle.readlines()]
        lines += template.splitlines()
        with open(responses_path, "w", encoding="utf-8") as fhandle:
            fhandle.write("\n".join(lines))

    # edit models.py
    models_path = f"moto/{escaped_service}/models.py"
    print_progress("inserting code", models_path, "green")
    insert_code_to_class(models_path, BaseBackend, func_in_models)

    # edit urls.py
    insert_url(service, operation, api_protocol)


@click.command()
def main():

    click.echo("This script uses the click-module.\n")
    click.echo(" - Start typing the name of the service you want to extend\n"
               " - Use Tab to auto-complete the first suggest service\n"
               " - Use the up and down-arrows on the keyboard to select something from the dropdown\n"
               " - Press enter to continue\n")

    """Create basic files needed for the user's choice of service and op."""
    service, operation = select_service_and_operation()

    # pylint: disable=protected-access
    api_protocol = boto3.client(service)._service_model.metadata["protocol"]
    initialize_service(service, api_protocol)

    if api_protocol in ["query", "json", "rest-json"]:
        insert_codes(service, operation, api_protocol)
    else:
        print_progress(
            "skip inserting code",
            f'api protocol "{api_protocol}" is not supported',
            "yellow",
        )

    click.echo(
        "\n"
        "Remaining steps after development is complete:\n"
        '- Run scripts/implementation_coverage.py,\n'
        "- Run scripts/update_backend_index.py."
    )


if __name__ == "__main__":
    main()
