from __future__ import unicode_literals

import datetime

import boto
import boto3
from boto.redshift.exceptions import (
    ClusterNotFound,
    ClusterParameterGroupNotFound,
    ClusterSecurityGroupNotFound,
    ClusterSubnetGroupNotFound,
    InvalidSubnet
)
from botocore.exceptions import (
    ClientError
)
import sure  # noqa

from moto import mock_ec2
from moto import mock_ec2_deprecated
from moto import mock_redshift
from moto import mock_redshift_deprecated


@mock_redshift
def test_create_cluster_boto3():
    client = boto3.client('redshift', region_name='us-east-1')
    response = client.create_cluster(
        DBName='test',
        ClusterIdentifier='test',
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='user',
        MasterUserPassword='password',
    )
    response['Cluster']['NodeType'].should.equal('ds2.xlarge')
    create_time = response['Cluster']['ClusterCreateTime']
    create_time.should.be.lower_than(datetime.datetime.now(create_time.tzinfo))
    create_time.should.be.greater_than(datetime.datetime.now(create_time.tzinfo) - datetime.timedelta(minutes=1))


@mock_redshift
def test_create_snapshot_copy_grant():
    client = boto3.client('redshift', region_name='us-east-1')
    grants = client.create_snapshot_copy_grant(
        SnapshotCopyGrantName='test-us-east-1',
        KmsKeyId='fake',
    )
    grants['SnapshotCopyGrant']['SnapshotCopyGrantName'].should.equal('test-us-east-1')
    grants['SnapshotCopyGrant']['KmsKeyId'].should.equal('fake')

    client.delete_snapshot_copy_grant(
        SnapshotCopyGrantName='test-us-east-1',
    )

    client.describe_snapshot_copy_grants.when.called_with(
        SnapshotCopyGrantName='test-us-east-1',
    ).should.throw(Exception)


@mock_redshift
def test_create_many_snapshot_copy_grants():
    client = boto3.client('redshift', region_name='us-east-1')

    for i in range(10):
        client.create_snapshot_copy_grant(
            SnapshotCopyGrantName='test-us-east-1-{0}'.format(i),
            KmsKeyId='fake',
        )
    response = client.describe_snapshot_copy_grants()
    len(response['SnapshotCopyGrants']).should.equal(10)


@mock_redshift
def test_no_snapshot_copy_grants():
    client = boto3.client('redshift', region_name='us-east-1')
    response = client.describe_snapshot_copy_grants()
    len(response['SnapshotCopyGrants']).should.equal(0)


@mock_redshift_deprecated
def test_create_cluster():
    conn = boto.redshift.connect_to_region("us-east-1")
    cluster_identifier = 'my_cluster'

    cluster_response = conn.create_cluster(
        cluster_identifier,
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
        db_name="my_db",
        cluster_type="multi-node",
        availability_zone="us-east-1d",
        preferred_maintenance_window="Mon:03:00-Mon:11:00",
        automated_snapshot_retention_period=10,
        port=1234,
        cluster_version="1.0",
        allow_version_upgrade=True,
        number_of_nodes=3,
    )
    cluster_response['CreateClusterResponse']['CreateClusterResult'][
        'Cluster']['ClusterStatus'].should.equal('creating')

    cluster_response = conn.describe_clusters(cluster_identifier)
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]

    cluster['ClusterIdentifier'].should.equal(cluster_identifier)
    cluster['NodeType'].should.equal("dw.hs1.xlarge")
    cluster['MasterUsername'].should.equal("username")
    cluster['DBName'].should.equal("my_db")
    cluster['ClusterSecurityGroups'][0][
        'ClusterSecurityGroupName'].should.equal("Default")
    cluster['VpcSecurityGroups'].should.equal([])
    cluster['ClusterSubnetGroupName'].should.equal(None)
    cluster['AvailabilityZone'].should.equal("us-east-1d")
    cluster['PreferredMaintenanceWindow'].should.equal("Mon:03:00-Mon:11:00")
    cluster['ClusterParameterGroups'][0][
        'ParameterGroupName'].should.equal("default.redshift-1.0")
    cluster['AutomatedSnapshotRetentionPeriod'].should.equal(10)
    cluster['Port'].should.equal(1234)
    cluster['ClusterVersion'].should.equal("1.0")
    cluster['AllowVersionUpgrade'].should.equal(True)
    cluster['NumberOfNodes'].should.equal(3)


@mock_redshift_deprecated
def test_create_single_node_cluster():
    conn = boto.redshift.connect_to_region("us-east-1")
    cluster_identifier = 'my_cluster'

    conn.create_cluster(
        cluster_identifier,
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
        db_name="my_db",
        cluster_type="single-node",
    )

    cluster_response = conn.describe_clusters(cluster_identifier)
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]

    cluster['ClusterIdentifier'].should.equal(cluster_identifier)
    cluster['NodeType'].should.equal("dw.hs1.xlarge")
    cluster['MasterUsername'].should.equal("username")
    cluster['DBName'].should.equal("my_db")
    cluster['NumberOfNodes'].should.equal(1)


