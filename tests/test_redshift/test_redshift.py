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
import sure  # noqa

from moto import mock_ec2_deprecated, mock_redshift_deprecated, mock_redshift


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

    conn.create_cluster(
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
        number_of_nodes=2,
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
    cluster['NumberOfNodes'].should.equal(2)


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
