import time
import datetime

import boto3
from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2
from moto import mock_redshift
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_redshift
def test_create_cluster_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
    )
    cluster = response["Cluster"]
    cluster["ClusterIdentifier"].should.equal("test")
    cluster["NodeType"].should.equal("ds2.xlarge")
    cluster["ClusterStatus"].should.equal("creating")
    create_time = cluster["ClusterCreateTime"]
    create_time.should.be.lower_than(datetime.datetime.now(create_time.tzinfo))
    create_time.should.be.greater_than(
        datetime.datetime.now(create_time.tzinfo) - datetime.timedelta(minutes=1)
    )
    cluster["MasterUsername"].should.equal("user")
    cluster["DBName"].should.equal("test")
    cluster["AutomatedSnapshotRetentionPeriod"].should.equal(1)
    cluster["ClusterSecurityGroups"].should.equal(
        [{"ClusterSecurityGroupName": "Default", "Status": "active"}]
    )
    cluster["VpcSecurityGroups"].should.equal([])
    cluster["ClusterParameterGroups"].should.equal(
        [
            {
                "ParameterGroupName": "default.redshift-1.0",
                "ParameterApplyStatus": "in-sync",
            }
        ]
    )
    cluster["ClusterSubnetGroupName"].should.equal("")
    cluster["AvailabilityZone"].should.equal("us-east-1a")
    cluster["PreferredMaintenanceWindow"].should.equal("Mon:03:00-Mon:03:30")
    cluster["ClusterVersion"].should.equal("1.0")
    cluster["AllowVersionUpgrade"].should.equal(True)
    cluster["NumberOfNodes"].should.equal(1)
    cluster["EnhancedVpcRouting"].should.equal(False)
    cluster["KmsKeyId"].should.equal("")
    cluster["Endpoint"]["Port"].should.equal(5439)


@mock_redshift
def test_create_cluster_with_enhanced_vpc_routing_enabled():
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )
    response["Cluster"]["NodeType"].should.equal("ds2.xlarge")
    create_time = response["Cluster"]["ClusterCreateTime"]
    create_time.should.be.lower_than(datetime.datetime.now(create_time.tzinfo))
    create_time.should.be.greater_than(
        datetime.datetime.now(create_time.tzinfo) - datetime.timedelta(minutes=1)
    )
    response["Cluster"]["EnhancedVpcRouting"].should.equal(True)


@mock_redshift
def test_create_and_describe_cluster_with_kms_key_id():
    kms_key_id = (
        "arn:aws:kms:us-east-1:123456789012:key/00000000-0000-0000-0000-000000000000"
    )
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
        KmsKeyId=kms_key_id,
    )
    response["Cluster"]["KmsKeyId"].should.equal(kms_key_id)

    response = client.describe_clusters()
    clusters = response.get("Clusters", [])
    len(clusters).should.equal(1)

    cluster = clusters[0]
    cluster["KmsKeyId"].should.equal(kms_key_id)


@mock_redshift
def test_create_snapshot_copy_grant():
    client = boto3.client("redshift", region_name="us-east-1")
    grants = client.create_snapshot_copy_grant(
        SnapshotCopyGrantName="test-us-east-1", KmsKeyId="fake"
    )
    grants["SnapshotCopyGrant"]["SnapshotCopyGrantName"].should.equal("test-us-east-1")
    grants["SnapshotCopyGrant"]["KmsKeyId"].should.equal("fake")

    client.delete_snapshot_copy_grant(SnapshotCopyGrantName="test-us-east-1")

    client.describe_snapshot_copy_grants.when.called_with(
        SnapshotCopyGrantName="test-us-east-1"
    ).should.throw(ClientError)


@mock_redshift
def test_create_many_snapshot_copy_grants():
    client = boto3.client("redshift", region_name="us-east-1")

    for i in range(10):
        client.create_snapshot_copy_grant(
            SnapshotCopyGrantName=f"test-us-east-1-{i}", KmsKeyId="fake"
        )
    response = client.describe_snapshot_copy_grants()
    len(response["SnapshotCopyGrants"]).should.equal(10)


@mock_redshift
def test_no_snapshot_copy_grants():
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.describe_snapshot_copy_grants()
    len(response["SnapshotCopyGrants"]).should.equal(0)


@mock_redshift
def test_create_cluster_all_attributes():
    """
    Ran against AWS (on 30/05/2021)
    Disabled assertions are bugs/not-yet-implemented
    """
    region = "us-east-1"
    client = boto3.client("redshift", region_name=region)
    cluster_identifier = "my-cluster"

    cluster_response = client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="dc1.large",
        MasterUsername="username",
        MasterUserPassword="Password1",
        DBName="my_db",
        ClusterType="multi-node",
        AvailabilityZone="us-east-1d",
        PreferredMaintenanceWindow="Mon:03:00-Mon:11:00",
        AutomatedSnapshotRetentionPeriod=10,
        Port=1234,
        ClusterVersion="1.0",
        AllowVersionUpgrade=True,
        NumberOfNodes=3,
    )
    cluster = cluster_response["Cluster"]
    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    cluster["NodeType"].should.equal("dc1.large")
    cluster["ClusterStatus"].should.equal("creating")
    # cluster["ClusterAvailabilityStatus"].should.equal("Modifying")
    cluster["MasterUsername"].should.equal("username")
    cluster["DBName"].should.equal("my_db")
    cluster["AutomatedSnapshotRetentionPeriod"].should.equal(10)
    # cluster["ManualSnapshotRetentionPeriod"].should.equal(-1)
    # cluster["ClusterSecurityGroups"].should.equal([])
    cluster["ClusterParameterGroups"].should.have.length_of(1)
    param_group = cluster["ClusterParameterGroups"][0]
    param_group.should.equal(
        {
            "ParameterGroupName": "default.redshift-1.0",
            "ParameterApplyStatus": "in-sync",
        }
    )
    # cluster["ClusterSubnetGroupName"].should.equal("default")
    cluster["AvailabilityZone"].should.equal("us-east-1d")
    cluster["PreferredMaintenanceWindow"].should.equal("Mon:03:00-Mon:11:00")
    cluster["ClusterVersion"].should.equal("1.0")
    cluster["AllowVersionUpgrade"].should.equal(True)
    cluster["NumberOfNodes"].should.equal(3)
    # cluster["PubliclyAccessible"].should.equal(True)
    cluster["Encrypted"].should.equal(False)
    cluster["EnhancedVpcRouting"].should.equal(False)

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]

    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    # AWS returns 'Available' (upper cased)
    cluster["ClusterStatus"].should.equal("available")
    # cluster["ClusterAvailabilityStatus"].should.equal("Available")
    cluster["NodeType"].should.equal("dc1.large")
    cluster["MasterUsername"].should.equal("username")
    cluster["DBName"].should.equal("my_db")
    # AWS returns: ClusterSecurityGroups=[]
    # cluster["ClusterSecurityGroups"][0]["ClusterSecurityGroupName"].should.equal("Default")
    # AWS returns default sg: [{'VpcSecurityGroupId': 'sg-...', 'Status': 'active'}],
    # cluster["VpcSecurityGroups"].should.equal([])
    # cluster["ClusterSubnetGroupName"].should.equal("default")
    # AWS returns default VPC ID
    # cluster["VpcId"].should.equal("vpc-...")
    cluster["AvailabilityZone"].should.equal("us-east-1d")
    cluster["PreferredMaintenanceWindow"].should.equal("Mon:03:00-Mon:11:00")
    cluster["ClusterParameterGroups"][0]["ParameterGroupName"].should.equal(
        "default.redshift-1.0"
    )
    cluster["AutomatedSnapshotRetentionPeriod"].should.equal(10)
    # Endpoint only returned when ClusterStatus=Available
    cluster["Endpoint"]["Address"].should.match(
        f"{cluster_identifier}.[a-z0-9]+.{region}.redshift.amazonaws.com"
    )
    cluster["Endpoint"]["Port"].should.equal(1234)
    cluster["ClusterVersion"].should.equal("1.0")
    cluster["AllowVersionUpgrade"].should.equal(True)
    cluster["NumberOfNodes"].should.equal(3)


