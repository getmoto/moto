#!/usr/bin/env python
"""This script generates template codes and response body for specified boto3's operation and apply to appropriate files.
You only have to select service and operation that you want to add.
This script looks at the botocore's definition file of specified service and operation, and auto-generates codes and reponses.
Basically, this script supports almost all services, as long as its protocol is `query`, `json` or `rest-json`.
Event if aws adds new services, this script will work as long as the protocol is known.

TODO:
  - This scripts don't generates functions in `responses.py` for `rest-json`, because I don't know the rule of it. want someone fix this.
  - In some services's operations, this scripts might crash. Make new issue on github then.
"""
import os
import re
import inspect
import importlib
from lxml import etree

import click
import jinja2
from prompt_toolkit import (
    prompt
)
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.shortcuts import print_tokens

from botocore import xform_name
from botocore.session import Session
import boto3

from moto.core.responses import BaseResponse
from moto.core import BaseBackend
from implementation_coverage import (
    get_moto_implementation
)
from inflection import singularize

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), './template')

INPUT_IGNORED_IN_BACKEND = ['Marker', 'PageSize']
OUTPUT_IGNORED_IN_BACKEND = ['NextMarker']


def print_progress(title, body, color):
    click.secho(u'\t{}\t'.format(title), fg=color, nl=False)
    click.echo(body)


def select_service_and_operation():
    service_names = Session().get_available_services()
    service_completer = WordCompleter(service_names)
    service_name = prompt(u'Select service: ', completer=service_completer)
    if service_name not in service_names:
        click.secho(u'{} is not valid service'.format(service_name), fg='red')
        raise click.Abort()
    moto_client = get_moto_implementation(service_name)
    real_client = boto3.client(service_name, region_name='us-east-1')
    implemented = []
    not_implemented = []

    operation_names = [xform_name(op) for op in real_client.meta.service_model.operation_names]
    for op in operation_names:
        if moto_client and op in dir(moto_client):
            implemented.append(op)
        else:
            not_implemented.append(op)
    operation_completer = WordCompleter(operation_names)

    click.echo('==Current Implementation Status==')
    for operation_name in operation_names:
        check = 'X' if operation_name in implemented else ' '
        click.secho('[{}] {}'.format(check, operation_name))
    click.echo('=================================')
    operation_name = prompt(u'Select Operation: ', completer=operation_completer)

    if operation_name not in operation_names:
        click.secho('{} is not valid operation'.format(operation_name), fg='red')
        raise click.Abort()

    if operation_name in implemented:
        click.secho('{} is already implemented'.format(operation_name), fg='red')
        raise click.Abort()
    return service_name, operation_name

def get_escaped_service(service):
    return service.replace('-', '')

def get_lib_dir(service):
    return os.path.join('moto', get_escaped_service(service))

def get_test_dir(service):
    return os.path.join('tests', 'test_{}'.format(get_escaped_service(service)))


def render_template(tmpl_dir, tmpl_filename, context, service, alt_filename=None):
    is_test = True if 'test' in tmpl_dir else False
    rendered = jinja2.Environment(
        loader=jinja2.FileSystemLoader(tmpl_dir)
    ).get_template(tmpl_filename).render(context)

    dirname = get_test_dir(service) if is_test else get_lib_dir(service)
    filename = alt_filename or os.path.splitext(tmpl_filename)[0]
    filepath = os.path.join(dirname, filename)

    if os.path.exists(filepath):
        print_progress('skip creating', filepath, 'yellow')
    else:
        print_progress('creating', filepath, 'green')
        with open(filepath, 'w') as f:
            f.write(rendered)


def append_mock_to_init_py(service):
    path = os.path.join(os.path.dirname(__file__), '..', 'moto', '__init__.py')
    with open(path) as f:
        lines = [_.replace('\n', '') for _ in f.readlines()]

    if any(_ for _ in lines if re.match('^from.*mock_{}.*$'.format(service), _)):
        return
    filtered_lines = [_ for _ in lines if re.match('^from.*mock.*$', _)]
    last_import_line_index = lines.index(filtered_lines[-1])

    new_line = 'from .{} import mock_{}  # flake8: noqa'.format(get_escaped_service(service), get_escaped_service(service))
    lines.insert(last_import_line_index + 1, new_line)

    body = '\n'.join(lines) + '\n'
    with open(path, 'w') as f:
        f.write(body)


