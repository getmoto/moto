from __future__ import unicode_literals

import sure  # noqa
import re
from nose.tools import assert_raises
import boto3
from botocore.client import ClientError


from datetime import datetime
import pytz

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

    exc.exception.response['Error']['Code'].should.equal('AlreadyExistsException')


@mock_glue
def test_get_database_not_exits():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'nosuchdatabase'

    with assert_raises(ClientError) as exc:
        helpers.get_database(client, database_name)

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('Database nosuchdatabase not found')


@mock_glue
def test_create_table():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_name = 'myspecialtable'
    table_input = helpers.create_table_input(database_name, table_name)
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
    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        helpers.create_table(client, database_name, table_name)

    exc.exception.response['Error']['Code'].should.equal('AlreadyExistsException')


@mock_glue
def test_get_tables():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_names = ['myfirsttable', 'mysecondtable', 'mythirdtable']
    table_inputs = {}

    for table_name in table_names:
        table_input = helpers.create_table_input(database_name, table_name)
        table_inputs[table_name] = table_input
        helpers.create_table(client, database_name, table_name, table_input)

    response = helpers.get_tables(client, database_name)

    tables = response['TableList']

    tables.should.have.length_of(3)

    for table in tables:
        table_name = table['Name']
        table_name.should.equal(table_inputs[table_name]['Name'])
        table['StorageDescriptor'].should.equal(table_inputs[table_name]['StorageDescriptor'])
        table['PartitionKeys'].should.equal(table_inputs[table_name]['PartitionKeys'])


@mock_glue
def test_get_table_versions():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_name = 'myfirsttable'
    version_inputs = {}

    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)
    version_inputs["1"] = table_input

    columns = [{'Name': 'country', 'Type': 'string'}]
    table_input = helpers.create_table_input(database_name, table_name, columns=columns)
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["2"] = table_input

    # Updateing with an indentical input should still create a new version
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["3"] = table_input

    response = helpers.get_table_versions(client, database_name, table_name)

    vers = response['TableVersions']

    vers.should.have.length_of(3)
    vers[0]['Table']['StorageDescriptor']['Columns'].should.equal([])
    vers[-1]['Table']['StorageDescriptor']['Columns'].should.equal(columns)

    for n, ver in enumerate(vers):
        n = str(n + 1)
        ver['VersionId'].should.equal(n)
        ver['Table']['Name'].should.equal(table_name)
        ver['Table']['StorageDescriptor'].should.equal(version_inputs[n]['StorageDescriptor'])
        ver['Table']['PartitionKeys'].should.equal(version_inputs[n]['PartitionKeys'])

    response = helpers.get_table_version(client, database_name, table_name, "3")
    ver = response['TableVersion']

    ver['VersionId'].should.equal("3")
    ver['Table']['Name'].should.equal(table_name)
    ver['Table']['StorageDescriptor']['Columns'].should.equal(columns)


@mock_glue
def test_get_table_version_not_found():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        helpers.get_table_version(client, database_name, 'myfirsttable', "20")

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('version', re.I)


@mock_glue
def test_get_table_version_invalid_input():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        helpers.get_table_version(client, database_name, 'myfirsttable', "10not-an-int")

    exc.exception.response['Error']['Code'].should.equal('InvalidInputException')


@mock_glue
def test_get_table_not_exits():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    with assert_raises(ClientError) as exc:
        helpers.get_table(client, database_name, 'myfirsttable')

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('Table myfirsttable not found')


@mock_glue
def test_get_table_when_database_not_exits():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'nosuchdatabase'

    with assert_raises(ClientError) as exc:
        helpers.get_table(client, database_name, 'myfirsttable')

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('Database nosuchdatabase not found')