@mock_redshift
def test_create_single_node_cluster_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"

    cluster = client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="Password1",
        DBName="my_db",
        ClusterType="single-node",
    )["Cluster"]
    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    cluster["NumberOfNodes"].should.equal(1)

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]

    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    cluster["NodeType"].should.equal("dw.hs1.xlarge")
    cluster["MasterUsername"].should.equal("username")
    cluster["DBName"].should.equal("my_db")
    cluster["NumberOfNodes"].should.equal(1)


@mock_redshift
@mock_ec2
def test_create_cluster_in_subnet_group():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client("redshift", region_name="us-east-1")
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
        ClusterSubnetGroupName="my_subnet_group",
    )

    cluster_response = client.describe_clusters(ClusterIdentifier="my_cluster")
    cluster = cluster_response["Clusters"][0]
    cluster["ClusterSubnetGroupName"].should.equal("my_subnet_group")


@mock_redshift
@mock_ec2
def test_create_cluster_in_subnet_group_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client("redshift", region_name="us-east-1")
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
        ClusterSubnetGroupName="my_subnet_group",
    )

    cluster_response = client.describe_clusters(ClusterIdentifier="my_cluster")
    cluster = cluster_response["Clusters"][0]
    cluster["ClusterSubnetGroupName"].should.equal("my_subnet_group")


@mock_redshift
def test_create_cluster_with_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group1",
        Description="This is my security group",
    )
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group2",
        Description="This is my security group",
    )

    cluster_identifier = "my_cluster"
    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        ClusterSecurityGroups=["security_group1", "security_group2"],
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = response["Clusters"][0]
    group_names = [
        group["ClusterSecurityGroupName"] for group in cluster["ClusterSecurityGroups"]
    ]
    set(group_names).should.equal({"security_group1", "security_group2"})


@mock_redshift
@mock_ec2
def test_create_cluster_with_vpc_security_groups_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_id = "my_cluster"
    security_group = ec2.create_security_group(
        Description="vpc_security_group", GroupName="a group", VpcId=vpc.id
    )
    client.create_cluster(
        ClusterIdentifier=cluster_id,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        VpcSecurityGroupIds=[security_group.id],
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_id)
    cluster = response["Clusters"][0]
    group_ids = [group["VpcSecurityGroupId"] for group in cluster["VpcSecurityGroups"]]
    list(group_ids).should.equal([security_group.id])


@mock_redshift
def test_create_cluster_with_iam_roles():
    iam_roles_arn = ["arn:aws:iam:::role/my-iam-role"]
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_id = "my_cluster"
    client.create_cluster(
        ClusterIdentifier=cluster_id,
        NodeType="dw.hs1.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        IamRoles=iam_roles_arn,
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_id)
    cluster = response["Clusters"][0]
    iam_roles = [role["IamRoleArn"] for role in cluster["IamRoles"]]
    iam_roles_arn.should.equal(iam_roles)


@mock_redshift
def test_create_cluster_with_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_id = "my-cluster"
    group = client.create_cluster_parameter_group(
        ParameterGroupName="my-parameter-group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my group",
    )["ClusterParameterGroup"]
    group["ParameterGroupName"].should.equal("my-parameter-group")
    group["ParameterGroupFamily"].should.equal("redshift-1.0")
    group["Description"].should.equal("This is my group")
    group["Tags"].should.equal([])

    cluster = client.create_cluster(
        ClusterIdentifier=cluster_id,
        NodeType="dc1.large",
        MasterUsername="username",
        MasterUserPassword="Password1",
        ClusterType="single-node",
        ClusterParameterGroupName="my-parameter-group",
    )["Cluster"]
    cluster["ClusterParameterGroups"].should.have.length_of(1)
    cluster["ClusterParameterGroups"][0]["ParameterGroupName"].should.equal(
        "my-parameter-group"
    )
    cluster["ClusterParameterGroups"][0]["ParameterApplyStatus"].should.equal("in-sync")

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_id)
    cluster = cluster_response["Clusters"][0]
    cluster["ClusterParameterGroups"].should.have.length_of(1)
    cluster["ClusterParameterGroups"][0]["ParameterGroupName"].should.equal(
        "my-parameter-group"
    )
    cluster["ClusterParameterGroups"][0]["ParameterApplyStatus"].should.equal("in-sync")


@mock_redshift
def test_describe_non_existent_cluster_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_clusters(ClusterIdentifier="not-a-cluster")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClusterNotFound")
    err["Message"].should.equal("Cluster not-a-cluster not found.")


@mock_redshift
def test_modify_cluster_vpc_routing():
    iam_roles_arn = ["arn:aws:iam:::role/my-iam-role"]
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"

    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="single-node",
        MasterUsername="username",
        MasterUserPassword="password",
        IamRoles=iam_roles_arn,
    )

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]
    cluster["EnhancedVpcRouting"].should.equal(False)

    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group", Description="security_group"
    )

    client.create_cluster_parameter_group(
        ParameterGroupName="my_parameter_group",
        ParameterGroupFamily="redshift-1.0",
        Description="my_parameter_group",
    )

    client.modify_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="multi-node",
        NodeType="ds2.8xlarge",
        NumberOfNodes=3,
        ClusterSecurityGroups=["security_group"],
        MasterUserPassword="new_password",
        ClusterParameterGroupName="my_parameter_group",
        AutomatedSnapshotRetentionPeriod=7,
        PreferredMaintenanceWindow="Tue:03:00-Tue:11:00",
        AllowVersionUpgrade=False,
        NewClusterIdentifier=cluster_identifier,
        EnhancedVpcRouting=True,
    )

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]
    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    cluster["NodeType"].should.equal("ds2.8xlarge")
    cluster["PreferredMaintenanceWindow"].should.equal("Tue:03:00-Tue:11:00")
    cluster["AutomatedSnapshotRetentionPeriod"].should.equal(7)
    cluster["AllowVersionUpgrade"].should.equal(False)
    # This one should remain unmodified.
    cluster["NumberOfNodes"].should.equal(3)
    cluster["EnhancedVpcRouting"].should.equal(True)