def append_mock_import_to_backends_py(service):
    path = os.path.join(os.path.dirname(__file__), '..', 'moto', 'backends.py')
    with open(path) as f:
        lines = [_.replace('\n', '') for _ in f.readlines()]

    if any(_ for _ in lines if re.match('^from moto\.{}.*{}_backends.*$'.format(service, service), _)):
        return
    filtered_lines = [_ for _ in lines if re.match('^from.*backends.*$', _)]
    last_import_line_index = lines.index(filtered_lines[-1])

    new_line = 'from moto.{} import {}_backends'.format(get_escaped_service(service), get_escaped_service(service))
    lines.insert(last_import_line_index + 1, new_line)

    body = '\n'.join(lines) + '\n'
    with open(path, 'w') as f:
        f.write(body)

def append_mock_dict_to_backends_py(service):
    path = os.path.join(os.path.dirname(__file__), '..', 'moto', 'backends.py')
    with open(path) as f:
        lines = [_.replace('\n', '') for _ in f.readlines()]

    if any(_ for _ in lines if re.match(".*'{}': {}_backends.*".format(service, service), _)):
        return
    filtered_lines = [_ for _ in lines if re.match(".*'.*':.*_backends.*", _)]
    last_elem_line_index = lines.index(filtered_lines[-1])

    new_line = "    '{}': {}_backends,".format(service, get_escaped_service(service))
    prev_line = lines[last_elem_line_index]
    if not prev_line.endswith('{') and not prev_line.endswith(','):
        lines[last_elem_line_index] += ','
    lines.insert(last_elem_line_index + 1, new_line)

    body = '\n'.join(lines) + '\n'
    with open(path, 'w') as f:
        f.write(body)

def initialize_service(service, operation, api_protocol):
    """create lib and test dirs if not exist
    """
    lib_dir = get_lib_dir(service)
    test_dir = get_test_dir(service)

    print_progress('Initializing service', service, 'green')

    client = boto3.client(service)
    service_class = client.__class__.__name__
    endpoint_prefix = client._service_model.endpoint_prefix

    tmpl_context = {
        'service': service,
        'service_class': service_class,
        'endpoint_prefix': endpoint_prefix,
        'api_protocol': api_protocol,
        'escaped_service': get_escaped_service(service)
    }

    # initialize service directory
    if os.path.exists(lib_dir):
        print_progress('skip creating', lib_dir, 'yellow')
    else:
        print_progress('creating', lib_dir, 'green')
        os.makedirs(lib_dir)

    tmpl_dir = os.path.join(TEMPLATE_DIR, 'lib')
    for tmpl_filename in os.listdir(tmpl_dir):
        render_template(
            tmpl_dir, tmpl_filename, tmpl_context, service
        )

    # initialize test directory
    if os.path.exists(test_dir):
        print_progress('skip creating', test_dir, 'yellow')
    else:
        print_progress('creating', test_dir, 'green')
        os.makedirs(test_dir)
    tmpl_dir = os.path.join(TEMPLATE_DIR, 'test')
    for tmpl_filename in os.listdir(tmpl_dir):
        alt_filename = 'test_{}.py'.format(get_escaped_service(service)) if tmpl_filename == 'test_service.py.j2' else None
        render_template(
            tmpl_dir, tmpl_filename, tmpl_context, service, alt_filename
        )

    # append mock to init files
    append_mock_to_init_py(service)
    append_mock_import_to_backends_py(service)
    append_mock_dict_to_backends_py(service)


def to_upper_camel_case(s):
    return ''.join([_.title() for _ in s.split('_')])


def to_lower_camel_case(s):
    words = s.split('_')
    return ''.join(words[:1] + [_.title() for _ in words[1:]])


