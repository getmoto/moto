from __future__ import unicode_literals

from botocore.exceptions import ClientError, ParamValidationError
import boto3
from sure import this  # noqa
from . import mock_kms, mock_rds


test_tags = [
    {
        'Key': 'foo',
        'Value': 'bar',
    },
    {
        'Key': 'foo1',
        'Value': 'bar1',
    },
]

@mock_rds
def test_create_db_snapshot():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_snapshot.when.called_with(
        DBInstanceIdentifier='db-primary-1',
        DBSnapshotIdentifier='snapshot-1').should.throw(ClientError)

    conn.create_db_instance(DBInstanceIdentifier='db-primary-1',
                            AllocatedStorage=10,
                            Engine='postgres',
                            DBName='staging-postgres',
                            DBInstanceClass='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=["my_sg"],
                            StorageEncrypted=True)

    snapshot = conn.create_db_snapshot(DBInstanceIdentifier='db-primary-1',
                                       DBSnapshotIdentifier='g-1').get('DBSnapshot')

    snapshot.get('Engine').should.equal('postgres')
    snapshot.get('DBInstanceIdentifier').should.equal('db-primary-1')
    snapshot.get('DBSnapshotIdentifier').should.equal('g-1')

@mock_rds
def test_describe_db_snapshots_paginated():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance(
        DBInstanceIdentifier='instance-1',
        DatabaseName='db_name',
        Engine='postgres',
        MasterUsername='root',
        MasterUserPassword='password',
        Port=1234,
        Tags=test_tags)
    auto_snapshots = client.describe_db_snapshots(MaxRecords=20).get('DBSnapshots')
    custom_snap_start = len(auto_snapshots)
    for i in range(custom_snap_start, 21):
        client.create_db_snapshot(
            DBSnapshotIdentifier='instance-snap-{}'.format(i),
            DBClusterIdentifier='instance-1'
        )

    resp = client.describe_db_snapshots(MaxRecords=20)
    snaps = resp.get('DBSnapshots')
    snaps.should.have.length_of(20)
    snaps[custom_snap_start]['DBSnapshotIdentifier'].should.equal('instance-snap-{}'.format(custom_snap_start))

    resp2 = client.describe_db_snapshots(Marker=resp['Marker'])
    resp2['DBSnapshots'].should.have.length_of(1)
    resp2['DBSnapshots'][0]['DBSnapshotIdentifier'].should.equal('instance-snap-20')

    resp3 = client.describe_db_snapshots()
    resp3['DBSnapshots'].should.have.length_of(21)

@mock_rds
def test_copy_unencrypted_db_snapshot_to_encrypted_db_snapshot():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance(DBInstanceIdentifier='unencrypted-db-instance',
                              AllocatedStorage=10,
                              Engine='postgres',
                              DBName='staging-postgres',
                              DBInstanceClass='db.m1.small',
                              MasterUsername='root',
                              MasterUserPassword='pass',
                              StorageEncrypted=False)
    snapshot = client.create_db_snapshot(DBInstanceIdentifier='unencrypted-db-instance',
                                         DBSnapshotIdentifier='unencrypted-db-snapshot').get('DBSnapshot')
    snapshot['Encrypted'].should.equal(False)

    client.copy_db_snapshot(SourceDBSnapshotIdentifier='unencrypted-db-snapshot',
                            TargetDBSnapshotIdentifier='encrypted-db-snapshot',
                            KmsKeyId='alias/aws/rds')
    snapshot = client.describe_db_snapshots(DBSnapshotIdentifier='encrypted-db-snapshot').get('DBSnapshots')[0]
    snapshot['DBSnapshotIdentifier'].should.equal('encrypted-db-snapshot')
    snapshot['Encrypted'].should.equal(True)


@mock_rds
def test_db_snapshot_events():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance(DBInstanceIdentifier='test-instance',
                              AllocatedStorage=10,
                              Engine='postgres',
                              DBName='staging-postgres',
                              DBInstanceClass='db.m1.small',
                              MasterUsername='root',
                              MasterUserPassword='pass',
                              StorageEncrypted=False)
    # Automated snapshots
    snapshot = client.describe_db_snapshots(
        DBInstanceIdentifier='test-instance'
    ).get('DBSnapshots')[0]
    events = client.describe_events(
        SourceIdentifier=snapshot['DBSnapshotIdentifier'],
        SourceType='db-snapshot'
    ).get('Events')
    this(len(events)).should.be.greater_than(0)
    # Manual snapshot events
    client.create_db_snapshot(DBInstanceIdentifier='test-instance',
                              DBSnapshotIdentifier='test-snapshot')
    events = client.describe_events(
        SourceIdentifier='test-snapshot',
        SourceType='db-snapshot'
    ).get('Events')
    this(len(events)).should.be.greater_than(0)


@mock_rds
def test_create_db_snapshot_with_invalid_identifier_fails():
    client = boto3.client('rds', region_name='us-west-2')
    client.create_db_instance(
        DBInstanceIdentifier='db-primary-1',
        AllocatedStorage=10,
        Engine='postgres',
        DBName='staging-postgres',
        DBInstanceClass='db.m1.small',
        MasterUsername='root',
        MasterUserPassword='pass',
    )
    client.create_db_snapshot.when.called_with(
        DBInstanceIdentifier='db-primary-1',
        DBSnapshotIdentifier='rds:snapshot-1'
    ).should.throw(ClientError, 'not a valid identifier')