@mock_redshift_deprecated
def test_default_cluster_attributes():
    conn = boto.redshift.connect_to_region("us-east-1")
    cluster_identifier = 'my_cluster'

    conn.create_cluster(
        cluster_identifier,
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
    )

    cluster_response = conn.describe_clusters(cluster_identifier)
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]

    cluster['DBName'].should.equal("dev")
    cluster['ClusterSubnetGroupName'].should.equal(None)
    assert "us-east-" in cluster['AvailabilityZone']
    cluster['PreferredMaintenanceWindow'].should.equal("Mon:03:00-Mon:03:30")
    cluster['ClusterParameterGroups'][0][
        'ParameterGroupName'].should.equal("default.redshift-1.0")
    cluster['AutomatedSnapshotRetentionPeriod'].should.equal(1)
    cluster['Port'].should.equal(5439)
    cluster['ClusterVersion'].should.equal("1.0")
    cluster['AllowVersionUpgrade'].should.equal(True)
    cluster['NumberOfNodes'].should.equal(1)


@mock_redshift
@mock_ec2
def test_create_cluster_in_subnet_group():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster_subnet_group(
        ClusterSubnetGroupName="my_subnet_group",
        Description="This is my subnet group",
        SubnetIds=[subnet.id],
    )

    client.create_cluster(
        ClusterIdentifier="my_cluster",
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        ClusterSubnetGroupName='my_subnet_group',
    )

    cluster_response = client.describe_clusters(ClusterIdentifier="my_cluster")
    cluster = cluster_response['Clusters'][0]
    cluster['ClusterSubnetGroupName'].should.equal('my_subnet_group')


@mock_redshift
@mock_ec2
def test_create_cluster_in_subnet_group_boto3():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock='10.0.0.0/24')
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster_subnet_group(
        ClusterSubnetGroupName='my_subnet_group',
        Description='This is my subnet group',
        SubnetIds=[subnet.id]
    )

    client.create_cluster(
        ClusterIdentifier="my_cluster",
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        ClusterSubnetGroupName='my_subnet_group',
    )

    cluster_response = client.describe_clusters(ClusterIdentifier="my_cluster")
    cluster = cluster_response['Clusters'][0]
    cluster['ClusterSubnetGroupName'].should.equal('my_subnet_group')


@mock_redshift_deprecated
def test_create_cluster_with_security_group():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.create_cluster_security_group(
        "security_group1",
        "This is my security group",
    )
    conn.create_cluster_security_group(
        "security_group2",
        "This is my security group",
    )

    cluster_identifier = 'my_cluster'
    conn.create_cluster(
        cluster_identifier,
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
        cluster_security_groups=["security_group1", "security_group2"]
    )

    cluster_response = conn.describe_clusters(cluster_identifier)
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]
    group_names = [group['ClusterSecurityGroupName']
                   for group in cluster['ClusterSecurityGroups']]
    set(group_names).should.equal(set(["security_group1", "security_group2"]))


@mock_redshift
def test_create_cluster_with_security_group_boto3():
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group1",
        Description="This is my security group",
    )
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group2",
        Description="This is my security group",
    )

    cluster_identifier = 'my_cluster'
    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        ClusterSecurityGroups=["security_group1", "security_group2"]
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = response['Clusters'][0]
    group_names = [group['ClusterSecurityGroupName']
                   for group in cluster['ClusterSecurityGroups']]
    set(group_names).should.equal({"security_group1", "security_group2"})


@mock_redshift_deprecated
@mock_ec2_deprecated
def test_create_cluster_with_vpc_security_groups():
    vpc_conn = boto.connect_vpc()
    ec2_conn = boto.connect_ec2()
    redshift_conn = boto.connect_redshift()
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    security_group = ec2_conn.create_security_group(
        "vpc_security_group", "a group", vpc_id=vpc.id)

    redshift_conn.create_cluster(
        "my_cluster",
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
        vpc_security_group_ids=[security_group.id],
    )

    cluster_response = redshift_conn.describe_clusters("my_cluster")
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]
    group_ids = [group['VpcSecurityGroupId']
                 for group in cluster['VpcSecurityGroups']]
    list(group_ids).should.equal([security_group.id])