@mock_redshift
def test_modify_cluster_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group",
        Description="This is my security group",
    )
    client.create_cluster_parameter_group(
        ParameterGroupName="my_parameter_group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my parameter group",
    )

    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="single-node",
        MasterUsername="username",
        MasterUserPassword="password",
    )

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]
    cluster["EnhancedVpcRouting"].should.equal(False)

    client.modify_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="multi-node",
        NumberOfNodes=4,
        NodeType="dw.hs1.xlarge",
        ClusterSecurityGroups=["security_group"],
        MasterUserPassword="new_password",
        ClusterParameterGroupName="my_parameter_group",
        AutomatedSnapshotRetentionPeriod=7,
        PreferredMaintenanceWindow="Tue:03:00-Tue:11:00",
        AllowVersionUpgrade=False,
        NewClusterIdentifier=cluster_identifier,
    )

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]
    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    cluster["NodeType"].should.equal("dw.hs1.xlarge")
    cluster["ClusterSecurityGroups"][0]["ClusterSecurityGroupName"].should.equal(
        "security_group"
    )
    cluster["PreferredMaintenanceWindow"].should.equal("Tue:03:00-Tue:11:00")
    cluster["ClusterParameterGroups"][0]["ParameterGroupName"].should.equal(
        "my_parameter_group"
    )
    cluster["AutomatedSnapshotRetentionPeriod"].should.equal(7)
    cluster["AllowVersionUpgrade"].should.equal(False)
    cluster["NumberOfNodes"].should.equal(4)


@mock_redshift
@mock_ec2
def test_create_cluster_subnet_group():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    client = boto3.client("redshift", region_name="us-east-1")

    client.create_cluster_subnet_group(
        ClusterSubnetGroupName="my_subnet_group",
        Description="This is my subnet group",
        SubnetIds=[subnet1.id, subnet2.id],
    )

    subnets_response = client.describe_cluster_subnet_groups(
        ClusterSubnetGroupName="my_subnet_group"
    )
    my_subnet = subnets_response["ClusterSubnetGroups"][0]

    my_subnet["ClusterSubnetGroupName"].should.equal("my_subnet_group")
    my_subnet["Description"].should.equal("This is my subnet group")
    subnet_ids = [subnet["SubnetIdentifier"] for subnet in my_subnet["Subnets"]]
    set(subnet_ids).should.equal(set([subnet1.id, subnet2.id]))


@mock_redshift
def test_authorize_security_group_ingress():
    iam_roles_arn = ["arn:aws:iam:::role/my-iam-role"]
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"

    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        NodeType="single-node",
        MasterUsername="username",
        MasterUserPassword="password",
        IamRoles=iam_roles_arn,
    )

    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group",
        Description="security_group_description",
    )

    response = client.authorize_cluster_security_group_ingress(
        ClusterSecurityGroupName="security_group", CIDRIP="192.168.10.0/28"
    )

    assert (
        response.get("ClusterSecurityGroup").get("ClusterSecurityGroupName")
        == "security_group"
    )
    assert (
        response.get("ClusterSecurityGroup").get("Description")
        == "security_group_description"
    )
    assert (
        response.get("ClusterSecurityGroup").get("IPRanges")[0].get("Status")
        == "authorized"
    )
    assert (
        response.get("ClusterSecurityGroup").get("IPRanges")[0].get("CIDRIP")
        == "192.168.10.0/28"
    )

    with pytest.raises(ClientError) as ex:
        client.authorize_cluster_security_group_ingress(
            ClusterSecurityGroupName="invalid_security_group", CIDRIP="192.168.10.0/28"
        )
    assert ex.value.response["Error"]["Code"] == "ClusterSecurityGroupNotFoundFault"

    assert (
        ex.value.response["Error"]["Message"]
        == "The cluster security group name does not refer to an existing cluster security group."
    )


