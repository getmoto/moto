from __future__ import unicode_literals

# noinspection PyPackageRequirements
import boto3
from botocore.exceptions import ClientError

from . import mock_rds

# import sure  # noqa
from sure import this


test_tags = [
    {"Key": "foo", "Value": "bar",},
    {"Key": "foo1", "Value": "bar1",},
]


# @mock_rds
# def test_create_db_cluster():
#     client = boto3.client('rds', region_name='us-west-2')
#     cluster = client.create_db_cluster(DBClusterIdentifier='cluster-1',
#                                        DatabaseName='db_name',
#                                        Engine='aurora-postgresql',
#                                        MasterUsername='root',
#                                        MasterUserPassword='password',
#                                        Port=1234,
#                                        Tags=test_tags).get('DBCluster')
#     this(cluster['DBClusterIdentifier']).should.equal('cluster-1')
#     tag_list = client.list_tags_for_resource(ResourceName=cluster['DBClusterArn']).get('TagList')
#     this(tag_list).should.equal(test_tags)
#
#
# @mock_rds
# def test_create_db_cluster_with_invalid_engine_fails():
#     client = boto3.client('rds', region_name='us-west-2')
#     client.create_db_cluster.when.called_with(
#         DBClusterIdentifier='cluster-1',
#         Engine='bad-engine-value',
#         MasterUsername='root',
#         MasterUserPassword='password'
#     ).should.throw(ClientError, 'Invalid DB engine')
#
#
# @mock_rds
# def test_create_db_cluster_with_invalid_engine_version_fails():
#     client = boto3.client('rds', region_name='us-west-2')
#     client.create_db_cluster.when.called_with(
#         DBClusterIdentifier='cluster-1',
#         Engine='aurora-postgresql',
#         EngineVersion='1.0',
#         MasterUsername='root',
#         MasterUserPassword='password'
#     ).should.throw(ClientError, 'Cannot find version 1.0 for aurora-postgresql')
#
#
# @mock_rds
# def test_add_remove_db_instance_from_db_cluster():
#     client = boto3.client('rds', region_name='us-west-2')
#     cluster = client.create_db_cluster(DBClusterIdentifier='cluster-1',
#                                        DatabaseName='db_name',
#                                        Engine='aurora-postgresql',
#                                        MasterUsername='root',
#                                        MasterUserPassword='password').get('DBCluster')
#     cluster['DBClusterMembers'].should.have.length_of(0)
#     client.create_db_instance(DBInstanceIdentifier='test-instance',
#                               DBInstanceClass='db.m1.small',
#                               Engine='aurora-postgresql',
#                               DBClusterIdentifier='cluster-1')
#     cluster = client.describe_db_clusters(DBClusterIdentifier='cluster-1').get('DBClusters')[0]
#     cluster['DBClusterMembers'].should.have.length_of(1)
#     client.delete_db_instance(DBInstanceIdentifier='test-instance')
#     cluster = client.describe_db_clusters(DBClusterIdentifier='cluster-1').get('DBClusters')[0]
#     cluster['DBClusterMembers'].should.have.length_of(0)


@mock_rds
def test_describe_db_cluster_parameter_groups_paginated():
    client = boto3.client("rds", region_name="us-west-2")
    default_groups = client.describe_db_cluster_parameter_groups(MaxRecords=20).get(
        "DBClusterParameterGroups"
    )
    custom_group_start = len(default_groups)
    for i in range(custom_group_start, 21):
        client.create_db_cluster_parameter_group(
            DBClusterParameterGroupName="cluster-pg-{}".format(i),
            DBParameterGroupFamily="aurora-postgresql9.6",
            Description="test description",
        )

    resp = client.describe_db_cluster_parameter_groups(MaxRecords=20)
    groups = resp.get("DBClusterParameterGroups")
    groups.should.have.length_of(20)
    groups[custom_group_start]["DBClusterParameterGroupName"].should.equal(
        "cluster-pg-{}".format(custom_group_start)
    )

    groups = client.describe_db_cluster_parameter_groups(Marker=resp["Marker"]).get(
        "DBClusterParameterGroups"
    )
    groups.should.have.length_of(1)
    groups[0]["DBClusterParameterGroupName"].should.equal("cluster-pg-20")

    all_groups = client.describe_db_cluster_parameter_groups().get(
        "DBClusterParameterGroups"
    )
    all_groups.should.have.length_of(21)


@mock_rds
def test_describe_default_db_cluster_parameter_groups():
    client = boto3.client("rds", region_name="us-west-2")
    groups = client.describe_db_cluster_parameter_groups().get(
        "DBClusterParameterGroups"
    )
    len(groups).should.be.greater_than(0)
    for group in groups:
        group["DBClusterParameterGroupName"].should.match(r"^default")


@mock_rds
def test_describe_non_existent_db_cluster_parameter_group_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.describe_db_cluster_parameter_groups.when.called_with(
        DBClusterParameterGroupName="non-existent"
    ).should.throw(ClientError, "not found")


# @mock_rds
# def test_delete_db_cluster():
#     client = boto3.client('rds', region_name='us-west-2')
#     client.create_db_cluster(DBClusterIdentifier='cluster-1',
#                              DatabaseName='db_name',
#                              Engine='aurora-postgresql',
#                              MasterUsername='root',
#                              MasterUserPassword='password',
#                              Port=1234)
#     cluster = client.delete_db_cluster(DBClusterIdentifier='cluster-1').get('DBCluster')
#     cluster['DBClusterIdentifier'].should.equal('cluster-1')
#     # TODO: skipfinalsnapshot stuff
#
#
@mock_rds
def test_delete_non_existent_db_cluster_parameter_group_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.delete_db_cluster_parameter_group.when.called_with(
        DBClusterParameterGroupName="non-existent"
    ).should.throw(ClientError, "not found")


#
#
# @mock_rds
# def test_delete_db_cluster_with_active_members_fails():
#     client = boto3.client('rds', region_name='us-west-2')
#     client.create_db_cluster(DBClusterIdentifier='cluster-1',
#                              DatabaseName='db_name',
#                              Engine='aurora-postgresql',
#                              MasterUsername='root',
#                              MasterUserPassword='password',
#                              Port=1234)
#     client.create_db_instance(DBInstanceIdentifier='test-instance',
#                               DBInstanceClass='db.m1.small',
#                               Engine='aurora-postgresql',
#                               DBClusterIdentifier='cluster-1')
#     client.delete_db_cluster.when.called_with(
#         DBClusterIdentifier='cluster-1').should.throw(ClientError, 'Cluster cannot be deleted')