@mock_redshift
@mock_ec2
def test_create_cluster_with_vpc_security_groups_boto3():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_id = 'my_cluster'
    security_group = ec2.create_security_group(
        Description="vpc_security_group",
        GroupName="a group",
        VpcId=vpc.id)
    client.create_cluster(
        ClusterIdentifier=cluster_id,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        VpcSecurityGroupIds=[security_group.id],
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_id)
    cluster = response['Clusters'][0]
    group_ids = [group['VpcSecurityGroupId']
                 for group in cluster['VpcSecurityGroups']]
    list(group_ids).should.equal([security_group.id])


@mock_redshift
def test_create_cluster_with_iam_roles():
    iam_roles_arn = ['arn:aws:iam:::role/my-iam-role', ]
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_id = 'my_cluster'
    client.create_cluster(
        ClusterIdentifier=cluster_id,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        IamRoles=iam_roles_arn
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_id)
    cluster = response['Clusters'][0]
    iam_roles = [role['IamRoleArn'] for role in cluster['IamRoles']]
    iam_roles_arn.should.equal(iam_roles)


@mock_redshift_deprecated
def test_create_cluster_with_parameter_group():
    conn = boto.connect_redshift()
    conn.create_cluster_parameter_group(
        "my_parameter_group",
        "redshift-1.0",
        "This is my parameter group",
    )

    conn.create_cluster(
        "my_cluster",
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
        cluster_parameter_group_name='my_parameter_group',
    )

    cluster_response = conn.describe_clusters("my_cluster")
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]
    cluster['ClusterParameterGroups'][0][
        'ParameterGroupName'].should.equal("my_parameter_group")


@mock_redshift_deprecated
def test_describe_non_existent_cluster():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_clusters.when.called_with(
        "not-a-cluster").should.throw(ClusterNotFound)

@mock_redshift_deprecated
def test_delete_cluster():
    conn = boto.connect_redshift()
    cluster_identifier = "my_cluster"
    snapshot_identifier = "my_snapshot"

    conn.create_cluster(
        cluster_identifier,
        node_type="single-node",
        master_username="username",
        master_user_password="password",
    )

    conn.delete_cluster.when.called_with(cluster_identifier, False).should.throw(AttributeError)

    clusters = conn.describe_clusters()['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters']
    list(clusters).should.have.length_of(1)

    conn.delete_cluster(
        cluster_identifier=cluster_identifier,
        skip_final_cluster_snapshot=False,
        final_cluster_snapshot_identifier=snapshot_identifier
      )

    clusters = conn.describe_clusters()['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters']
    list(clusters).should.have.length_of(0)

    snapshots = conn.describe_cluster_snapshots()["DescribeClusterSnapshotsResponse"][
        "DescribeClusterSnapshotsResult"]["Snapshots"]
    list(snapshots).should.have.length_of(1)

    assert snapshot_identifier in snapshots[0]["SnapshotIdentifier"]

    # Delete invalid id
    conn.delete_cluster.when.called_with(
        "not-a-cluster").should.throw(ClusterNotFound)


@mock_redshift_deprecated
def test_modify_cluster():
    conn = boto.connect_redshift()
    cluster_identifier = 'my_cluster'
    conn.create_cluster_security_group(
        "security_group",
        "This is my security group",
    )
    conn.create_cluster_parameter_group(
        "my_parameter_group",
        "redshift-1.0",
        "This is my parameter group",
    )

    conn.create_cluster(
        cluster_identifier,
        node_type='single-node',
        master_username="username",
        master_user_password="password",
    )

    conn.modify_cluster(
        cluster_identifier,
        cluster_type="multi-node",
        node_type="dw.hs1.xlarge",
        cluster_security_groups="security_group",
        master_user_password="new_password",
        cluster_parameter_group_name="my_parameter_group",
        automated_snapshot_retention_period=7,
        preferred_maintenance_window="Tue:03:00-Tue:11:00",
        allow_version_upgrade=False,
        new_cluster_identifier="new_identifier",
    )

    cluster_response = conn.describe_clusters("new_identifier")
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]

    cluster['ClusterIdentifier'].should.equal("new_identifier")
    cluster['NodeType'].should.equal("dw.hs1.xlarge")
    cluster['ClusterSecurityGroups'][0][
        'ClusterSecurityGroupName'].should.equal("security_group")
    cluster['PreferredMaintenanceWindow'].should.equal("Tue:03:00-Tue:11:00")
    cluster['ClusterParameterGroups'][0][
        'ParameterGroupName'].should.equal("my_parameter_group")
    cluster['AutomatedSnapshotRetentionPeriod'].should.equal(7)
    cluster['AllowVersionUpgrade'].should.equal(False)
    # This one should remain unmodified.
    cluster['NumberOfNodes'].should.equal(1)


