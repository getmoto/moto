from __future__ import unicode_literals

import boto
from boto.redshift.exceptions import ClusterNotFound, ClusterSubnetGroupNotFound
import sure  # noqa

from moto import mock_ec2, mock_redshift


@mock_redshift
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
        # cluster_security_groups=None,
        # vpc_security_group_ids=None,
        availability_zone="us-east-1d",
        preferred_maintenance_window="Mon:03:00-Mon:11:00",
        # cluster_parameter_group_name=None,
        automated_snapshot_retention_period=10,
        port=1234,
        cluster_version="1.0",
        allow_version_upgrade=True,
        number_of_nodes=3,
    )

    cluster_response = conn.describe_clusters(cluster_identifier)
    cluster = cluster_response['DescribeClustersResponse']['DescribeClustersResult']['Clusters'][0]

    cluster['ClusterIdentifier'].should.equal(cluster_identifier)
    cluster['NodeType'].should.equal("dw.hs1.xlarge")
    cluster['MasterUsername'].should.equal("username")
    cluster['DBName'].should.equal("my_db")
    cluster['ClusterSecurityGroups'].should.equal([])
    cluster['VpcSecurityGroups'].should.equal([])
    cluster['ClusterSubnetGroupName'].should.equal(None)
    cluster['AvailabilityZone'].should.equal("us-east-1d")
    cluster['PreferredMaintenanceWindow'].should.equal("Mon:03:00-Mon:11:00")
    cluster['ClusterParameterGroups'].should.equal([])
    cluster['AutomatedSnapshotRetentionPeriod'].should.equal(10)
    cluster['Port'].should.equal(1234)
    cluster['ClusterVersion'].should.equal("1.0")
    cluster['AllowVersionUpgrade'].should.equal(True)
    cluster['NumberOfNodes'].should.equal(3)


@mock_redshift
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
    cluster = cluster_response['DescribeClustersResponse']['DescribeClustersResult']['Clusters'][0]

    cluster['ClusterIdentifier'].should.equal(cluster_identifier)
    cluster['NodeType'].should.equal("dw.hs1.xlarge")
    cluster['MasterUsername'].should.equal("username")
    cluster['DBName'].should.equal("my_db")
    cluster['NumberOfNodes'].should.equal(1)


@mock_redshift
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
    cluster = cluster_response['DescribeClustersResponse']['DescribeClustersResult']['Clusters'][0]

    cluster['DBName'].should.equal("dev")
    # cluster['ClusterSecurityGroups'].should.equal([])
    # cluster['VpcSecurityGroups'].should.equal([])
    cluster['ClusterSubnetGroupName'].should.equal(None)
    assert "us-east-" in cluster['AvailabilityZone']
    cluster['PreferredMaintenanceWindow'].should.equal("Mon:03:00-Mon:03:30")
    # cluster['ClusterParameterGroups'].should.equal([])
    cluster['AutomatedSnapshotRetentionPeriod'].should.equal(1)
    cluster['Port'].should.equal(5439)
    cluster['ClusterVersion'].should.equal("1.0")
    cluster['AllowVersionUpgrade'].should.equal(True)
    cluster['NumberOfNodes'].should.equal(1)


@mock_redshift
@mock_ec2
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
    cluster = cluster_response['DescribeClustersResponse']['DescribeClustersResult']['Clusters'][0]
    cluster['ClusterSubnetGroupName'].should.equal('my_subnet_group')


@mock_redshift
def test_describe_non_existant_cluster():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_clusters.when.called_with("not-a-cluster").should.throw(ClusterNotFound)


@mock_redshift
def test_delete_cluster():
    conn = boto.connect_redshift()
    cluster_identifier = 'my_cluster'

    conn.create_cluster(
        cluster_identifier,
        node_type='single-node',
        master_username="username",
        master_user_password="password",
    )

    clusters = conn.describe_clusters()['DescribeClustersResponse']['DescribeClustersResult']['Clusters']
    list(clusters).should.have.length_of(1)

    conn.delete_cluster(cluster_identifier)

    clusters = conn.describe_clusters()['DescribeClustersResponse']['DescribeClustersResult']['Clusters']
    list(clusters).should.have.length_of(0)

    # Delete invalid id
    conn.delete_cluster.when.called_with("not-a-cluster").should.throw(ClusterNotFound)


@mock_redshift
def test_modify_cluster():
    conn = boto.connect_redshift()
    cluster_identifier = 'my_cluster'

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
        # cluster_security_groups=None,
        # vpc_security_group_ids=None,
        master_user_password="new_password",
        # cluster_parameter_group_name=None,
        automated_snapshot_retention_period=7,
        preferred_maintenance_window="Tue:03:00-Tue:11:00",
        allow_version_upgrade=False,
        new_cluster_identifier="new_identifier",
    )

    cluster_response = conn.describe_clusters("new_identifier")
    cluster = cluster_response['DescribeClustersResponse']['DescribeClustersResult']['Clusters'][0]

    cluster['ClusterIdentifier'].should.equal("new_identifier")
    cluster['NodeType'].should.equal("dw.hs1.xlarge")
    # cluster['ClusterSecurityGroups'].should.equal([])
    # cluster['VpcSecurityGroups'].should.equal([])
    cluster['PreferredMaintenanceWindow'].should.equal("Tue:03:00-Tue:11:00")
    # cluster['ClusterParameterGroups'].should.equal([])
    cluster['AutomatedSnapshotRetentionPeriod'].should.equal(7)
    cluster['AllowVersionUpgrade'].should.equal(False)
    cluster['NumberOfNodes'].should.equal(2)


@mock_redshift
@mock_ec2
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

    list(redshift_conn.describe_cluster_subnet_groups()).should.have.length_of(1)

    subnets_response = redshift_conn.describe_cluster_subnet_groups("my_subnet")
    my_subnet = subnets_response['DescribeClusterSubnetGroupsResponse']['DescribeClusterSubnetGroupsResult']['ClusterSubnetGroups'][0]

    my_subnet['ClusterSubnetGroupName'].should.equal("my_subnet")
    my_subnet['Description'].should.equal("This is my subnet group")
    subnet_ids = [subnet['SubnetIdentifier'] for subnet in my_subnet['Subnets']]
    set(subnet_ids).should.equal(set([subnet1.id, subnet2.id]))


@mock_redshift
def test_describe_non_existant_subnet_group():
    conn = boto.redshift.connect_to_region("us-east-1")
    conn.describe_cluster_subnet_groups.when.called_with("not-a-subnet-group").should.throw(ClusterSubnetGroupNotFound)


@mock_redshift
@mock_ec2
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
    subnets = subnets_response['DescribeClusterSubnetGroupsResponse']['DescribeClusterSubnetGroupsResult']['ClusterSubnetGroups']
    subnets.should.have.length_of(1)

    redshift_conn.delete_cluster_subnet_group("my_subnet")

    subnets_response = redshift_conn.describe_cluster_subnet_groups()
    subnets = subnets_response['DescribeClusterSubnetGroupsResponse']['DescribeClusterSubnetGroupsResult']['ClusterSubnetGroups']
    subnets.should.have.length_of(0)

    # Delete invalid id
    redshift_conn.describe_cluster_subnet_groups.when.called_with("not-a-subnet-group").should.throw(ClusterSubnetGroupNotFound)
