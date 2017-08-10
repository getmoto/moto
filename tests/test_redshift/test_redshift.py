from __future__ import unicode_literals

import boto
import boto3
from boto.redshift.exceptions import (
    ClusterNotFound,
    ClusterParameterGroupNotFound,
    ClusterSecurityGroupNotFound,
    ClusterSubnetGroupNotFound,
    InvalidSubnet,
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
def test_default_cluster_attibutes():
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


@mock_redshift_deprecated
@mock_ec2_deprecated
def test_create_cluster_in_subnet_group():
    vpc_conn = boto.connect_vpc()
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.0.0.0/24")
    redshift_conn = boto.connect_redshift()
    redshift_conn.create_cluster_subnet_group(
        "my_subnet_group",
        "This is my subnet group",
        subnet_ids=[subnet.id],
    )

    redshift_conn.create_cluster(
        "my_cluster",
        node_type="dw.hs1.xlarge",
        master_username="username",
        master_user_password="password",
        cluster_subnet_group_name='my_subnet_group',
    )

    cluster_response = redshift_conn.describe_clusters("my_cluster")
    cluster = cluster_response['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters'][0]
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
def test_describe_non_existant_cluster():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_clusters.when.called_with(
        "not-a-cluster").should.throw(ClusterNotFound)


@mock_redshift_deprecated
def test_delete_cluster():
    conn = boto.connect_redshift()
    cluster_identifier = 'my_cluster'

    conn.create_cluster(
        cluster_identifier,
        node_type='single-node',
        master_username="username",
        master_user_password="password",
    )

    clusters = conn.describe_clusters()['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters']
    list(clusters).should.have.length_of(1)

    conn.delete_cluster(cluster_identifier)

    clusters = conn.describe_clusters()['DescribeClustersResponse'][
        'DescribeClustersResult']['Clusters']
    list(clusters).should.have.length_of(0)

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


@mock_redshift_deprecated
@mock_ec2_deprecated
def test_create_cluster_subnet_group():
    vpc_conn = boto.connect_vpc()
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet1 = vpc_conn.create_subnet(vpc.id, "10.0.0.0/24")
    subnet2 = vpc_conn.create_subnet(vpc.id, "10.0.1.0/24")

    redshift_conn = boto.connect_redshift()

    redshift_conn.create_cluster_subnet_group(
        "my_subnet",
        "This is my subnet group",
        subnet_ids=[subnet1.id, subnet2.id],
    )

    subnets_response = redshift_conn.describe_cluster_subnet_groups(
        "my_subnet")
    my_subnet = subnets_response['DescribeClusterSubnetGroupsResponse'][
        'DescribeClusterSubnetGroupsResult']['ClusterSubnetGroups'][0]

    my_subnet['ClusterSubnetGroupName'].should.equal("my_subnet")
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
def test_describe_non_existant_subnet_group():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_cluster_subnet_groups.when.called_with(
        "not-a-subnet-group").should.throw(ClusterSubnetGroupNotFound)


@mock_redshift_deprecated
@mock_ec2_deprecated
def test_delete_cluster_subnet_group():
    vpc_conn = boto.connect_vpc()
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.0.0.0/24")
    redshift_conn = boto.connect_redshift()

    redshift_conn.create_cluster_subnet_group(
        "my_subnet",
        "This is my subnet group",
        subnet_ids=[subnet.id],
    )

    subnets_response = redshift_conn.describe_cluster_subnet_groups()
    subnets = subnets_response['DescribeClusterSubnetGroupsResponse'][
        'DescribeClusterSubnetGroupsResult']['ClusterSubnetGroups']
    subnets.should.have.length_of(1)

    redshift_conn.delete_cluster_subnet_group("my_subnet")

    subnets_response = redshift_conn.describe_cluster_subnet_groups()
    subnets = subnets_response['DescribeClusterSubnetGroupsResponse'][
        'DescribeClusterSubnetGroupsResult']['ClusterSubnetGroups']
    subnets.should.have.length_of(0)

    # Delete invalid id
    redshift_conn.delete_cluster_subnet_group.when.called_with(
        "not-a-subnet-group").should.throw(ClusterSubnetGroupNotFound)


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
def test_describe_non_existant_security_group():
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
def test_describe_non_existant_parameter_group():
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
def test_describe_snapshot_tags():
    client = boto3.client('redshift', region_name='us-east-1')
    cluster_identifier = 'my_cluster'
    snapshot_identifier = 'my_snapshot'
    tag_key = 'test-tag-key'
    tag_value = 'teat-tag-value'

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
        ClusterIdentifier=cluster_identifier,
        Tags=[{'Key': tag_key,
               'Value': tag_value}]
    )

    tags_response = client.describe_tags(ResourceType='Snapshot')
    tagged_resources = tags_response['TaggedResources']
    list(tagged_resources).should.have.length_of(1)
    tag = tagged_resources[0]['Tag']
    tag['Key'].should.equal(tag_key)
    tag['Value'].should.equal(tag_value)