@mock_redshift
@mock_ec2
def test_create_cluster_subnet_group():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    client = boto3.client('redshift', region_name='us-east-1')

    client.create_cluster_subnet_group(
        ClusterSubnetGroupName='my_subnet_group',
        Description='This is my subnet group',
        SubnetIds=[subnet1.id, subnet2.id],
    )

    subnets_response = client.describe_cluster_subnet_groups(
        ClusterSubnetGroupName="my_subnet_group")
    my_subnet = subnets_response['ClusterSubnetGroups'][0]

    my_subnet['ClusterSubnetGroupName'].should.equal("my_subnet_group")
    my_subnet['Description'].should.equal("This is my subnet group")
    subnet_ids = [subnet['SubnetIdentifier']
                  for subnet in my_subnet['Subnets']]
    set(subnet_ids).should.equal(set([subnet1.id, subnet2.id]))


@mock_redshift_deprecated
@mock_ec2_deprecated
def test_create_invalid_cluster_subnet_group():
    redshift_conn = boto.connect_redshift()
    redshift_conn.create_cluster_subnet_group.when.called_with(
        "my_subnet",
        "This is my subnet group",
        subnet_ids=["subnet-1234"],
    ).should.throw(InvalidSubnet)


@mock_redshift_deprecated
def test_describe_non_existent_subnet_group():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_cluster_subnet_groups.when.called_with(
        "not-a-subnet-group").should.throw(ClusterSubnetGroupNotFound)


@mock_redshift
@mock_ec2
def test_delete_cluster_subnet_group():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client('redshift', region_name='us-east-1')

    client.create_cluster_subnet_group(
        ClusterSubnetGroupName='my_subnet_group',
        Description='This is my subnet group',
        SubnetIds=[subnet.id],
    )

    subnets_response = client.describe_cluster_subnet_groups()
    subnets = subnets_response['ClusterSubnetGroups']
    subnets.should.have.length_of(1)

    client.delete_cluster_subnet_group(ClusterSubnetGroupName="my_subnet_group")

    subnets_response = client.describe_cluster_subnet_groups()
    subnets = subnets_response['ClusterSubnetGroups']
    subnets.should.have.length_of(0)

    # Delete invalid id
    client.delete_cluster_subnet_group.when.called_with(
        ClusterSubnetGroupName="not-a-subnet-group").should.throw(ClientError)


@mock_redshift_deprecated
def test_create_cluster_security_group():
    conn = boto.connect_redshift()
    conn.create_cluster_security_group(
        "my_security_group",
        "This is my security group",
    )

    groups_response = conn.describe_cluster_security_groups(
        "my_security_group")
    my_group = groups_response['DescribeClusterSecurityGroupsResponse'][
        'DescribeClusterSecurityGroupsResult']['ClusterSecurityGroups'][0]

    my_group['ClusterSecurityGroupName'].should.equal("my_security_group")
    my_group['Description'].should.equal("This is my security group")
    list(my_group['IPRanges']).should.equal([])


@mock_redshift_deprecated
def test_describe_non_existent_security_group():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_cluster_security_groups.when.called_with(
        "not-a-security-group").should.throw(ClusterSecurityGroupNotFound)


@mock_redshift_deprecated
def test_delete_cluster_security_group():
    conn = boto.connect_redshift()
    conn.create_cluster_security_group(
        "my_security_group",
        "This is my security group",
    )

    groups_response = conn.describe_cluster_security_groups()
    groups = groups_response['DescribeClusterSecurityGroupsResponse'][
        'DescribeClusterSecurityGroupsResult']['ClusterSecurityGroups']
    groups.should.have.length_of(2)  # The default group already exists

    conn.delete_cluster_security_group("my_security_group")

    groups_response = conn.describe_cluster_security_groups()
    groups = groups_response['DescribeClusterSecurityGroupsResponse'][
        'DescribeClusterSecurityGroupsResult']['ClusterSecurityGroups']
    groups.should.have.length_of(1)

    # Delete invalid id
    conn.delete_cluster_security_group.when.called_with(
        "not-a-security-group").should.throw(ClusterSecurityGroupNotFound)


@mock_redshift_deprecated
def test_create_cluster_parameter_group():
    conn = boto.connect_redshift()
    conn.create_cluster_parameter_group(
        "my_parameter_group",
        "redshift-1.0",
        "This is my parameter group",
    )

    groups_response = conn.describe_cluster_parameter_groups(
        "my_parameter_group")
    my_group = groups_response['DescribeClusterParameterGroupsResponse'][
        'DescribeClusterParameterGroupsResult']['ParameterGroups'][0]

    my_group['ParameterGroupName'].should.equal("my_parameter_group")
    my_group['ParameterGroupFamily'].should.equal("redshift-1.0")
    my_group['Description'].should.equal("This is my parameter group")


@mock_redshift_deprecated
def test_describe_non_existent_parameter_group():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_cluster_parameter_groups.when.called_with(
        "not-a-parameter-group").should.throw(ClusterParameterGroupNotFound)