@mock_redshift
@mock_ec2
def test_create_invalid_cluster_subnet_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_cluster_subnet_group(
            ClusterSubnetGroupName="my_subnet",
            Description="This is my subnet group",
            SubnetIds=["subnet-1234"],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidSubnet")
    err["Message"].should.match(r"Subnet \[[a-z0-9-']+\] not found.")


@mock_redshift
@mock_ec2
def test_describe_non_existent_subnet_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_cluster_subnet_groups(ClusterSubnetGroupName="my_subnet")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClusterSubnetGroupNotFound")
    err["Message"].should.equal("Subnet group my_subnet not found.")


@mock_redshift
@mock_ec2
def test_delete_cluster_subnet_group():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client("redshift", region_name="us-east-1")

    client.create_cluster_subnet_group(
        ClusterSubnetGroupName="my_subnet_group",
        Description="This is my subnet group",
        SubnetIds=[subnet.id],
    )

    subnets_response = client.describe_cluster_subnet_groups()
    subnets = subnets_response["ClusterSubnetGroups"]
    subnets.should.have.length_of(1)

    client.delete_cluster_subnet_group(ClusterSubnetGroupName="my_subnet_group")

    subnets_response = client.describe_cluster_subnet_groups()
    subnets = subnets_response["ClusterSubnetGroups"]
    subnets.should.have.length_of(0)

    # Delete invalid id
    client.delete_cluster_subnet_group.when.called_with(
        ClusterSubnetGroupName="not-a-subnet-group"
    ).should.throw(ClientError)


@mock_redshift
def test_create_cluster_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    group = client.create_cluster_security_group(
        ClusterSecurityGroupName="my_security_group",
        Description="This is my security group",
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )["ClusterSecurityGroup"]
    group["ClusterSecurityGroupName"].should.equal("my_security_group")
    group["Description"].should.equal("This is my security group")
    group["EC2SecurityGroups"].should.equal([])
    group["IPRanges"].should.equal([])
    group["Tags"].should.equal([{"Key": "tag_key", "Value": "tag_value"}])

    groups_response = client.describe_cluster_security_groups(
        ClusterSecurityGroupName="my_security_group"
    )
    my_group = groups_response["ClusterSecurityGroups"][0]

    my_group["ClusterSecurityGroupName"].should.equal("my_security_group")
    my_group["Description"].should.equal("This is my security group")
    my_group["EC2SecurityGroups"].should.equal([])
    my_group["IPRanges"].should.equal([])
    my_group["Tags"].should.equal([{"Key": "tag_key", "Value": "tag_value"}])


@mock_redshift
def test_describe_non_existent_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_cluster_security_groups(ClusterSecurityGroupName="non-existent")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClusterSecurityGroupNotFound")
    err["Message"].should.equal("Security group non-existent not found.")


@mock_redshift
def test_delete_cluster_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster_security_group(
        ClusterSecurityGroupName="my_security_group",
        Description="This is my security group",
    )

    groups = client.describe_cluster_security_groups()["ClusterSecurityGroups"]
    groups.should.have.length_of(2)  # The default group already exists

    client.delete_cluster_security_group(ClusterSecurityGroupName="my_security_group")

    groups = client.describe_cluster_security_groups()["ClusterSecurityGroups"]
    groups.should.have.length_of(1)

    # Delete invalid id
    with pytest.raises(ClientError) as ex:
        client.delete_cluster_security_group(
            ClusterSecurityGroupName="not-a-security-group"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClusterSecurityGroupNotFound")
    err["Message"].should.equal("Security group not-a-security-group not found.")


@mock_redshift
def test_create_cluster_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    group = client.create_cluster_parameter_group(
        ParameterGroupName="my-parameter-group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my group",
    )["ClusterParameterGroup"]
    group["ParameterGroupName"].should.equal("my-parameter-group")
    group["ParameterGroupFamily"].should.equal("redshift-1.0")
    group["Description"].should.equal("This is my group")
    group["Tags"].should.equal([])

    groups_response = client.describe_cluster_parameter_groups(
        ParameterGroupName="my-parameter-group"
    )
    my_group = groups_response["ParameterGroups"][0]

    my_group["ParameterGroupName"].should.equal("my-parameter-group")
    my_group["ParameterGroupFamily"].should.equal("redshift-1.0")
    my_group["Description"].should.equal("This is my group")


@mock_redshift
def test_describe_non_existent_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_cluster_parameter_groups(
            ParameterGroupName="not-a-parameter-group"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClusterParameterGroupNotFound")
    err["Message"].should.equal("Parameter group not-a-parameter-group not found.")


@mock_redshift
def test_delete_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster_parameter_group(
        ParameterGroupName="my-parameter-group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my group",
    )
    client.describe_cluster_parameter_groups()["ParameterGroups"].should.have.length_of(
        2
    )

    x = client.delete_cluster_parameter_group(ParameterGroupName="my-parameter-group")
    del x["ResponseMetadata"]
    x.should.equal({})

    with pytest.raises(ClientError) as ex:
        client.delete_cluster_parameter_group(ParameterGroupName="my-parameter-group")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ClusterParameterGroupNotFound")
    # BUG: This is what AWS returns
    # err["Message"].should.equal("ParameterGroup not found: my-parameter-group")
    err["Message"].should.equal("Parameter group my-parameter-group not found.")

    client.describe_cluster_parameter_groups()["ParameterGroups"].should.have.length_of(
        1
    )


@mock_redshift
def test_create_cluster_snapshot_of_non_existent_cluster():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "non-existent-cluster-id"
    client.create_cluster_snapshot.when.called_with(
        SnapshotIdentifier="snapshot-id", ClusterIdentifier=cluster_identifier
    ).should.throw(ClientError, f"Cluster {cluster_identifier} not found.")


@mock_redshift
def test_automated_snapshot_on_cluster_creation():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"

    cluster_response = client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )

    cluster_response["Cluster"]["Tags"].should.equal(
        [{"Key": "tag_key", "Value": "tag_value"}]
    )
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier
    )
    resp_auto_snap["Snapshots"][0]["SnapshotType"].should.equal("automated")
    # Tags from cluster are not copied over to automated snapshot
    resp_auto_snap["Snapshots"][0]["Tags"].should.equal([])


@mock_redshift
def test_delete_automated_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"

    cluster_response = client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )
    cluster_response["Cluster"]["NodeType"].should.equal("ds2.xlarge")
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier
    )
    snapshot_identifier = resp_auto_snap["Snapshots"][0]["SnapshotIdentifier"]
    # Delete automated snapshot should result in error
    client.delete_cluster_snapshot.when.called_with(
        SnapshotIdentifier=snapshot_identifier
    ).should.throw(
        ClientError,
        f"Cannot delete the snapshot {snapshot_identifier} because only manual snapshots may be deleted",
    )


@mock_redshift
def test_presence_automated_snapshot_on_cluster_delete():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"

    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
    )
    # Ensure automated snapshot is available
    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    resp["Snapshots"].should.have.length_of(1)

    # Delete the cluster
    cluster_response = client.delete_cluster(
        ClusterIdentifier=cluster_identifier, SkipFinalClusterSnapshot=True
    )
    cluster = cluster_response["Cluster"]
    cluster["ClusterIdentifier"].should.equal(cluster_identifier)

    # Ensure Automated snapshot is deleted
    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    resp["Snapshots"].should.have.length_of(0)


@mock_redshift
def test_describe_snapshot_with_filter():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    snapshot_identifier = "my_snapshot"

    cluster_response = client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )
    cluster_response["Cluster"]["NodeType"].should.equal("ds2.xlarge")
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier, SnapshotType="automated"
    )
    auto_snapshot_identifier = resp_auto_snap["Snapshots"][0]["SnapshotIdentifier"]
    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier, ClusterIdentifier=cluster_identifier
    )

    resp = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier, SnapshotType="automated"
    )
    resp["Snapshots"].should.have.length_of(1)

    resp = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier, SnapshotType="manual"
    )
    resp["Snapshots"].should.have.length_of(1)

    resp = client.describe_cluster_snapshots(
        SnapshotIdentifier=snapshot_identifier, SnapshotType="manual"
    )
    resp["Snapshots"].should.have.length_of(1)

    resp = client.describe_cluster_snapshots(
        SnapshotIdentifier=auto_snapshot_identifier, SnapshotType="automated"
    )
    resp["Snapshots"].should.have.length_of(1)

    client.describe_cluster_snapshots.when.called_with(
        SnapshotIdentifier=snapshot_identifier, SnapshotType="automated"
    ).should.throw(ClientError, f"Snapshot {snapshot_identifier} not found.")

    client.describe_cluster_snapshots.when.called_with(
        SnapshotIdentifier=auto_snapshot_identifier, SnapshotType="manual"
    ).should.throw(ClientError, f"Snapshot {auto_snapshot_identifier} not found.")


@mock_redshift
def test_create_cluster_from_automated_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    original_cluster_identifier = "original-cluster"
    new_cluster_identifier = "new-cluster"

    client.create_cluster(
        ClusterIdentifier=original_cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )

    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=original_cluster_identifier, SnapshotType="automated"
    )
    auto_snapshot_identifier = resp_auto_snap["Snapshots"][0]["SnapshotIdentifier"]
    client.restore_from_cluster_snapshot.when.called_with(
        ClusterIdentifier=original_cluster_identifier,
        SnapshotIdentifier=auto_snapshot_identifier,
    ).should.throw(ClientError, "ClusterAlreadyExists")

    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=auto_snapshot_identifier,
        Port=1234,
    )
    response["Cluster"]["ClusterStatus"].should.equal("creating")

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    new_cluster["NodeType"].should.equal("ds2.xlarge")
    new_cluster["MasterUsername"].should.equal("username")
    new_cluster["Endpoint"]["Port"].should.equal(1234)
    new_cluster["EnhancedVpcRouting"].should.equal(True)

    # Make sure the new cluster has automated snapshot on cluster creation
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=new_cluster_identifier, SnapshotType="automated"
    )
    resp_auto_snap["Snapshots"].should.have.length_of(1)