@mock_glue
def test_delete_table():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_name = 'myspecialtable'
    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)

    result = client.delete_table(DatabaseName=database_name, Name=table_name)
    result['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    # confirm table is deleted
    with assert_raises(ClientError) as exc:
        helpers.get_table(client, database_name, table_name)

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('Table myspecialtable not found')

@mock_glue
def test_batch_delete_table():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    helpers.create_database(client, database_name)

    table_name = 'myspecialtable'
    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)

    result = client.batch_delete_table(DatabaseName=database_name, TablesToDelete=[table_name])
    result['ResponseMetadata']['HTTPStatusCode'].should.equal(200)

    # confirm table is deleted
    with assert_raises(ClientError) as exc:
        helpers.get_table(client, database_name, table_name)

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('Table myspecialtable not found')


@mock_glue
def test_get_partitions_empty():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    response['Partitions'].should.have.length_of(0)


@mock_glue
def test_create_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    before = datetime.now(pytz.utc)

    part_input = helpers.create_partition_input(database_name, table_name, values=values)
    helpers.create_partition(client, database_name, table_name, part_input)

    after = datetime.now(pytz.utc)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    partitions = response['Partitions']

    partitions.should.have.length_of(1)

    partition = partitions[0]

    partition['TableName'].should.equal(table_name)
    partition['StorageDescriptor'].should.equal(part_input['StorageDescriptor'])
    partition['Values'].should.equal(values)
    partition['CreationTime'].should.be.greater_than(before)
    partition['CreationTime'].should.be.lower_than(after)


@mock_glue
def test_create_partition_already_exist():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    helpers.create_partition(client, database_name, table_name, values=values)

    with assert_raises(ClientError) as exc:
        helpers.create_partition(client, database_name, table_name, values=values)

    exc.exception.response['Error']['Code'].should.equal('AlreadyExistsException')


@mock_glue
def test_get_partition_not_found():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        helpers.get_partition(client, database_name, table_name, values)

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('partition')

@mock_glue
def test_batch_create_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    before = datetime.now(pytz.utc)

    partition_inputs = []
    for i in range(0, 20):
        values = ["2018-10-{:2}".format(i)]
        part_input = helpers.create_partition_input(database_name, table_name, values=values)
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs
    )

    after = datetime.now(pytz.utc)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    partitions = response['Partitions']

    partitions.should.have.length_of(20)

    for idx, partition in enumerate(partitions):
        partition_input = partition_inputs[idx]

        partition['TableName'].should.equal(table_name)
        partition['StorageDescriptor'].should.equal(partition_input['StorageDescriptor'])
        partition['Values'].should.equal(partition_input['Values'])
        partition['CreationTime'].should.be.greater_than(before)
        partition['CreationTime'].should.be.lower_than(after)


@mock_glue
def test_batch_create_partition_already_exist():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    helpers.create_partition(client, database_name, table_name, values=values)

    partition_input = helpers.create_partition_input(database_name, table_name, values=values)

    response = client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=[partition_input]
    )

    response.should.have.key('Errors')
    response['Errors'].should.have.length_of(1)
    response['Errors'][0]['PartitionValues'].should.equal(values)
    response['Errors'][0]['ErrorDetail']['ErrorCode'].should.equal('AlreadyExistsException')


@mock_glue
def test_get_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    values = [['2018-10-01'], ['2018-09-01']]

    helpers.create_partition(client, database_name, table_name, values=values[0])
    helpers.create_partition(client, database_name, table_name, values=values[1])

    response = client.get_partition(DatabaseName=database_name, TableName=table_name, PartitionValues=values[1])

    partition = response['Partition']

    partition['TableName'].should.equal(table_name)
    partition['Values'].should.equal(values[1])


@mock_glue
def test_update_partition_not_found_moving():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        helpers.update_partition(client, database_name, table_name, old_values=['0000-00-00'], values=['2018-10-02'])

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('partition')


@mock_glue
def test_update_partition_not_found_change_in_place():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        helpers.update_partition(client, database_name, table_name, old_values=values, values=values)

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')
    exc.exception.response['Error']['Message'].should.match('partition')