@mock_redshift_deprecated
def test_delete_cluster_parameter_group():
    conn = boto.connect_redshift()
    conn.create_cluster_parameter_group(
        "my_parameter_group",
        "redshift-1.0",
        "This is my parameter group",
    )

    groups_response = conn.describe_cluster_parameter_groups()
    groups = groups_response['DescribeClusterParameterGroupsResponse'][
        'DescribeClusterParameterGroupsResult']['ParameterGroups']
    groups.should.have.length_of(2)  # The default group already exists

    conn.delete_cluster_parameter_group("my_parameter_group")

    groups_response = conn.describe_cluster_parameter_groups()
    groups = groups_response['DescribeClusterParameterGroupsResponse'][
        'DescribeClusterParameterGroupsResult']['ParameterGroups']
    groups.should.have.length_of(1)

    # Delete invalid id
    conn.delete_cluster_parameter_group.when.called_with(
        "not-a-parameter-group").should.throw(ClusterParameterGroupNotFound)


@mock_redshift
def test_create_cluster_snapshot_of_non_existent_cluster():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'non-existent-cluster-id'
    client.create_cluster_snapshot.when.called_with(
        SnapshotIdentifier='snapshot-id',
        ClusterIdentifier=cluster_identifier,
    ).should.throw(ClientError, 'Cluster {} not found.'.format(cluster_identifier))


@mock_redshift
def test_create_cluster_snapshot():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    snapshot_identifier = 'my_snapshot'

    cluster_response = client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )
    cluster_response['Cluster']['NodeType'].should.equal('ds2.xlarge')

    snapshot_response = client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{'Key': 'test-tag-key',
               'Value': 'test-tag-value'}]
    )
    snapshot = snapshot_response['Snapshot']
    snapshot['SnapshotIdentifier'].should.equal(snapshot_identifier)
    snapshot['ClusterIdentifier'].should.equal(cluster_identifier)
    snapshot['NumberOfNodes'].should.equal(1)
    snapshot['NodeType'].should.equal('ds2.xlarge')
    snapshot['MasterUsername'].should.equal('username')


@mock_redshift
def test_describe_cluster_snapshots():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    snapshot_identifier_1 = 'my_snapshot_1'
    snapshot_identifier_2 = 'my_snapshot_2'

    client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier_1,
        ClusterIdentifier=cluster_identifier,
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier_2,
        ClusterIdentifier=cluster_identifier,
    )

    resp_snap_1 = client.describe_cluster_snapshots(SnapshotIdentifier=snapshot_identifier_1)
    snapshot_1 = resp_snap_1['Snapshots'][0]
    snapshot_1['SnapshotIdentifier'].should.equal(snapshot_identifier_1)
    snapshot_1['ClusterIdentifier'].should.equal(cluster_identifier)
    snapshot_1['NumberOfNodes'].should.equal(1)
    snapshot_1['NodeType'].should.equal('ds2.xlarge')
    snapshot_1['MasterUsername'].should.equal('username')

    resp_snap_2 = client.describe_cluster_snapshots(SnapshotIdentifier=snapshot_identifier_2)
    snapshot_2 = resp_snap_2['Snapshots'][0]
    snapshot_2['SnapshotIdentifier'].should.equal(snapshot_identifier_2)
    snapshot_2['ClusterIdentifier'].should.equal(cluster_identifier)
    snapshot_2['NumberOfNodes'].should.equal(1)
    snapshot_2['NodeType'].should.equal('ds2.xlarge')
    snapshot_2['MasterUsername'].should.equal('username')

    resp_clust = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    resp_clust['Snapshots'][0].should.equal(resp_snap_1['Snapshots'][0])
    resp_clust['Snapshots'][1].should.equal(resp_snap_2['Snapshots'][0])


@mock_redshift
def test_describe_cluster_snapshots_not_found_error():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    snapshot_identifier = 'my_snapshot'

    client.describe_cluster_snapshots.when.called_with(
        ClusterIdentifier=cluster_identifier,
    ).should.throw(ClientError, 'Cluster {} not found.'.format(cluster_identifier))

    client.describe_cluster_snapshots.when.called_with(
        SnapshotIdentifier=snapshot_identifier
    ).should.throw(ClientError, 'Snapshot {} not found.'.format(snapshot_identifier))


@mock_redshift
def test_delete_cluster_snapshot():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    snapshot_identifier = 'my_snapshot'

    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier
    )

    snapshots = client.describe_cluster_snapshots()['Snapshots']
    list(snapshots).should.have.length_of(1)

    client.delete_cluster_snapshot(SnapshotIdentifier=snapshot_identifier)[
        'Snapshot']['Status'].should.equal('deleted')

    snapshots = client.describe_cluster_snapshots()['Snapshots']
    list(snapshots).should.have.length_of(0)

    # Delete invalid id
    client.delete_cluster_snapshot.when.called_with(
        SnapshotIdentifier="not-a-snapshot").should.throw(ClientError)