@mock_redshift
def test_create_cluster_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    snapshot_identifier = "my_snapshot"

    cluster_response = client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )
    cluster_response["Cluster"]["NodeType"].should.equal("ds2.xlarge")

    snapshot_response = client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{"Key": "test-tag-key", "Value": "test-tag-value"}],
    )
    snapshot = snapshot_response["Snapshot"]
    snapshot["SnapshotIdentifier"].should.equal(snapshot_identifier)
    snapshot["ClusterIdentifier"].should.equal(cluster_identifier)
    snapshot["NumberOfNodes"].should.equal(1)
    snapshot["NodeType"].should.equal("ds2.xlarge")
    snapshot["MasterUsername"].should.equal("username")


@mock_redshift
def test_describe_cluster_snapshots():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    snapshot_identifier_1 = "my_snapshot_1"
    snapshot_identifier_2 = "my_snapshot_2"

    client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
    )

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier_1, ClusterIdentifier=cluster_identifier
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier_2, ClusterIdentifier=cluster_identifier
    )

    resp_snap_1 = client.describe_cluster_snapshots(
        SnapshotIdentifier=snapshot_identifier_1
    )
    snapshot_1 = resp_snap_1["Snapshots"][0]
    snapshot_1["SnapshotIdentifier"].should.equal(snapshot_identifier_1)
    snapshot_1["ClusterIdentifier"].should.equal(cluster_identifier)
    snapshot_1["NumberOfNodes"].should.equal(1)
    snapshot_1["NodeType"].should.equal("ds2.xlarge")
    snapshot_1["MasterUsername"].should.equal("username")

    resp_snap_2 = client.describe_cluster_snapshots(
        SnapshotIdentifier=snapshot_identifier_2
    )
    snapshot_2 = resp_snap_2["Snapshots"][0]
    snapshot_2["SnapshotIdentifier"].should.equal(snapshot_identifier_2)
    snapshot_2["ClusterIdentifier"].should.equal(cluster_identifier)
    snapshot_2["NumberOfNodes"].should.equal(1)
    snapshot_2["NodeType"].should.equal("ds2.xlarge")
    snapshot_2["MasterUsername"].should.equal("username")

    resp_clust = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier, SnapshotType="manual"
    )
    resp_clust["Snapshots"][0].should.equal(resp_snap_1["Snapshots"][0])
    resp_clust["Snapshots"][1].should.equal(resp_snap_2["Snapshots"][0])


@mock_redshift
def test_describe_cluster_snapshots_not_found_error():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "non-existent-cluster-id"
    snapshot_identifier = "non-existent-snapshot-id"

    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    resp["Snapshots"].should.have.length_of(0)

    client.describe_cluster_snapshots.when.called_with(
        SnapshotIdentifier=snapshot_identifier
    ).should.throw(ClientError, f"Snapshot {snapshot_identifier} not found.")


@mock_redshift
def test_delete_cluster_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    snapshot_identifier = "my_snapshot"

    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier, ClusterIdentifier=cluster_identifier
    )

    snapshots = client.describe_cluster_snapshots()["Snapshots"]
    list(snapshots).should.have.length_of(2)

    client.delete_cluster_snapshot(SnapshotIdentifier=snapshot_identifier)["Snapshot"][
        "Status"
    ].should.equal("deleted")

    snapshots = client.describe_cluster_snapshots()["Snapshots"]
    list(snapshots).should.have.length_of(1)

    # Delete invalid id
    client.delete_cluster_snapshot.when.called_with(
        SnapshotIdentifier="non-existent"
    ).should.throw(ClientError, "Snapshot non-existent not found.")


@mock_redshift
def test_cluster_snapshot_already_exists():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    snapshot_identifier = "my_snapshot"

    client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
    )

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier, ClusterIdentifier=cluster_identifier
    )

    client.create_cluster_snapshot.when.called_with(
        SnapshotIdentifier=snapshot_identifier, ClusterIdentifier=cluster_identifier
    ).should.throw(ClientError, f"{snapshot_identifier} already exists")


@mock_redshift
def test_create_cluster_from_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    original_cluster_identifier = "original-cluster"
    original_snapshot_identifier = "original-snapshot"
    new_cluster_identifier = "new-cluster"

    client.create_cluster(
        ClusterIdentifier=original_cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )

    client.create_cluster_snapshot(
        SnapshotIdentifier=original_snapshot_identifier,
        ClusterIdentifier=original_cluster_identifier,
    )

    client.restore_from_cluster_snapshot.when.called_with(
        ClusterIdentifier=original_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
    ).should.throw(ClientError, "ClusterAlreadyExists")

    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        Port=1234,
    )
    response["Cluster"]["ClusterStatus"].should.equal("creating")

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    new_cluster["NodeType"].should.equal("ds2.xlarge")
    new_cluster["MasterUsername"].should.equal("username")
    new_cluster["Endpoint"]["Port"].should.equal(1234)
    new_cluster["EnhancedVpcRouting"].should.equal(True)


@mock_redshift
def test_create_cluster_with_node_type_from_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    original_cluster_identifier = "original-cluster"
    original_snapshot_identifier = "original-snapshot"
    new_cluster_identifier = "new-cluster"

    client.create_cluster(
        ClusterIdentifier=original_cluster_identifier,
        ClusterType="multi-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
        NumberOfNodes=2,
    )

    client.create_cluster_snapshot(
        SnapshotIdentifier=original_snapshot_identifier,
        ClusterIdentifier=original_cluster_identifier,
    )

    client.restore_from_cluster_snapshot.when.called_with(
        ClusterIdentifier=original_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
    ).should.throw(ClientError, "ClusterAlreadyExists")

    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        NodeType="ra3.xlplus",
        NumberOfNodes=3,
    )
    response["Cluster"]["ClusterStatus"].should.equal("creating")

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    new_cluster["NodeType"].should.equal("ra3.xlplus")
    new_cluster["NumberOfNodes"].should.equal(3)
    new_cluster["MasterUsername"].should.equal("username")
    new_cluster["EnhancedVpcRouting"].should.equal(True)


@mock_redshift
def test_create_cluster_from_snapshot_with_waiter():
    client = boto3.client("redshift", region_name="us-east-1")
    original_cluster_identifier = "original-cluster"
    original_snapshot_identifier = "original-snapshot"
    new_cluster_identifier = "new-cluster"

    client.create_cluster(
        ClusterIdentifier=original_cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        EnhancedVpcRouting=True,
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier=original_snapshot_identifier,
        ClusterIdentifier=original_cluster_identifier,
    )
    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        Port=1234,
    )
    response["Cluster"]["ClusterStatus"].should.equal("creating")

    client.get_waiter("cluster_restored").wait(
        ClusterIdentifier=new_cluster_identifier,
        WaiterConfig={"Delay": 1, "MaxAttempts": 2},
    )

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    new_cluster["NodeType"].should.equal("ds2.xlarge")
    new_cluster["MasterUsername"].should.equal("username")
    new_cluster["EnhancedVpcRouting"].should.equal(True)
    new_cluster["Endpoint"]["Port"].should.equal(1234)


