#!/usr/bin/env python
import os

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

from implementation_coverage import (
    get_moto_implementation
)
TEMPLATE_DIR = './template'


def print_progress(title, body, color):
    click.secho('\t{}\t'.format(title), fg=color, nl=False)
    click.echo(body)


def select_service_and_operation():
    service_names = Session().get_available_services()
    service_completer = WordCompleter(service_names)
    service_name = prompt('Select service: ', completer=service_completer)
    if service_name not in service_names:
        click.secho('{} is not valid service'.format(service_name), fg='red')
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
    operation_name = prompt('Select Operation: ', completer=operation_completer)

    if operation_name not in operation_names:
        click.secho('{} is not valid operation'.format(operation_name), fg='red')
        raise click.Abort()

    if operation_name in implemented:
        click.secho('{} is already implemented'.format(operation_name), fg='red')
        raise click.Abort()
    return service_name, operation_name


def get_lib_dir(service):
    return os.path.join('moto', service)

def get_test_dir(service):
    return os.path.join('tests', 'test_{}'.format(service))


def render_teamplte(tmpl_dir, tmpl_filename, context, service, alt_filename=None):
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


def initialize_service(service, operation):
    """create lib and test dirs if not exist
    """
    lib_dir = os.path.join('moto', service)
    test_dir = os.path.join('tests', 'test_{}'.format(service))

    print_progress('Initializing service', service, 'green')

    service_class = boto3.client(service).__class__.__name__

    tmpl_context = {
        'service': service,
        'service_class': service_class
    }

    # initialize service directory
    if os.path.exists(lib_dir):
        print_progress('skip creating', lib_dir, 'yellow')
    else:
        print_progress('creating', lib_dir, 'green')
        os.makedirs(lib_dir)

    tmpl_dir = os.path.join(TEMPLATE_DIR, 'lib')
    for tmpl_filename in os.listdir(tmpl_dir):
        render_teamplte(
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
        alt_filename = 'test_{}.py'.format(service) if tmpl_filename == 'test_service.py.j2' else None
        render_teamplte(
            tmpl_dir, tmpl_filename, tmpl_context, service, alt_filename
        )


@click.command()
def main():
    service, operation = select_service_and_operation()
    initialize_service(service, operation)

if __name__ == '__main__':
    main()