@mock_redshift
def test_cluster_snapshot_already_exists():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    snapshot_identifier = 'my_snapshot'

    client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier
    )

    client.create_cluster_snapshot.when.called_with(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier
    ).should.throw(ClientError)


@mock_redshift
def test_create_cluster_from_snapshot():
    client = boto3.client('redshift', region_name='us-east-1')
    original_cluster_identifier = 'original-cluster'
    original_snapshot_identifier = 'original-snapshot'
    new_cluster_identifier = 'new-cluster'

    client.create_cluster(
        ClusterIdentifier=original_cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=original_snapshot_identifier,
        ClusterIdentifier=original_cluster_identifier
    )
    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        Port=1234
    )
    response['Cluster']['ClusterStatus'].should.equal('creating')

    response = client.describe_clusters(
        ClusterIdentifier=new_cluster_identifier
    )
    new_cluster = response['Clusters'][0]
    new_cluster['NodeType'].should.equal('ds2.xlarge')
    new_cluster['MasterUsername'].should.equal('username')
    new_cluster['Endpoint']['Port'].should.equal(1234)


@mock_redshift
def test_create_cluster_from_snapshot_with_waiter():
    client = boto3.client('redshift', region_name='us-east-1')
    original_cluster_identifier = 'original-cluster'
    original_snapshot_identifier = 'original-snapshot'
    new_cluster_identifier = 'new-cluster'

    client.create_cluster(
        ClusterIdentifier=original_cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=original_snapshot_identifier,
        ClusterIdentifier=original_cluster_identifier
    )
    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        Port=1234
    )
    response['Cluster']['ClusterStatus'].should.equal('creating')

    client.get_waiter('cluster_restored').wait(
        ClusterIdentifier=new_cluster_identifier,
        WaiterConfig={
            'Delay': 1,
            'MaxAttempts': 2,
        }
    )

    response = client.describe_clusters(
        ClusterIdentifier=new_cluster_identifier
    )
    new_cluster = response['Clusters'][0]
    new_cluster['NodeType'].should.equal('ds2.xlarge')
    new_cluster['MasterUsername'].should.equal('username')
    new_cluster['Endpoint']['Port'].should.equal(1234)


@mock_redshift
def test_create_cluster_from_non_existent_snapshot():
    client = boto3.client('redshift', region_name='us-east-1')
    client.restore_from_cluster_snapshot.when.called_with(
        ClusterIdentifier='cluster-id',
        SnapshotIdentifier='non-existent-snapshot',
    ).should.throw(ClientError, 'Snapshot non-existent-snapshot not found.')


@mock_redshift
def test_create_cluster_status_update():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'test-cluster'

    response = client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )
    response['Cluster']['ClusterStatus'].should.equal('creating')

    response = client.describe_clusters(
        ClusterIdentifier=cluster_identifier
    )
    response['Clusters'][0]['ClusterStatus'].should.equal('available')


@mock_redshift
def test_describe_tags_with_resource_type():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    cluster_arn = 'arn:aws:redshift:us-east-1:123456789012:' \
                  'cluster:{}'.format(cluster_identifier)
    snapshot_identifier = 'my_snapshot'
    snapshot_arn = 'arn:aws:redshift:us-east-1:123456789012:' \
                   'snapshot:{}/{}'.format(cluster_identifier,
                                           snapshot_identifier)
    tag_key = 'test-tag-key'
    tag_value = 'test-tag-value'

    client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
        Tags=[{'Key': tag_key,
               'Value': tag_value}]
    )
    tags_response = client.describe_tags(ResourceType='cluster')
    tagged_resources = tags_response['TaggedResources']
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]['ResourceType'].should.equal('cluster')
    tagged_resources[0]['ResourceName'].should.equal(cluster_arn)
    tag = tagged_resources[0]['Tag']
    tag['Key'].should.equal(tag_key)
    tag['Value'].should.equal(tag_value)

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{'Key': tag_key,
               'Value': tag_value}]
    )
    tags_response = client.describe_tags(ResourceType='snapshot')
    tagged_resources = tags_response['TaggedResources']
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]['ResourceType'].should.equal('snapshot')
    tagged_resources[0]['ResourceName'].should.equal(snapshot_arn)
    tag = tagged_resources[0]['Tag']
    tag['Key'].should.equal(tag_key)
    tag['Value'].should.equal(tag_value)


@mock_redshift
def test_describe_tags_cannot_specify_resource_type_and_resource_name():
    client = boto3.client('redshift', region_name='us-east-1')
    resource_name = 'arn:aws:redshift:us-east-1:123456789012:cluster:cluster-id'
    resource_type = 'cluster'
    client.describe_tags.when.called_with(
        ResourceName=resource_name,
        ResourceType=resource_type
    ).should.throw(ClientError, 'using either an ARN or a resource type')