def to_snake_case(s):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def get_function_in_responses(service, operation, protocol):
    """refers to definition of API in botocore, and autogenerates function
    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    client = boto3.client(service)

    aws_operation_name = to_upper_camel_case(operation)
    op_model = client._service_model.operation_model(aws_operation_name)
    if not hasattr(op_model.output_shape, 'members'):
        outputs = {}
    else:
        outputs = op_model.output_shape.members
    inputs = op_model.input_shape.members
    input_names = [to_snake_case(_) for _ in inputs.keys() if _ not in INPUT_IGNORED_IN_BACKEND]
    output_names = [to_snake_case(_) for _ in outputs.keys() if _ not in OUTPUT_IGNORED_IN_BACKEND]
    body = '\ndef {}(self):\n'.format(operation)

    for input_name, input_type in inputs.items():
        type_name = input_type.type_name
        if type_name == 'integer':
            arg_line_tmpl = '    {} = self._get_int_param("{}")\n'
        elif type_name == 'list':
            arg_line_tmpl = '    {} = self._get_list_prefix("{}.member")\n'
        else:
            arg_line_tmpl = '    {} = self._get_param("{}")\n'
        body += arg_line_tmpl.format(to_snake_case(input_name), input_name)
    if output_names:
        body += '    {} = self.{}_backend.{}(\n'.format(', '.join(output_names), get_escaped_service(service), operation)
    else:
        body += '    self.{}_backend.{}(\n'.format(get_escaped_service(service), operation)
    for input_name in input_names:
        body += '        {}={},\n'.format(input_name, input_name)

    body += '    )\n'
    if protocol == 'query':
        body += '    template = self.response_template({}_TEMPLATE)\n'.format(operation.upper())
        body += '    return template.render({})\n'.format(
            ', '.join(['{}={}'.format(_, _) for _ in output_names])
        )
    elif protocol in ['json', 'rest-json']:
        body += '    # TODO: adjust response\n'
        body += '    return json.dumps(dict({}))\n'.format(', '.join(['{}={}'.format(to_lower_camel_case(_), _) for _ in output_names]))
    return body


def get_function_in_models(service, operation):
    """refers to definition of API in botocore, and autogenerates function
    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    client = boto3.client(service)
    aws_operation_name = to_upper_camel_case(operation)
    op_model = client._service_model.operation_model(aws_operation_name)
    inputs = op_model.input_shape.members
    if not hasattr(op_model.output_shape, 'members'):
        outputs = {}
    else:
        outputs = op_model.output_shape.members
    input_names = [to_snake_case(_) for _ in inputs.keys() if _ not in INPUT_IGNORED_IN_BACKEND]
    output_names = [to_snake_case(_) for _ in outputs.keys() if _ not in OUTPUT_IGNORED_IN_BACKEND]
    if input_names:
        body = 'def {}(self, {}):\n'.format(operation, ', '.join(input_names))
    else:
        body = 'def {}(self)\n'
    body += '    # implement here\n'
    body += '    return {}\n\n'.format(', '.join(output_names))

    return body


def _get_subtree(name, shape, replace_list, name_prefix=[]):
    class_name = shape.__class__.__name__
    if class_name in ('StringShape', 'Shape'):
        t = etree.Element(name)
        if name_prefix:
            t.text = '{{ %s.%s }}' % (name_prefix[-1], to_snake_case(name))
        else:
            t.text = '{{ %s }}' % to_snake_case(name)
        return t
    elif class_name in ('ListShape', ):
        replace_list.append((name, name_prefix))
        t = etree.Element(name)
        t_member = etree.Element('member')
        t.append(t_member)
        for nested_name, nested_shape in shape.member.members.items():
            t_member.append(_get_subtree(nested_name, nested_shape, replace_list, name_prefix + [singularize(name.lower())]))
        return t
    raise ValueError('Not supported Shape')


def get_response_query_template(service, operation):
    """refers to definition of API in botocore, and autogenerates template
    Assume that response format is xml when protocol is query

    You can see example of elbv2 from link below.
      https://github.com/boto/botocore/blob/develop/botocore/data/elbv2/2015-12-01/service-2.json
    """
    client = boto3.client(service)
    aws_operation_name = to_upper_camel_case(operation)
    op_model = client._service_model.operation_model(aws_operation_name)
    result_wrapper = op_model.output_shape.serialization['resultWrapper']
    response_wrapper = result_wrapper.replace('Result', 'Response')
    metadata = op_model.metadata
    xml_namespace = metadata['xmlNamespace']

    # build xml tree
    t_root = etree.Element(response_wrapper,  xmlns=xml_namespace)

    # build metadata
    t_metadata = etree.Element('ResponseMetadata')
    t_request_id = etree.Element('RequestId')
    t_request_id.text = '1549581b-12b7-11e3-895e-1334aEXAMPLE'
    t_metadata.append(t_request_id)
    t_root.append(t_metadata)

    # build result
    t_result = etree.Element(result_wrapper)
    outputs = op_model.output_shape.members
    replace_list = []
    for output_name, output_shape in outputs.items():
        t_result.append(_get_subtree(output_name, output_shape, replace_list))
    t_root.append(t_result)
    xml_body = etree.tostring(t_root, pretty_print=True).decode('utf-8')
    xml_body_lines = xml_body.splitlines()
    for replace in replace_list:
        name = replace[0]
        prefix = replace[1]
        singular_name = singularize(name)

        start_tag = '<%s>' % name
        iter_name = '{}.{}'.format(prefix[-1], name.lower())if prefix else name.lower()
        loop_start = '{%% for %s in %s %%}' % (singular_name.lower(), iter_name)
        end_tag = '</%s>' % name
        loop_end = '{{ endfor }}'

        start_tag_indexes = [i for i, l in enumerate(xml_body_lines) if start_tag in l]
        if len(start_tag_indexes) != 1:
            raise Exception('tag %s not found in response body' % start_tag)
        start_tag_index = start_tag_indexes[0]
        xml_body_lines.insert(start_tag_index + 1, loop_start)

        end_tag_indexes = [i for i, l in enumerate(xml_body_lines) if end_tag in l]
        if len(end_tag_indexes) != 1:
            raise Exception('tag %s not found in response body' % end_tag)
        end_tag_index = end_tag_indexes[0]
        xml_body_lines.insert(end_tag_index, loop_end)
    xml_body = '\n'.join(xml_body_lines)
    body = '\n{}_TEMPLATE = """{}"""'.format(operation.upper(), xml_body)
    return body


