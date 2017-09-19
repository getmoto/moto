#!/usr/bin/env python
import os

import click
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


def create_dirs(service, operation):
    """create lib and test dirs if not exist
    """
    lib_dir = os.path.join('moto', service)
    test_dir = os.path.join('test', 'test_{}'.format(service))
    if os.path.exists(lib_dir):
        return

    click.secho('\tInitializing service\t', fg='green', nl=False)
    click.secho(service)

    click.secho('\tcraeting\t', fg='green', nl=False)
    click.echo(lib_dir)
    os.mkdirs(lib_dir)
    # do init lib dir

    if not os.path.exists(test_dir):
        click.secho('\tcraeting\t', fg='green', nl=False)
        click.echo(test_dir)
        os.mkdirs(test_dir)
        # do init test dir


@click.command()
def main():
    service, operation = select_service_and_operation()
    create_dirs(service, operation)

if __name__ == '__main__':
    main()