@mock_redshift
def test_describe_tags_with_resource_name():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'cluster-id'
    cluster_arn = 'arn:aws:redshift:us-east-1:123456789012:' \
                  'cluster:{}'.format(cluster_identifier)
    snapshot_identifier = 'snapshot-id'
    snapshot_arn = 'arn:aws:redshift:us-east-1:123456789012:' \
                   'snapshot:{}/{}'.format(cluster_identifier,
                                           snapshot_identifier)
    tag_key = 'test-tag-key'
    tag_value = 'test-tag-value'

    client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
        Tags=[{'Key': tag_key,
               'Value': tag_value}]
    )
    tags_response = client.describe_tags(ResourceName=cluster_arn)
    tagged_resources = tags_response['TaggedResources']
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]['ResourceType'].should.equal('cluster')
    tagged_resources[0]['ResourceName'].should.equal(cluster_arn)
    tag = tagged_resources[0]['Tag']
    tag['Key'].should.equal(tag_key)
    tag['Value'].should.equal(tag_value)

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{'Key': tag_key,
               'Value': tag_value}]
    )
    tags_response = client.describe_tags(ResourceName=snapshot_arn)
    tagged_resources = tags_response['TaggedResources']
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]['ResourceType'].should.equal('snapshot')
    tagged_resources[0]['ResourceName'].should.equal(snapshot_arn)
    tag = tagged_resources[0]['Tag']
    tag['Key'].should.equal(tag_key)
    tag['Value'].should.equal(tag_value)


@mock_redshift
def test_create_tags():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'cluster-id'
    cluster_arn = 'arn:aws:redshift:us-east-1:123456789012:' \
                  'cluster:{}'.format(cluster_identifier)
    tag_key = 'test-tag-key'
    tag_value = 'test-tag-value'
    num_tags = 5
    tags = []
    for i in range(0, num_tags):
        tag = {'Key': '{}-{}'.format(tag_key, i),
               'Value': '{}-{}'.format(tag_value, i)}
        tags.append(tag)

    client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
    )
    client.create_tags(
        ResourceName=cluster_arn,
        Tags=tags
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = response['Clusters'][0]
    list(cluster['Tags']).should.have.length_of(num_tags)
    response = client.describe_tags(ResourceName=cluster_arn)
    list(response['TaggedResources']).should.have.length_of(num_tags)


@mock_redshift
def test_delete_tags():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'cluster-id'
    cluster_arn = 'arn:aws:redshift:us-east-1:123456789012:' \
                  'cluster:{}'.format(cluster_identifier)
    tag_key = 'test-tag-key'
    tag_value = 'test-tag-value'
    tags = []
    for i in range(1, 2):
        tag = {'Key': '{}-{}'.format(tag_key, i),
               'Value': '{}-{}'.format(tag_value, i)}
        tags.append(tag)

    client.create_cluster(
        DBName='test-db',
        ClusterIdentifier=cluster_identifier,
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='username',
        MasterUserPassword='password',
        Tags=tags
    )
    client.delete_tags(
        ResourceName=cluster_arn,
        TagKeys=[tag['Key'] for tag in tags
                 if tag['Key'] != '{}-1'.format(tag_key)]
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = response['Clusters'][0]
    list(cluster['Tags']).should.have.length_of(1)
    response = client.describe_tags(ResourceName=cluster_arn)
    list(response['TaggedResources']).should.have.length_of(1)


@mock_ec2
@mock_redshift
def test_describe_tags_all_resource_types():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock='10.0.0.0/24')
    client = boto3.client('redshift', region_name='us-east-1')
    response = client.describe_tags()
    list(response['TaggedResources']).should.have.length_of(0)
    client.create_cluster_subnet_group(
        ClusterSubnetGroupName='my_subnet_group',
        Description='This is my subnet group',
        SubnetIds=[subnet.id],
        Tags=[{'Key': 'tag_key',
               'Value': 'tag_value'}]
    )
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group1",
        Description="This is my security group",
        Tags=[{'Key': 'tag_key',
               'Value': 'tag_value'}]
    )
    client.create_cluster(
        DBName='test',
        ClusterIdentifier='my_cluster',
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='user',
        MasterUserPassword='password',
        Tags=[{'Key': 'tag_key',
               'Value': 'tag_value'}]
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier='my_snapshot',
        ClusterIdentifier='my_cluster',
        Tags=[{'Key': 'tag_key',
               'Value': 'tag_value'}]
    )
    client.create_cluster_parameter_group(
        ParameterGroupName="my_parameter_group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my parameter group",
        Tags=[{'Key': 'tag_key',
               'Value': 'tag_value'}]
    )
    response = client.describe_tags()
    expected_types = ['cluster', 'parametergroup', 'securitygroup', 'snapshot', 'subnetgroup']
    tagged_resources = response['TaggedResources']
    returned_types = [resource['ResourceType'] for resource in tagged_resources]
    list(tagged_resources).should.have.length_of(len(expected_types))
    set(returned_types).should.equal(set(expected_types))