@mock_redshift
def test_create_cluster_from_non_existent_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    client.restore_from_cluster_snapshot.when.called_with(
        ClusterIdentifier="cluster-id", SnapshotIdentifier="non-existent-snapshot"
    ).should.throw(ClientError, "Snapshot non-existent-snapshot not found.")


@mock_redshift
def test_create_cluster_status_update():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "test-cluster"

    response = client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
    )
    response["Cluster"]["ClusterStatus"].should.equal("creating")

    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    response["Clusters"][0]["ClusterStatus"].should.equal("available")


@mock_redshift
def test_describe_tags_with_resource_type():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    cluster_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:{cluster_identifier}"
    )
    snapshot_identifier = "my_snapshot"
    snapshot_arn = f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:snapshot:{cluster_identifier}/{snapshot_identifier}"
    tag_key = "test-tag-key"
    tag_value = "test-tag-value"

    client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        Tags=[{"Key": tag_key, "Value": tag_value}],
    )
    tags_response = client.describe_tags(ResourceType="cluster")
    tagged_resources = tags_response["TaggedResources"]
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]["ResourceType"].should.equal("cluster")
    tagged_resources[0]["ResourceName"].should.equal(cluster_arn)
    tag = tagged_resources[0]["Tag"]
    tag["Key"].should.equal(tag_key)
    tag["Value"].should.equal(tag_value)

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{"Key": tag_key, "Value": tag_value}],
    )
    tags_response = client.describe_tags(ResourceType="snapshot")
    tagged_resources = tags_response["TaggedResources"]
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]["ResourceType"].should.equal("snapshot")
    tagged_resources[0]["ResourceName"].should.equal(snapshot_arn)
    tag = tagged_resources[0]["Tag"]
    tag["Key"].should.equal(tag_key)
    tag["Value"].should.equal(tag_value)


@mock_redshift
def test_describe_tags_cannot_specify_resource_type_and_resource_name():
    client = boto3.client("redshift", region_name="us-east-1")
    resource_name = f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:cluster-id"
    resource_type = "cluster"
    client.describe_tags.when.called_with(
        ResourceName=resource_name, ResourceType=resource_type
    ).should.throw(ClientError, "using either an ARN or a resource type")


@mock_redshift
def test_describe_tags_with_resource_name():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "cluster-id"
    cluster_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:{cluster_identifier}"
    )
    snapshot_identifier = "snapshot-id"
    snapshot_arn = f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:snapshot:{cluster_identifier}/{snapshot_identifier}"
    tag_key = "test-tag-key"
    tag_value = "test-tag-value"

    client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        Tags=[{"Key": tag_key, "Value": tag_value}],
    )
    tags_response = client.describe_tags(ResourceName=cluster_arn)
    tagged_resources = tags_response["TaggedResources"]
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]["ResourceType"].should.equal("cluster")
    tagged_resources[0]["ResourceName"].should.equal(cluster_arn)
    tag = tagged_resources[0]["Tag"]
    tag["Key"].should.equal(tag_key)
    tag["Value"].should.equal(tag_value)

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{"Key": tag_key, "Value": tag_value}],
    )
    tags_response = client.describe_tags(ResourceName=snapshot_arn)
    tagged_resources = tags_response["TaggedResources"]
    list(tagged_resources).should.have.length_of(1)
    tagged_resources[0]["ResourceType"].should.equal("snapshot")
    tagged_resources[0]["ResourceName"].should.equal(snapshot_arn)
    tag = tagged_resources[0]["Tag"]
    tag["Key"].should.equal(tag_key)
    tag["Value"].should.equal(tag_value)


@mock_redshift
def test_create_tags():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "cluster-id"
    cluster_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:{cluster_identifier}"
    )
    tag_key = "test-tag-key"
    tag_value = "test-tag-value"
    num_tags = 5
    tags = []
    for i in range(0, num_tags):
        tag = {"Key": f"{tag_key}-{i}", "Value": f"{tag_value}-{i}"}
        tags.append(tag)

    client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
    )
    client.create_tags(ResourceName=cluster_arn, Tags=tags)
    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = response["Clusters"][0]
    list(cluster["Tags"]).should.have.length_of(num_tags)
    response = client.describe_tags(ResourceName=cluster_arn)
    list(response["TaggedResources"]).should.have.length_of(num_tags)


@mock_redshift
def test_delete_tags():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "cluster-id"
    cluster_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:{cluster_identifier}"
    )
    tag_key = "test-tag-key"
    tag_value = "test-tag-value"
    tags = []
    for i in range(1, 2):
        tag = {"Key": f"{tag_key}-{i}", "Value": f"{tag_value}-{i}"}
        tags.append(tag)

    client.create_cluster(
        DBName="test-db",
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="username",
        MasterUserPassword="password",
        Tags=tags,
    )
    client.delete_tags(
        ResourceName=cluster_arn,
        TagKeys=[tag["Key"] for tag in tags if tag["Key"] != f"{tag_key}-1"],
    )
    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = response["Clusters"][0]
    list(cluster["Tags"]).should.have.length_of(1)
    response = client.describe_tags(ResourceName=cluster_arn)
    list(response["TaggedResources"]).should.have.length_of(1)


@mock_ec2
@mock_redshift
def test_describe_tags_all_resource_types():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.describe_tags()
    list(response["TaggedResources"]).should.have.length_of(0)
    client.create_cluster_subnet_group(
        ClusterSubnetGroupName="my_subnet_group",
        Description="This is my subnet group",
        SubnetIds=[subnet.id],
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )
    client.create_cluster_security_group(
        ClusterSecurityGroupName="security_group1",
        Description="This is my security group",
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )
    client.create_cluster(
        DBName="test",
        ClusterIdentifier="my_cluster",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )
    client.create_cluster_snapshot(
        SnapshotIdentifier="my_snapshot",
        ClusterIdentifier="my_cluster",
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )
    client.create_cluster_parameter_group(
        ParameterGroupName="my_parameter_group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my parameter group",
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )
    response = client.describe_tags()
    expected_types = [
        "cluster",
        "parametergroup",
        "securitygroup",
        "snapshot",
        "subnetgroup",
    ]
    tagged_resources = response["TaggedResources"]
    returned_types = [resource["ResourceType"] for resource in tagged_resources]
    list(tagged_resources).should.have.length_of(len(expected_types))
    set(returned_types).should.equal(set(expected_types))


