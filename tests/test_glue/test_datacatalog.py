from __future__ import unicode_literals

import sure  # noqa
from nose.tools import assert_raises
import boto3
from botocore.client import ClientError

from moto import mock_glue
from . import helpers


@mock_glue
def test_create_database():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    response = helpers.get_database(client, database_name)
    database = response['Database']

    database.should.equal({'Name': database_name})


@mock_glue
def test_create_database_already_exists():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'cantcreatethisdatabasetwice'
    helpers.create_database(client, database_name)

    with assert_raises(ClientError) as exc:
        helpers.create_database(client, database_name)

    exc.exception.response['Error']['Code'].should.equal('DatabaseAlreadyExistsException')


@mock_glue
def test_create_table():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_name = 'myspecialtable'
    s3_location = 's3://my-bucket/{database_name}/{table_name}'.format(
        database_name=database_name,
        table_name=table_name
    )

    table_input = helpers.create_table_input(table_name, s3_location)
    helpers.create_table(client, database_name, table_name, table_input)

    response = helpers.get_table(client, database_name, table_name)
    table = response['Table']

    table['Name'].should.equal(table_input['Name'])
    table['StorageDescriptor'].should.equal(table_input['StorageDescriptor'])
    table['PartitionKeys'].should.equal(table_input['PartitionKeys'])


@mock_glue
def test_create_table_already_exists():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_name = 'cantcreatethistabletwice'
    s3_location = 's3://my-bucket/{database_name}/{table_name}'.format(
        database_name=database_name,
        table_name=table_name
    )

    table_input = helpers.create_table_input(table_name, s3_location)
    helpers.create_table(client, database_name, table_name, table_input)

    with assert_raises(ClientError) as exc:
        helpers.create_table(client, database_name, table_name, table_input)

    exc.exception.response['Error']['Code'].should.equal('TableAlreadyExistsException')


@mock_glue
def test_get_tables():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_names = ['myfirsttable', 'mysecondtable', 'mythirdtable']
    table_inputs = {}

    for table_name in table_names:
        s3_location = 's3://my-bucket/{database_name}/{table_name}'.format(
            database_name=database_name,
            table_name=table_name
        )
        table_input = helpers.create_table_input(table_name, s3_location)
        table_inputs[table_name] = table_input
        helpers.create_table(client, database_name, table_name, table_input)

    response = helpers.get_tables(client, database_name)

    tables = response['TableList']

    assert len(tables) == 3

    for table in tables:
        table_name = table['Name']
        table_name.should.equal(table_inputs[table_name]['Name'])
        table['StorageDescriptor'].should.equal(table_inputs[table_name]['StorageDescriptor'])
        table['PartitionKeys'].should.equal(table_inputs[table_name]['PartitionKeys'])