@mock_redshift
def test_tagged_resource_not_found_error():
    client = boto3.client('redshift', region_name='us-east-1')

    cluster_arn = 'arn:aws:redshift:us-east-1::cluster:fake'
    client.describe_tags.when.called_with(
        ResourceName=cluster_arn
    ).should.throw(ClientError, 'cluster (fake) not found.')

    snapshot_arn = 'arn:aws:redshift:us-east-1::snapshot:cluster-id/snap-id'
    client.delete_tags.when.called_with(
        ResourceName=snapshot_arn,
        TagKeys=['test']
    ).should.throw(ClientError, 'snapshot (snap-id) not found.')

    client.describe_tags.when.called_with(
        ResourceType='cluster'
    ).should.throw(ClientError, "resource of type 'cluster' not found.")

    client.describe_tags.when.called_with(
        ResourceName='bad:arn'
    ).should.throw(ClientError, "Tagging is not supported for this type of resource")


@mock_redshift
def test_enable_snapshot_copy():
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster(
        ClusterIdentifier='test',
        ClusterType='single-node',
        DBName='test',
        Encrypted=True,
        MasterUsername='user',
        MasterUserPassword='password',
        NodeType='ds2.xlarge',
    )
    client.enable_snapshot_copy(
        ClusterIdentifier='test',
        DestinationRegion='us-west-2',
        RetentionPeriod=3,
        SnapshotCopyGrantName='copy-us-east-1-to-us-west-2'
    )
    response = client.describe_clusters(ClusterIdentifier='test')
    cluster_snapshot_copy_status = response['Clusters'][0]['ClusterSnapshotCopyStatus']
    cluster_snapshot_copy_status['RetentionPeriod'].should.equal(3)
    cluster_snapshot_copy_status['DestinationRegion'].should.equal('us-west-2')
    cluster_snapshot_copy_status['SnapshotCopyGrantName'].should.equal('copy-us-east-1-to-us-west-2')


@mock_redshift
def test_enable_snapshot_copy_unencrypted():
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster(
        ClusterIdentifier='test',
        ClusterType='single-node',
        DBName='test',
        MasterUsername='user',
        MasterUserPassword='password',
        NodeType='ds2.xlarge',
    )
    client.enable_snapshot_copy(
        ClusterIdentifier='test',
        DestinationRegion='us-west-2',
    )
    response = client.describe_clusters(ClusterIdentifier='test')
    cluster_snapshot_copy_status = response['Clusters'][0]['ClusterSnapshotCopyStatus']
    cluster_snapshot_copy_status['RetentionPeriod'].should.equal(7)
    cluster_snapshot_copy_status['DestinationRegion'].should.equal('us-west-2')


@mock_redshift
def test_disable_snapshot_copy():
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster(
        DBName='test',
        ClusterIdentifier='test',
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='user',
        MasterUserPassword='password',
    )
    client.enable_snapshot_copy(
        ClusterIdentifier='test',
        DestinationRegion='us-west-2',
        RetentionPeriod=3,
        SnapshotCopyGrantName='copy-us-east-1-to-us-west-2',
    )
    client.disable_snapshot_copy(
        ClusterIdentifier='test',
    )
    response = client.describe_clusters(ClusterIdentifier='test')
    response['Clusters'][0].shouldnt.contain('ClusterSnapshotCopyStatus')


@mock_redshift
def test_modify_snapshot_copy_retention_period():
    client = boto3.client('redshift', region_name='us-east-1')
    client.create_cluster(
        DBName='test',
        ClusterIdentifier='test',
        ClusterType='single-node',
        NodeType='ds2.xlarge',
        MasterUsername='user',
        MasterUserPassword='password',
    )
    client.enable_snapshot_copy(
        ClusterIdentifier='test',
        DestinationRegion='us-west-2',
        RetentionPeriod=3,
        SnapshotCopyGrantName='copy-us-east-1-to-us-west-2',
    )
    client.modify_snapshot_copy_retention_period(
        ClusterIdentifier='test',
        RetentionPeriod=5,
    )
    response = client.describe_clusters(ClusterIdentifier='test')
    cluster_snapshot_copy_status = response['Clusters'][0]['ClusterSnapshotCopyStatus']
    cluster_snapshot_copy_status['RetentionPeriod'].should.equal(5)