@mock_redshift
def test_tagged_resource_not_found_error():
    client = boto3.client("redshift", region_name="us-east-1")

    cluster_arn = "arn:aws:redshift:us-east-1::cluster:fake"
    client.describe_tags.when.called_with(ResourceName=cluster_arn).should.throw(
        ClientError, "cluster (fake) not found."
    )

    snapshot_arn = "arn:aws:redshift:us-east-1::snapshot:cluster-id/snap-id"
    client.delete_tags.when.called_with(
        ResourceName=snapshot_arn, TagKeys=["test"]
    ).should.throw(ClientError, "snapshot (snap-id) not found.")

    client.describe_tags.when.called_with(ResourceType="cluster").should.throw(
        ClientError, "resource of type 'cluster' not found."
    )

    client.describe_tags.when.called_with(ResourceName="bad:arn").should.throw(
        ClientError, "Tagging is not supported for this type of resource"
    )


@mock_redshift
def test_enable_snapshot_copy():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster(
        ClusterIdentifier="test",
        ClusterType="single-node",
        DBName="test",
        Encrypted=True,
        MasterUsername="user",
        MasterUserPassword="password",
        NodeType="ds2.xlarge",
    )
    with pytest.raises(ClientError) as ex:
        client.enable_snapshot_copy(
            ClusterIdentifier="test", DestinationRegion="us-west-2", RetentionPeriod=3
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.value.response["Error"]["Message"].should.contain(
        "SnapshotCopyGrantName is required for Snapshot Copy on KMS encrypted clusters."
    )
    with pytest.raises(ClientError) as ex:
        client.enable_snapshot_copy(
            ClusterIdentifier="test",
            DestinationRegion="us-east-1",
            RetentionPeriod=3,
            SnapshotCopyGrantName="invalid-us-east-1-to-us-east-1",
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownSnapshotCopyRegionFault")
    ex.value.response["Error"]["Message"].should.contain("Invalid region us-east-1")
    client.enable_snapshot_copy(
        ClusterIdentifier="test",
        DestinationRegion="us-west-2",
        RetentionPeriod=3,
        SnapshotCopyGrantName="copy-us-east-1-to-us-west-2",
    )
    response = client.describe_clusters(ClusterIdentifier="test")
    cluster_snapshot_copy_status = response["Clusters"][0]["ClusterSnapshotCopyStatus"]
    cluster_snapshot_copy_status["RetentionPeriod"].should.equal(3)
    cluster_snapshot_copy_status["DestinationRegion"].should.equal("us-west-2")
    cluster_snapshot_copy_status["SnapshotCopyGrantName"].should.equal(
        "copy-us-east-1-to-us-west-2"
    )


@mock_redshift
def test_enable_snapshot_copy_unencrypted():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster(
        ClusterIdentifier="test",
        ClusterType="single-node",
        DBName="test",
        MasterUsername="user",
        MasterUserPassword="password",
        NodeType="ds2.xlarge",
    )
    client.enable_snapshot_copy(ClusterIdentifier="test", DestinationRegion="us-west-2")
    response = client.describe_clusters(ClusterIdentifier="test")
    cluster_snapshot_copy_status = response["Clusters"][0]["ClusterSnapshotCopyStatus"]
    cluster_snapshot_copy_status["RetentionPeriod"].should.equal(7)
    cluster_snapshot_copy_status["DestinationRegion"].should.equal("us-west-2")


@mock_redshift
def test_disable_snapshot_copy():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
    )
    client.enable_snapshot_copy(
        ClusterIdentifier="test",
        DestinationRegion="us-west-2",
        RetentionPeriod=3,
        SnapshotCopyGrantName="copy-us-east-1-to-us-west-2",
    )
    client.disable_snapshot_copy(ClusterIdentifier="test")
    response = client.describe_clusters(ClusterIdentifier="test")
    response["Clusters"][0].shouldnt.contain("ClusterSnapshotCopyStatus")


@mock_redshift
def test_modify_snapshot_copy_retention_period():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
    )
    client.enable_snapshot_copy(
        ClusterIdentifier="test",
        DestinationRegion="us-west-2",
        RetentionPeriod=3,
        SnapshotCopyGrantName="copy-us-east-1-to-us-west-2",
    )
    client.modify_snapshot_copy_retention_period(
        ClusterIdentifier="test", RetentionPeriod=5
    )
    response = client.describe_clusters(ClusterIdentifier="test")
    cluster_snapshot_copy_status = response["Clusters"][0]["ClusterSnapshotCopyStatus"]
    cluster_snapshot_copy_status["RetentionPeriod"].should.equal(5)


@mock_redshift
def test_create_duplicate_cluster_fails():
    kwargs = {
        "ClusterIdentifier": "test",
        "ClusterType": "single-node",
        "DBName": "test",
        "MasterUsername": "user",
        "MasterUserPassword": "password",
        "NodeType": "ds2.xlarge",
    }
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster(**kwargs)
    client.create_cluster.when.called_with(**kwargs).should.throw(
        ClientError, "ClusterAlreadyExists"
    )


@mock_redshift
def test_delete_cluster_with_final_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_cluster(ClusterIdentifier="non-existent")
    ex.value.response["Error"]["Code"].should.equal("ClusterNotFound")
    ex.value.response["Error"]["Message"].should.match(r"Cluster .+ not found.")

    cluster_identifier = "my_cluster"
    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        DBName="test",
        MasterUsername="user",
        MasterUserPassword="password",
        NodeType="ds2.xlarge",
    )

    with pytest.raises(ClientError) as ex:
        client.delete_cluster(
            ClusterIdentifier=cluster_identifier, SkipFinalClusterSnapshot=False
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterCombination")
    ex.value.response["Error"]["Message"].should.contain(
        "FinalClusterSnapshotIdentifier is required unless SkipFinalClusterSnapshot is specified."
    )

    snapshot_identifier = "my_snapshot"
    client.delete_cluster(
        ClusterIdentifier=cluster_identifier,
        SkipFinalClusterSnapshot=False,
        FinalClusterSnapshotIdentifier=snapshot_identifier,
    )

    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    resp["Snapshots"].should.have.length_of(1)
    resp["Snapshots"][0]["SnapshotIdentifier"].should.equal(snapshot_identifier)
    resp["Snapshots"][0]["SnapshotType"].should.equal("manual")

    with pytest.raises(ClientError) as ex:
        client.describe_clusters(ClusterIdentifier=cluster_identifier)
    ex.value.response["Error"]["Code"].should.equal("ClusterNotFound")
    ex.value.response["Error"]["Message"].should.match(r"Cluster .+ not found.")


@mock_redshift
def test_delete_cluster_without_final_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        DBName="test",
        MasterUsername="user",
        MasterUserPassword="password",
        NodeType="ds2.xlarge",
    )
    cluster_response = client.delete_cluster(
        ClusterIdentifier=cluster_identifier, SkipFinalClusterSnapshot=True
    )
    cluster = cluster_response["Cluster"]
    cluster["ClusterIdentifier"].should.equal(cluster_identifier)
    cluster["NodeType"].should.equal("ds2.xlarge")
    # Bug: This is what AWS returns
    # cluster["ClusterStatus"].should.equal("deleting")
    cluster["MasterUsername"].should.equal("user")
    cluster["DBName"].should.equal("test")
    endpoint = cluster["Endpoint"]
    endpoint["Address"].should.match(
        f"{cluster_identifier}.[a-z0-9]+.us-east-1.redshift.amazonaws.com"
    )
    endpoint["Port"].should.equal(5439)
    cluster["AutomatedSnapshotRetentionPeriod"].should.equal(1)
    cluster["ClusterParameterGroups"].should.have.length_of(1)
    param_group = cluster["ClusterParameterGroups"][0]
    param_group.should.equal(
        {
            "ParameterGroupName": "default.redshift-1.0",
            "ParameterApplyStatus": "in-sync",
        }
    )
    cluster["AvailabilityZone"].should.equal("us-east-1a")
    cluster["ClusterVersion"].should.equal("1.0")
    cluster["AllowVersionUpgrade"].should.equal(True)
    cluster["NumberOfNodes"].should.equal(1)
    cluster["Encrypted"].should.equal(False)
    cluster["EnhancedVpcRouting"].should.equal(False)

    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    resp["Snapshots"].should.have.length_of(0)

    with pytest.raises(ClientError) as ex:
        client.describe_clusters(ClusterIdentifier=cluster_identifier)
    ex.value.response["Error"]["Code"].should.equal("ClusterNotFound")
    ex.value.response["Error"]["Message"].should.match(r"Cluster .+ not found.")


