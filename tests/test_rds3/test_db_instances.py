from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError

from . import mock_rds
from sure import this


@mock_rds
def test_specifying_availability_zone_with_multi_az_fails():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance.when.called_with(
        DBInstanceIdentifier='test-instance',
        AllocatedStorage=10,
        Engine='postgres',
        DBName='test-db',
        DBInstanceClass='db.m4.large',
        MasterUsername='root',
        MasterUserPassword='password',
        MultiAZ=True,
        AvailabilityZone='us-west-2a'
    ).should.throw(ClientError, 'Requesting a specific availability zone is not valid for Multi-AZ instances.')


@mock_rds
def test_create_duplicate_db_instance_fails():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance(
        DBInstanceIdentifier='test-instance',
        AllocatedStorage=10,
        Engine='postgres',
        DBName='test-db',
        DBInstanceClass='db.m4.large',
        MasterUsername='root',
        MasterUserPassword='password',
    )
    client.create_db_instance.when.called_with(
        DBInstanceIdentifier='test-instance',
        AllocatedStorage=10,
        Engine='postgres',
        DBName='test-db',
        DBInstanceClass='db.m4.large',
        MasterUsername='root',
        MasterUserPassword='password',
    ).should.throw(ClientError, 'DB Instance already exists')


@mock_rds
def test_db_instance_events():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance(
        DBInstanceIdentifier='test-instance',
        AllocatedStorage=10,
        Engine='postgres',
        DBName='test-db',
        DBInstanceClass='db.m4.large',
        MasterUsername='root',
        MasterUserPassword='password',
    )
    events = client.describe_events(
        SourceIdentifier='test-instance',
        SourceType='db-instance'
    ).get('Events')
    this(len(events)).should.be.greater_than(0)