def insert_code_to_class(path, base_class, new_code):
    with open(path) as f:
        lines = [_.replace('\n', '') for _ in f.readlines()]
    mod_path = os.path.splitext(path)[0].replace('/', '.')
    mod = importlib.import_module(mod_path)
    clsmembers = inspect.getmembers(mod, inspect.isclass)
    _response_cls = [_[1] for _ in clsmembers if issubclass(_[1], base_class) and _[1] != base_class]
    if len(_response_cls) != 1:
        raise Exception('unknown error, number of clsmembers is not 1')
    response_cls = _response_cls[0]
    code_lines, line_no = inspect.getsourcelines(response_cls)
    end_line_no = line_no + len(code_lines)

    func_lines = [' ' * 4 + _ for _ in new_code.splitlines()]

    lines = lines[:end_line_no] + func_lines + lines[end_line_no:]

    body = '\n'.join(lines) + '\n'
    with open(path, 'w') as f:
        f.write(body)


def insert_url(service, operation, api_protocol):
    client = boto3.client(service)
    service_class = client.__class__.__name__
    aws_operation_name = to_upper_camel_case(operation)
    uri = client._service_model.operation_model(aws_operation_name).http['requestUri']

    path = os.path.join(os.path.dirname(__file__), '..', 'moto', get_escaped_service(service), 'urls.py')
    with open(path) as f:
        lines = [_.replace('\n', '') for _ in f.readlines()]

    if any(_ for _ in lines if re.match(uri, _)):
        return

    url_paths_found = False
    last_elem_line_index = -1
    for i, line in enumerate(lines):
        if line.startswith('url_paths'):
            url_paths_found = True
        if url_paths_found and line.startswith('}'):
            last_elem_line_index = i - 1

    prev_line = lines[last_elem_line_index]
    if not prev_line.endswith('{') and not prev_line.endswith(','):
        lines[last_elem_line_index] += ','

    # generate url pattern
    if api_protocol == 'rest-json':
        new_line = "    '{0}/.*$': response.dispatch,"
    else:
        new_line = "    '{0}%s$': %sResponse.dispatch," % (
            uri, service_class
        )
    if new_line in lines:
        return
    lines.insert(last_elem_line_index + 1, new_line)

    body = '\n'.join(lines) + '\n'
    with open(path, 'w') as f:
        f.write(body)

def insert_codes(service, operation, api_protocol):
    func_in_responses = get_function_in_responses(service, operation, api_protocol)
    func_in_models = get_function_in_models(service, operation)
    # edit responses.py
    responses_path = 'moto/{}/responses.py'.format(get_escaped_service(service))
    print_progress('inserting code', responses_path, 'green')
    insert_code_to_class(responses_path, BaseResponse, func_in_responses)

    # insert template
    if api_protocol == 'query':
        template = get_response_query_template(service, operation)
        with open(responses_path) as f:
            lines = [_[:-1] for _ in f.readlines()]
        lines += template.splitlines()
        with open(responses_path, 'w') as f:
            f.write('\n'.join(lines))

    # edit models.py
    models_path = 'moto/{}/models.py'.format(get_escaped_service(service))
    print_progress('inserting code', models_path, 'green')
    insert_code_to_class(models_path, BaseBackend, func_in_models)

    # edit urls.py
    insert_url(service, operation, api_protocol)


@click.command()
def main():
    service, operation = select_service_and_operation()
    api_protocol = boto3.client(service)._service_model.metadata['protocol']
    initialize_service(service, operation, api_protocol)

    if api_protocol in ['query', 'json', 'rest-json']:
        insert_codes(service, operation, api_protocol)
    else:
        print_progress('skip inserting code', 'api protocol "{}" is not supported'.format(api_protocol), 'yellow')

    click.echo('You will still need to add the mock into "__init__.py"'.format(service))

if __name__ == '__main__':
    main()