@mock_glue
def test_update_partition_cannot_overwrite():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    values = [['2018-10-01'], ['2018-09-01']]

    helpers.create_partition(client, database_name, table_name, values=values[0])
    helpers.create_partition(client, database_name, table_name, values=values[1])

    with assert_raises(ClientError) as exc:
        helpers.update_partition(client, database_name, table_name, old_values=values[0], values=values[1])

    exc.exception.response['Error']['Code'].should.equal('AlreadyExistsException')


@mock_glue
def test_update_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)
    helpers.create_partition(client, database_name, table_name, values=values)

    response = helpers.update_partition(
        client,
        database_name,
        table_name,
        old_values=values,
        values=values,
        columns=[{'Name': 'country', 'Type': 'string'}],
    )

    response = client.get_partition(DatabaseName=database_name, TableName=table_name, PartitionValues=values)
    partition = response['Partition']

    partition['TableName'].should.equal(table_name)
    partition['StorageDescriptor']['Columns'].should.equal([{'Name': 'country', 'Type': 'string'}])


@mock_glue
def test_update_partition_move():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    new_values = ['2018-09-01']

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)
    helpers.create_partition(client, database_name, table_name, values=values)

    response = helpers.update_partition(
        client,
        database_name,
        table_name,
        old_values=values,
        values=new_values,
        columns=[{'Name': 'country', 'Type': 'string'}],
    )

    with assert_raises(ClientError) as exc:
        helpers.get_partition(client, database_name, table_name, values)

    # Old partition shouldn't exist anymore
    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')

    response = client.get_partition(DatabaseName=database_name, TableName=table_name, PartitionValues=new_values)
    partition = response['Partition']

    partition['TableName'].should.equal(table_name)
    partition['StorageDescriptor']['Columns'].should.equal([{'Name': 'country', 'Type': 'string'}])

@mock_glue
def test_delete_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    part_input = helpers.create_partition_input(database_name, table_name, values=values)
    helpers.create_partition(client, database_name, table_name, part_input)

    client.delete_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionValues=values,
    )

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)
    partitions = response['Partitions']
    partitions.should.be.empty

@mock_glue
def test_delete_partition_bad_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    values = ['2018-10-01']
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with assert_raises(ClientError) as exc:
        client.delete_partition(
            DatabaseName=database_name,
            TableName=table_name,
            PartitionValues=values,
        )

    exc.exception.response['Error']['Code'].should.equal('EntityNotFoundException')

@mock_glue
def test_batch_delete_partition():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    partition_inputs = []
    for i in range(0, 20):
        values = ["2018-10-{:2}".format(i)]
        part_input = helpers.create_partition_input(database_name, table_name, values=values)
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs
    )

    partition_values = [{"Values": p["Values"]} for p in partition_inputs]

    response = client.batch_delete_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionsToDelete=partition_values,
    )

    response.should_not.have.key('Errors')

@mock_glue
def test_batch_delete_partition_with_bad_partitions():
    client = boto3.client('glue', region_name='us-east-1')
    database_name = 'myspecialdatabase'
    table_name = 'myfirsttable'
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    partition_inputs = []
    for i in range(0, 20):
        values = ["2018-10-{:2}".format(i)]
        part_input = helpers.create_partition_input(database_name, table_name, values=values)
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs
    )

    partition_values = [{"Values": p["Values"]} for p in partition_inputs]

    partition_values.insert(5, {"Values": ["2018-11-01"]})
    partition_values.insert(10, {"Values": ["2018-11-02"]})
    partition_values.insert(15, {"Values": ["2018-11-03"]})

    response = client.batch_delete_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionsToDelete=partition_values,
    )

    response.should.have.key('Errors')
    response['Errors'].should.have.length_of(3)
    error_partitions = map(lambda x: x['PartitionValues'], response['Errors'])
    ['2018-11-01'].should.be.within(error_partitions)
    ['2018-11-02'].should.be.within(error_partitions)
    ['2018-11-03'].should.be.within(error_partitions)
