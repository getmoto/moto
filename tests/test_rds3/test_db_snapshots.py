from __future__ import unicode_literals

from botocore.exceptions import ClientError, ParamValidationError
import boto3
from sure import this  # noqa
from . import mock_kms, mock_rds2


@mock_rds2
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


@mock_rds2
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


@mock_rds2
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


@mock_rds2
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