@mock_redshift
def test_resize_cluster():
    client = boto3.client("redshift", region_name="us-east-1")
    resp = client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
    )
    resp["Cluster"]["NumberOfNodes"].should.equal(1)

    client.modify_cluster(
        ClusterIdentifier="test", ClusterType="multi-node", NumberOfNodes=2
    )
    resp = client.describe_clusters(ClusterIdentifier="test")
    resp["Clusters"][0]["NumberOfNodes"].should.equal(2)

    client.modify_cluster(ClusterIdentifier="test", ClusterType="single-node")
    resp = client.describe_clusters(ClusterIdentifier="test")
    resp["Clusters"][0]["NumberOfNodes"].should.equal(1)

    with pytest.raises(ClientError) as ex:
        client.modify_cluster(
            ClusterIdentifier="test", ClusterType="multi-node", NumberOfNodes=1
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterCombination")
    ex.value.response["Error"]["Message"].should.contain(
        "Number of nodes for cluster type multi-node must be greater than or equal to 2"
    )

    with pytest.raises(ClientError) as ex:
        client.modify_cluster(
            ClusterIdentifier="test",
            ClusterType="invalid-cluster-type",
            NumberOfNodes=1,
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.value.response["Error"]["Message"].should.contain("Invalid cluster type")


@mock_redshift
def test_get_cluster_credentials_non_existent_cluster_and_user():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_cluster_credentials(
            ClusterIdentifier="non-existent", DbUser="some_user"
        )
    ex.value.response["Error"]["Code"].should.equal("ClusterNotFound")
    ex.value.response["Error"]["Message"].should.match(r"Cluster .+ not found.")


@mock_redshift
def test_get_cluster_credentials_invalid_duration():
    client = boto3.client("redshift", region_name="us-east-1")

    cluster_identifier = "my_cluster"
    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        DBName="test",
        MasterUsername="user",
        MasterUserPassword="password",
        NodeType="ds2.xlarge",
    )

    db_user = "some_user"
    with pytest.raises(ClientError) as ex:
        client.get_cluster_credentials(
            ClusterIdentifier=cluster_identifier, DbUser=db_user, DurationSeconds=899
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.value.response["Error"]["Message"].should.contain(
        "Token duration must be between 900 and 3600 seconds"
    )

    with pytest.raises(ClientError) as ex:
        client.get_cluster_credentials(
            ClusterIdentifier=cluster_identifier, DbUser=db_user, DurationSeconds=3601
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
    ex.value.response["Error"]["Message"].should.contain(
        "Token duration must be between 900 and 3600 seconds"
    )


@mock_redshift
def test_get_cluster_credentials():
    client = boto3.client("redshift", region_name="us-east-1")

    cluster_identifier = "my_cluster"
    client.create_cluster(
        ClusterIdentifier=cluster_identifier,
        ClusterType="single-node",
        DBName="test",
        MasterUsername="user",
        MasterUserPassword="password",
        NodeType="ds2.xlarge",
    )

    expected_expiration = time.mktime(
        (datetime.datetime.now() + datetime.timedelta(0, 900)).timetuple()
    )
    db_user = "some_user"
    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser=db_user
    )
    response["DbUser"].should.equal(f"IAM:{db_user}")
    assert time.mktime((response["Expiration"]).timetuple()) == pytest.approx(
        expected_expiration
    )
    response["DbPassword"].should.have.length_of(32)

    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser=db_user, AutoCreate=True
    )
    response["DbUser"].should.equal(f"IAMA:{db_user}")

    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser="some_other_user", AutoCreate=False
    )
    response["DbUser"].should.equal("IAM:some_other_user")

    expected_expiration = time.mktime(
        (datetime.datetime.now() + datetime.timedelta(0, 3000)).timetuple()
    )
    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser=db_user, DurationSeconds=3000
    )
    assert time.mktime(response["Expiration"].timetuple()) == pytest.approx(
        expected_expiration
    )


@mock_redshift
def test_pause_cluster():
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
    )
    cluster = response["Cluster"]
    cluster["ClusterIdentifier"].should.equal("test")

    response = client.pause_cluster(ClusterIdentifier="test")
    cluster = response["Cluster"]
    cluster["ClusterIdentifier"].should.equal("test")
    # Verify this call returns all properties
    cluster["NodeType"].should.equal("ds2.xlarge")
    cluster["ClusterStatus"].should.equal("paused")
    cluster["ClusterVersion"].should.equal("1.0")
    cluster["AllowVersionUpgrade"].should.equal(True)
    cluster["Endpoint"]["Port"].should.equal(5439)


@mock_redshift
def test_pause_unknown_cluster():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.pause_cluster(ClusterIdentifier="test")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFound")
    err["Message"].should.equal("Cluster test not found.")


@mock_redshift
def test_resume_cluster():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster(
        DBName="test",
        ClusterIdentifier="test",
        ClusterType="single-node",
        NodeType="ds2.xlarge",
        MasterUsername="user",
        MasterUserPassword="password",
    )

    client.pause_cluster(ClusterIdentifier="test")
    response = client.resume_cluster(ClusterIdentifier="test")
    cluster = response["Cluster"]
    cluster["ClusterIdentifier"].should.equal("test")
    # Verify this call returns all properties
    cluster["NodeType"].should.equal("ds2.xlarge")
    cluster["ClusterStatus"].should.equal("available")
    cluster["ClusterVersion"].should.equal("1.0")
    cluster["AllowVersionUpgrade"].should.equal(True)
    cluster["Endpoint"]["Port"].should.equal(5439)


@mock_redshift
def test_resume_unknown_cluster():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.resume_cluster(ClusterIdentifier="test")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFound")
    err["Message"].should.equal("Cluster test not found.")
