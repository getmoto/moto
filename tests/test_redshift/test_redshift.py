import datetime
import re
import time

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzutc

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
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
    assert cluster["ClusterIdentifier"] == "test"
    assert cluster["NodeType"] == "ds2.xlarge"
    assert cluster["ClusterStatus"] == "creating"
    create_time = cluster["ClusterCreateTime"]
    assert create_time < datetime.datetime.now(create_time.tzinfo)
    assert create_time > (
        datetime.datetime.now(create_time.tzinfo) - datetime.timedelta(minutes=1)
    )
    assert cluster["MasterUsername"] == "user"
    assert cluster["DBName"] == "test"
    assert cluster["AutomatedSnapshotRetentionPeriod"] == 1
    assert cluster["ClusterSecurityGroups"] == [
        {"ClusterSecurityGroupName": "Default", "Status": "active"}
    ]
    assert cluster["VpcSecurityGroups"] == []
    assert cluster["ClusterParameterGroups"] == [
        {
            "ParameterGroupName": "default.redshift-1.0",
            "ParameterApplyStatus": "in-sync",
        }
    ]
    assert cluster["ClusterSubnetGroupName"] == ""
    assert cluster["AvailabilityZone"] == "us-east-1a"
    assert cluster["PreferredMaintenanceWindow"] == "Mon:03:00-Mon:03:30"
    assert cluster["ClusterVersion"] == "1.0"
    assert cluster["AllowVersionUpgrade"] is True
    assert cluster["NumberOfNodes"] == 1
    assert cluster["EnhancedVpcRouting"] is False
    assert cluster["KmsKeyId"] == ""
    assert cluster["Endpoint"]["Port"] == 5439


@mock_aws
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
    assert response["Cluster"]["NodeType"] == "ds2.xlarge"
    create_time = response["Cluster"]["ClusterCreateTime"]
    assert create_time < datetime.datetime.now(create_time.tzinfo)
    assert create_time > (
        datetime.datetime.now(create_time.tzinfo) - datetime.timedelta(minutes=1)
    )
    assert response["Cluster"]["EnhancedVpcRouting"] is True


@mock_aws
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
    assert response["Cluster"]["KmsKeyId"] == kms_key_id

    response = client.describe_clusters()
    clusters = response.get("Clusters", [])
    assert len(clusters) == 1

    cluster = clusters[0]
    assert cluster["KmsKeyId"] == kms_key_id


@mock_aws
def test_create_snapshot_copy_grant():
    client = boto3.client("redshift", region_name="us-east-1")
    grants = client.create_snapshot_copy_grant(
        SnapshotCopyGrantName="test-us-east-1", KmsKeyId="fake"
    )
    assert grants["SnapshotCopyGrant"]["SnapshotCopyGrantName"] == "test-us-east-1"
    assert grants["SnapshotCopyGrant"]["KmsKeyId"] == "fake"

    client.delete_snapshot_copy_grant(SnapshotCopyGrantName="test-us-east-1")

    with pytest.raises(ClientError):
        client.describe_snapshot_copy_grants(SnapshotCopyGrantName="test-us-east-1")


@mock_aws
def test_create_many_snapshot_copy_grants():
    client = boto3.client("redshift", region_name="us-east-1")

    for i in range(10):
        client.create_snapshot_copy_grant(
            SnapshotCopyGrantName=f"test-us-east-1-{i}", KmsKeyId="fake"
        )
    response = client.describe_snapshot_copy_grants()
    assert len(response["SnapshotCopyGrants"]) == 10


@mock_aws
def test_no_snapshot_copy_grants():
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.describe_snapshot_copy_grants()
    assert len(response["SnapshotCopyGrants"]) == 0


@mock_aws
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
    assert cluster["ClusterIdentifier"] == cluster_identifier
    assert cluster["NodeType"] == "dc1.large"
    assert cluster["ClusterStatus"] == "creating"
    # assert cluster["ClusterAvailabilityStatus"] == "Modifying"
    assert cluster["MasterUsername"] == "username"
    assert cluster["DBName"] == "my_db"
    assert cluster["AutomatedSnapshotRetentionPeriod"] == 10
    # assert cluster["ManualSnapshotRetentionPeriod"] == -1
    # assert cluster["ClusterSecurityGroups"] == []
    assert len(cluster["ClusterParameterGroups"]) == 1
    param_group = cluster["ClusterParameterGroups"][0]
    assert param_group == {
        "ParameterGroupName": "default.redshift-1.0",
        "ParameterApplyStatus": "in-sync",
    }
    # assert cluster["ClusterSubnetGroupName"] == "default"
    assert cluster["AvailabilityZone"] == "us-east-1d"
    assert cluster["PreferredMaintenanceWindow"] == "Mon:03:00-Mon:11:00"
    assert cluster["ClusterVersion"] == "1.0"
    assert cluster["AllowVersionUpgrade"] is True
    assert cluster["NumberOfNodes"] == 3
    # assert cluster["PubliclyAccessible"] is True
    assert cluster["Encrypted"] is False
    assert cluster["EnhancedVpcRouting"] is False

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]

    assert cluster["ClusterIdentifier"] == cluster_identifier
    # AWS returns 'Available' (upper cased)
    assert cluster["ClusterStatus"] == "available"
    # assert cluster["ClusterAvailabilityStatus"] == "Available"
    assert cluster["NodeType"] == "dc1.large"
    assert cluster["MasterUsername"] == "username"
    assert cluster["DBName"] == "my_db"
    # AWS returns: ClusterSecurityGroups=[]
    # assert cluster["ClusterSecurityGroups"][0]["ClusterSecurityGroupName"] == "Default"
    # AWS returns default sg: [{'VpcSecurityGroupId': 'sg-...', 'Status': 'active'}],
    # assert cluster["VpcSecurityGroups"] == []
    # assert cluster["ClusterSubnetGroupName"] == "default"
    # AWS returns default VPC ID
    # assert cluster["VpcId"] == "vpc-..."
    assert cluster["AvailabilityZone"] == "us-east-1d"
    assert cluster["PreferredMaintenanceWindow"] == "Mon:03:00-Mon:11:00"
    assert cluster["ClusterParameterGroups"][0]["ParameterGroupName"] == (
        "default.redshift-1.0"
    )
    assert cluster["AutomatedSnapshotRetentionPeriod"] == 10
    # Endpoint only returned when ClusterStatus=Available
    assert re.match(
        f"{cluster_identifier}.[a-z0-9]+.{region}.redshift.amazonaws.com",
        cluster["Endpoint"]["Address"],
    )
    assert cluster["Endpoint"]["Port"] == 1234
    assert cluster["ClusterVersion"] == "1.0"
    assert cluster["AllowVersionUpgrade"] is True
    assert cluster["NumberOfNodes"] == 3
    assert cluster["TotalStorageCapacityInMegaBytes"] == 0


@mock_aws
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
    assert cluster["ClusterIdentifier"] == cluster_identifier
    assert cluster["NumberOfNodes"] == 1

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    cluster = cluster_response["Clusters"][0]

    assert cluster["ClusterIdentifier"] == cluster_identifier
    assert cluster["NodeType"] == "dw.hs1.xlarge"
    assert cluster["MasterUsername"] == "username"
    assert cluster["DBName"] == "my_db"
    assert cluster["NumberOfNodes"] == 1


@mock_aws
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
    assert cluster["ClusterSubnetGroupName"] == "my_subnet_group"


@mock_aws
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
    assert cluster["ClusterSubnetGroupName"] == "my_subnet_group"


@mock_aws
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
    assert set(group_names) == {"security_group1", "security_group2"}


@mock_aws
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
    assert list(group_ids) == [security_group.id]


@mock_aws
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
    assert iam_roles_arn == iam_roles


@mock_aws
def test_create_cluster_with_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_id = "my-cluster"
    group = client.create_cluster_parameter_group(
        ParameterGroupName="my-parameter-group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my group",
    )["ClusterParameterGroup"]
    assert group["ParameterGroupName"] == "my-parameter-group"
    assert group["ParameterGroupFamily"] == "redshift-1.0"
    assert group["Description"] == "This is my group"
    assert group["Tags"] == []

    cluster = client.create_cluster(
        ClusterIdentifier=cluster_id,
        NodeType="dc1.large",
        MasterUsername="username",
        MasterUserPassword="Password1",
        ClusterType="single-node",
        ClusterParameterGroupName="my-parameter-group",
    )["Cluster"]
    assert len(cluster["ClusterParameterGroups"]) == 1
    assert cluster["ClusterParameterGroups"][0]["ParameterGroupName"] == (
        "my-parameter-group"
    )
    assert cluster["ClusterParameterGroups"][0]["ParameterApplyStatus"] == "in-sync"

    cluster_response = client.describe_clusters(ClusterIdentifier=cluster_id)
    cluster = cluster_response["Clusters"][0]
    assert len(cluster["ClusterParameterGroups"]) == 1
    assert cluster["ClusterParameterGroups"][0]["ParameterGroupName"] == (
        "my-parameter-group"
    )
    assert cluster["ClusterParameterGroups"][0]["ParameterApplyStatus"] == "in-sync"


@mock_aws
def test_describe_non_existent_cluster_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_clusters(ClusterIdentifier="not-a-cluster")
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFound"
    assert err["Message"] == "Cluster not-a-cluster not found."


@mock_aws
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
    assert cluster["EnhancedVpcRouting"] is False

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
    assert cluster["ClusterIdentifier"] == cluster_identifier
    assert cluster["NodeType"] == "ds2.8xlarge"
    assert cluster["PreferredMaintenanceWindow"] == "Tue:03:00-Tue:11:00"
    assert cluster["AutomatedSnapshotRetentionPeriod"] == 7
    assert cluster["AllowVersionUpgrade"] is False
    # This one should remain unmodified.
    assert cluster["NumberOfNodes"] == 3
    assert cluster["EnhancedVpcRouting"] is True


@mock_aws
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
    assert cluster["EnhancedVpcRouting"] is False

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
    assert cluster["ClusterIdentifier"] == cluster_identifier
    assert cluster["NodeType"] == "dw.hs1.xlarge"
    assert cluster["ClusterSecurityGroups"][0]["ClusterSecurityGroupName"] == (
        "security_group"
    )
    assert cluster["PreferredMaintenanceWindow"] == "Tue:03:00-Tue:11:00"
    assert cluster["ClusterParameterGroups"][0]["ParameterGroupName"] == (
        "my_parameter_group"
    )
    assert cluster["AutomatedSnapshotRetentionPeriod"] == 7
    assert cluster["AllowVersionUpgrade"] is False
    assert cluster["NumberOfNodes"] == 4


@mock_aws
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

    assert my_subnet["ClusterSubnetGroupName"] == "my_subnet_group"
    assert my_subnet["Description"] == "This is my subnet group"
    subnet_ids = [subnet["SubnetIdentifier"] for subnet in my_subnet["Subnets"]]
    assert set(subnet_ids) == set([subnet1.id, subnet2.id])


@mock_aws
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


@mock_aws
def test_create_invalid_cluster_subnet_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_cluster_subnet_group(
            ClusterSubnetGroupName="my_subnet",
            Description="This is my subnet group",
            SubnetIds=["subnet-1234"],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidSubnet"
    assert re.match(r"Subnet \[[a-z0-9-']+\] not found.", err["Message"])


@mock_aws
def test_describe_non_existent_subnet_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_cluster_subnet_groups(ClusterSubnetGroupName="my_subnet")
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterSubnetGroupNotFound"
    assert err["Message"] == "Subnet group my_subnet not found."


@mock_aws
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
    assert len(subnets) == 1

    client.delete_cluster_subnet_group(ClusterSubnetGroupName="my_subnet_group")

    subnets_response = client.describe_cluster_subnet_groups()
    subnets = subnets_response["ClusterSubnetGroups"]
    assert len(subnets) == 0

    # Delete invalid id
    with pytest.raises(ClientError):
        client.delete_cluster_subnet_group(ClusterSubnetGroupName="not-a-subnet-group")


@mock_aws
def test_create_cluster_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    group = client.create_cluster_security_group(
        ClusterSecurityGroupName="my_security_group",
        Description="This is my security group",
        Tags=[{"Key": "tag_key", "Value": "tag_value"}],
    )["ClusterSecurityGroup"]
    assert group["ClusterSecurityGroupName"] == "my_security_group"
    assert group["Description"] == "This is my security group"
    assert group["EC2SecurityGroups"] == []
    assert group["IPRanges"] == []
    assert group["Tags"] == [{"Key": "tag_key", "Value": "tag_value"}]

    groups_response = client.describe_cluster_security_groups(
        ClusterSecurityGroupName="my_security_group"
    )
    my_group = groups_response["ClusterSecurityGroups"][0]

    assert my_group["ClusterSecurityGroupName"] == "my_security_group"
    assert my_group["Description"] == "This is my security group"
    assert my_group["EC2SecurityGroups"] == []
    assert my_group["IPRanges"] == []
    assert my_group["Tags"] == [{"Key": "tag_key", "Value": "tag_value"}]


@mock_aws
def test_describe_non_existent_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_cluster_security_groups(ClusterSecurityGroupName="non-existent")
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterSecurityGroupNotFound"
    assert err["Message"] == "Security group non-existent not found."


@mock_aws
def test_delete_cluster_security_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster_security_group(
        ClusterSecurityGroupName="my_security_group",
        Description="This is my security group",
    )

    groups = client.describe_cluster_security_groups()["ClusterSecurityGroups"]
    assert len(groups) == 2  # The default group already exists

    client.delete_cluster_security_group(ClusterSecurityGroupName="my_security_group")

    groups = client.describe_cluster_security_groups()["ClusterSecurityGroups"]
    assert len(groups) == 1

    # Delete invalid id
    with pytest.raises(ClientError) as ex:
        client.delete_cluster_security_group(
            ClusterSecurityGroupName="not-a-security-group"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterSecurityGroupNotFound"
    assert err["Message"] == "Security group not-a-security-group not found."


@mock_aws
def test_create_cluster_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    group = client.create_cluster_parameter_group(
        ParameterGroupName="my-parameter-group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my group",
    )["ClusterParameterGroup"]
    assert group["ParameterGroupName"] == "my-parameter-group"
    assert group["ParameterGroupFamily"] == "redshift-1.0"
    assert group["Description"] == "This is my group"
    assert group["Tags"] == []

    groups_response = client.describe_cluster_parameter_groups(
        ParameterGroupName="my-parameter-group"
    )
    my_group = groups_response["ParameterGroups"][0]

    assert my_group["ParameterGroupName"] == "my-parameter-group"
    assert my_group["ParameterGroupFamily"] == "redshift-1.0"
    assert my_group["Description"] == "This is my group"


@mock_aws
def test_describe_non_existent_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.describe_cluster_parameter_groups(
            ParameterGroupName="not-a-parameter-group"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterParameterGroupNotFound"
    assert err["Message"] == "Parameter group not-a-parameter-group not found."


@mock_aws
def test_delete_parameter_group_boto3():
    client = boto3.client("redshift", region_name="us-east-1")
    client.create_cluster_parameter_group(
        ParameterGroupName="my-parameter-group",
        ParameterGroupFamily="redshift-1.0",
        Description="This is my group",
    )
    assert len(client.describe_cluster_parameter_groups()["ParameterGroups"]) == 2

    x = client.delete_cluster_parameter_group(ParameterGroupName="my-parameter-group")
    del x["ResponseMetadata"]
    assert x == {}

    with pytest.raises(ClientError) as ex:
        client.delete_cluster_parameter_group(ParameterGroupName="my-parameter-group")
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterParameterGroupNotFound"
    # BUG: This is what AWS returns
    # assert err["Message"] == "ParameterGroup not found: my-parameter-group"
    assert err["Message"] == "Parameter group my-parameter-group not found."

    assert len(client.describe_cluster_parameter_groups()["ParameterGroups"]) == 1


@mock_aws
def test_create_cluster_snapshot_of_non_existent_cluster():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "non-existent-cluster-id"
    with pytest.raises(ClientError) as client_err:
        client.create_cluster_snapshot(
            SnapshotIdentifier="snapshot-id", ClusterIdentifier=cluster_identifier
        )
    assert client_err.value.response["Error"]["Message"] == (
        f"Cluster {cluster_identifier} not found."
    )


@mock_aws
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

    assert cluster_response["Cluster"]["Tags"] == [
        {"Key": "tag_key", "Value": "tag_value"}
    ]
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier
    )
    assert resp_auto_snap["Snapshots"][0]["SnapshotType"] == "automated"
    # Tags from cluster are not copied over to automated snapshot
    assert resp_auto_snap["Snapshots"][0]["Tags"] == []


@mock_aws
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
    assert cluster_response["Cluster"]["NodeType"] == "ds2.xlarge"
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier
    )
    snapshot_identifier = resp_auto_snap["Snapshots"][0]["SnapshotIdentifier"]
    # Delete automated snapshot should result in error
    with pytest.raises(ClientError) as client_err:
        client.delete_cluster_snapshot(SnapshotIdentifier=snapshot_identifier)
    assert client_err.value.response["Error"]["Message"] == (
        f"Cannot delete the snapshot {snapshot_identifier} because only "
        "manual snapshots may be deleted"
    )


@mock_aws
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
    assert len(resp["Snapshots"]) == 1

    # Delete the cluster
    cluster_response = client.delete_cluster(
        ClusterIdentifier=cluster_identifier, SkipFinalClusterSnapshot=True
    )
    cluster = cluster_response["Cluster"]
    assert cluster["ClusterIdentifier"] == cluster_identifier

    # Ensure Automated snapshot is deleted
    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    assert len(resp["Snapshots"]) == 0


@mock_aws
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
    assert cluster_response["Cluster"]["NodeType"] == "ds2.xlarge"
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
    assert len(resp["Snapshots"]) == 1

    resp = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier, SnapshotType="manual"
    )
    assert len(resp["Snapshots"]) == 1

    resp = client.describe_cluster_snapshots(
        SnapshotIdentifier=snapshot_identifier, SnapshotType="manual"
    )
    assert len(resp["Snapshots"]) == 1

    resp = client.describe_cluster_snapshots(
        SnapshotIdentifier=auto_snapshot_identifier, SnapshotType="automated"
    )
    assert len(resp["Snapshots"]) == 1

    with pytest.raises(ClientError) as client_err:
        client.describe_cluster_snapshots(
            SnapshotIdentifier=snapshot_identifier, SnapshotType="automated"
        )
    assert client_err.value.response["Error"]["Message"] == (
        f"Snapshot {snapshot_identifier} not found."
    )

    with pytest.raises(ClientError) as client_err:
        client.describe_cluster_snapshots(
            SnapshotIdentifier=auto_snapshot_identifier, SnapshotType="manual"
        )
    assert client_err.value.response["Error"]["Message"] == (
        f"Snapshot {auto_snapshot_identifier} not found."
    )


@mock_aws
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
    with pytest.raises(ClientError) as client_err:
        client.restore_from_cluster_snapshot(
            ClusterIdentifier=original_cluster_identifier,
            SnapshotIdentifier=auto_snapshot_identifier,
        )
    assert client_err.value.response["Error"]["Code"] == "ClusterAlreadyExists"

    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=auto_snapshot_identifier,
        Port=1234,
    )
    assert response["Cluster"]["ClusterStatus"] == "creating"

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    assert new_cluster["NodeType"] == "ds2.xlarge"
    assert new_cluster["MasterUsername"] == "username"
    assert new_cluster["Endpoint"]["Port"] == 1234
    assert new_cluster["EnhancedVpcRouting"] is True

    # Make sure the new cluster has automated snapshot on cluster creation
    resp_auto_snap = client.describe_cluster_snapshots(
        ClusterIdentifier=new_cluster_identifier, SnapshotType="automated"
    )
    assert len(resp_auto_snap["Snapshots"]) == 1


@mock_aws
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
    assert cluster_response["Cluster"]["NodeType"] == "ds2.xlarge"

    snapshot_response = client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{"Key": "test-tag-key", "Value": "test-tag-value"}],
    )
    snapshot = snapshot_response["Snapshot"]
    assert snapshot["SnapshotIdentifier"] == snapshot_identifier
    assert snapshot["ClusterIdentifier"] == cluster_identifier
    assert snapshot["NumberOfNodes"] == 1
    assert snapshot["NodeType"] == "ds2.xlarge"
    assert snapshot["MasterUsername"] == "username"


@mock_aws
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
    assert snapshot_1["SnapshotIdentifier"] == snapshot_identifier_1
    assert snapshot_1["ClusterIdentifier"] == cluster_identifier
    assert snapshot_1["NumberOfNodes"] == 1
    assert snapshot_1["NodeType"] == "ds2.xlarge"
    assert snapshot_1["MasterUsername"] == "username"

    resp_snap_2 = client.describe_cluster_snapshots(
        SnapshotIdentifier=snapshot_identifier_2
    )
    snapshot_2 = resp_snap_2["Snapshots"][0]
    assert snapshot_2["SnapshotIdentifier"] == snapshot_identifier_2
    assert snapshot_2["ClusterIdentifier"] == cluster_identifier
    assert snapshot_2["NumberOfNodes"] == 1
    assert snapshot_2["NodeType"] == "ds2.xlarge"
    assert snapshot_2["MasterUsername"] == "username"

    resp_clust = client.describe_cluster_snapshots(
        ClusterIdentifier=cluster_identifier, SnapshotType="manual"
    )
    assert resp_clust["Snapshots"][0] == resp_snap_1["Snapshots"][0]
    assert resp_clust["Snapshots"][1] == resp_snap_2["Snapshots"][0]


@mock_aws
def test_describe_cluster_snapshots_not_found_error():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "non-existent-cluster-id"
    snapshot_identifier = "non-existent-snapshot-id"

    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    assert len(resp["Snapshots"]) == 0

    with pytest.raises(ClientError) as client_err:
        client.describe_cluster_snapshots(SnapshotIdentifier=snapshot_identifier)
    assert client_err.value.response["Error"]["Message"] == (
        f"Snapshot {snapshot_identifier} not found."
    )


@mock_aws
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
    assert len(list(snapshots)) == 2

    assert (
        client.delete_cluster_snapshot(SnapshotIdentifier=snapshot_identifier)[
            "Snapshot"
        ]["Status"]
        == "deleted"
    )

    snapshots = client.describe_cluster_snapshots()["Snapshots"]
    assert len(list(snapshots)) == 1

    # Delete invalid id
    with pytest.raises(ClientError) as client_err:
        client.delete_cluster_snapshot(SnapshotIdentifier="non-existent")
    assert client_err.value.response["Error"]["Message"] == (
        "Snapshot non-existent not found."
    )


@mock_aws
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

    with pytest.raises(ClientError) as client_err:
        client.create_cluster_snapshot(
            SnapshotIdentifier=snapshot_identifier, ClusterIdentifier=cluster_identifier
        )
    assert (
        f"{snapshot_identifier} already exists"
        in client_err.value.response["Error"]["Message"]
    )


@mock_aws
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

    with pytest.raises(ClientError) as client_err:
        client.restore_from_cluster_snapshot(
            ClusterIdentifier=original_cluster_identifier,
            SnapshotIdentifier=original_snapshot_identifier,
        )
    assert client_err.value.response["Error"]["Code"] == "ClusterAlreadyExists"

    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        Port=1234,
    )
    assert response["Cluster"]["ClusterStatus"] == "creating"

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    assert new_cluster["NodeType"] == "ds2.xlarge"
    assert new_cluster["MasterUsername"] == "username"
    assert new_cluster["Endpoint"]["Port"] == 1234
    assert new_cluster["EnhancedVpcRouting"] is True


@mock_aws
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

    with pytest.raises(ClientError) as client_err:
        client.restore_from_cluster_snapshot(
            ClusterIdentifier=original_cluster_identifier,
            SnapshotIdentifier=original_snapshot_identifier,
        )
    assert client_err.value.response["Error"]["Code"] == "ClusterAlreadyExists"

    response = client.restore_from_cluster_snapshot(
        ClusterIdentifier=new_cluster_identifier,
        SnapshotIdentifier=original_snapshot_identifier,
        NodeType="ra3.xlplus",
        NumberOfNodes=3,
    )
    assert response["Cluster"]["ClusterStatus"] == "creating"

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    assert new_cluster["NodeType"] == "ra3.xlplus"
    assert new_cluster["NumberOfNodes"] == 3
    assert new_cluster["MasterUsername"] == "username"
    assert new_cluster["EnhancedVpcRouting"] is True


@mock_aws
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
    assert response["Cluster"]["ClusterStatus"] == "creating"

    client.get_waiter("cluster_restored").wait(
        ClusterIdentifier=new_cluster_identifier,
        WaiterConfig={"Delay": 1, "MaxAttempts": 2},
    )

    response = client.describe_clusters(ClusterIdentifier=new_cluster_identifier)
    new_cluster = response["Clusters"][0]
    assert new_cluster["NodeType"] == "ds2.xlarge"
    assert new_cluster["MasterUsername"] == "username"
    assert new_cluster["EnhancedVpcRouting"] is True
    assert new_cluster["Endpoint"]["Port"] == 1234


@mock_aws
def test_create_cluster_from_non_existent_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")
    with pytest.raises(ClientError) as client_err:
        client.restore_from_cluster_snapshot(
            ClusterIdentifier="cluster-id", SnapshotIdentifier="non-existent-snapshot"
        )
    assert client_err.value.response["Error"]["Message"] == (
        "Snapshot non-existent-snapshot not found."
    )


@mock_aws
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
    assert response["Cluster"]["ClusterStatus"] == "creating"

    response = client.describe_clusters(ClusterIdentifier=cluster_identifier)
    assert response["Clusters"][0]["ClusterStatus"] == "available"


@mock_aws
def test_describe_tags_with_resource_type():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "my_cluster"
    cluster_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:{cluster_identifier}"
    )
    snapshot_identifier = "my_snapshot"
    snapshot_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:snapshot"
        f":{cluster_identifier}/{snapshot_identifier}"
    )
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
    assert len(list(tagged_resources)) == 1
    assert tagged_resources[0]["ResourceType"] == "cluster"
    assert tagged_resources[0]["ResourceName"] == cluster_arn
    tag = tagged_resources[0]["Tag"]
    assert tag["Key"] == tag_key
    assert tag["Value"] == tag_value

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{"Key": tag_key, "Value": tag_value}],
    )
    tags_response = client.describe_tags(ResourceType="snapshot")
    tagged_resources = tags_response["TaggedResources"]
    assert len(list(tagged_resources)) == 1
    assert tagged_resources[0]["ResourceType"] == "snapshot"
    assert tagged_resources[0]["ResourceName"] == snapshot_arn
    tag = tagged_resources[0]["Tag"]
    assert tag["Key"] == tag_key
    assert tag["Value"] == tag_value


@mock_aws
def test_describe_tags_cannot_specify_resource_type_and_resource_name():
    client = boto3.client("redshift", region_name="us-east-1")
    resource_name = f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:cluster-id"
    resource_type = "cluster"
    with pytest.raises(ClientError) as client_err:
        client.describe_tags(ResourceName=resource_name, ResourceType=resource_type)
    assert (
        "using either an ARN or a resource type"
        in client_err.value.response["Error"]["Message"]
    )


@mock_aws
def test_describe_tags_with_resource_name():
    client = boto3.client("redshift", region_name="us-east-1")
    cluster_identifier = "cluster-id"
    cluster_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:cluster:{cluster_identifier}"
    )
    snapshot_identifier = "snapshot-id"
    snapshot_arn = (
        f"arn:aws:redshift:us-east-1:{ACCOUNT_ID}:snapshot"
        f":{cluster_identifier}/{snapshot_identifier}"
    )
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
    assert len(list(tagged_resources)) == 1
    assert tagged_resources[0]["ResourceType"] == "cluster"
    assert tagged_resources[0]["ResourceName"] == cluster_arn
    tag = tagged_resources[0]["Tag"]
    assert tag["Key"] == tag_key
    assert tag["Value"] == tag_value

    client.create_cluster_snapshot(
        SnapshotIdentifier=snapshot_identifier,
        ClusterIdentifier=cluster_identifier,
        Tags=[{"Key": tag_key, "Value": tag_value}],
    )
    tags_response = client.describe_tags(ResourceName=snapshot_arn)
    tagged_resources = tags_response["TaggedResources"]
    assert len(list(tagged_resources)) == 1
    assert tagged_resources[0]["ResourceType"] == "snapshot"
    assert tagged_resources[0]["ResourceName"] == snapshot_arn
    tag = tagged_resources[0]["Tag"]
    assert tag["Key"] == tag_key
    assert tag["Value"] == tag_value


@mock_aws
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
    assert len(list(cluster["Tags"])) == num_tags
    response = client.describe_tags(ResourceName=cluster_arn)
    assert len(list(response["TaggedResources"])) == num_tags


@mock_aws
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
    assert len(list(cluster["Tags"])) == 1
    response = client.describe_tags(ResourceName=cluster_arn)
    assert len(list(response["TaggedResources"])) == 1


@mock_aws
def test_describe_tags_all_resource_types():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    client = boto3.client("redshift", region_name="us-east-1")
    response = client.describe_tags()
    assert len(list(response["TaggedResources"])) == 0
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
    assert len(list(tagged_resources)) == len(expected_types)
    assert set(returned_types) == set(expected_types)


@mock_aws
def test_tagged_resource_not_found_error():
    client = boto3.client("redshift", region_name="us-east-1")

    cluster_arn = "arn:aws:redshift:us-east-1::cluster:fake"
    with pytest.raises(ClientError) as client_err:
        client.describe_tags(ResourceName=cluster_arn)
    assert client_err.value.response["Error"]["Message"] == "cluster (fake) not found."

    snapshot_arn = "arn:aws:redshift:us-east-1::snapshot:cluster-id/snap-id"
    with pytest.raises(ClientError) as client_err:
        client.delete_tags(ResourceName=snapshot_arn, TagKeys=["test"])
    assert (
        client_err.value.response["Error"]["Message"] == "snapshot (snap-id) not found."
    )

    with pytest.raises(ClientError) as client_err:
        client.describe_tags(ResourceType="cluster")
    assert client_err.value.response["Error"]["Message"] == (
        "resource of type 'cluster' not found."
    )

    with pytest.raises(ClientError) as client_err:
        client.describe_tags(ResourceName="bad:arn")
    assert (
        "Tagging is not supported for this type of resource"
        in client_err.value.response["Error"]["Message"]
    )


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        "SnapshotCopyGrantName is required for Snapshot Copy on KMS encrypted clusters."
    ) in ex.value.response["Error"]["Message"]
    with pytest.raises(ClientError) as ex:
        client.enable_snapshot_copy(
            ClusterIdentifier="test",
            DestinationRegion="us-east-1",
            RetentionPeriod=3,
            SnapshotCopyGrantName="invalid-us-east-1-to-us-east-1",
        )
    assert ex.value.response["Error"]["Code"] == "UnknownSnapshotCopyRegionFault"
    assert "Invalid region us-east-1" in ex.value.response["Error"]["Message"]
    client.enable_snapshot_copy(
        ClusterIdentifier="test",
        DestinationRegion="us-west-2",
        RetentionPeriod=3,
        SnapshotCopyGrantName="copy-us-east-1-to-us-west-2",
    )
    response = client.describe_clusters(ClusterIdentifier="test")
    cluster_snapshot_copy_status = response["Clusters"][0]["ClusterSnapshotCopyStatus"]
    assert cluster_snapshot_copy_status["RetentionPeriod"] == 3
    assert cluster_snapshot_copy_status["DestinationRegion"] == "us-west-2"
    assert cluster_snapshot_copy_status["SnapshotCopyGrantName"] == (
        "copy-us-east-1-to-us-west-2"
    )


@mock_aws
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
    assert cluster_snapshot_copy_status["RetentionPeriod"] == 7
    assert cluster_snapshot_copy_status["DestinationRegion"] == "us-west-2"


@mock_aws
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
    assert "ClusterSnapshotCopyStatus" not in response["Clusters"][0]


@mock_aws
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
    assert cluster_snapshot_copy_status["RetentionPeriod"] == 5


@mock_aws
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
    with pytest.raises(ClientError) as client_err:
        client.create_cluster(**kwargs)
    assert client_err.value.response["Error"]["Code"] == "ClusterAlreadyExists"


@mock_aws
def test_delete_cluster_with_final_snapshot():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_cluster(ClusterIdentifier="non-existent")
    assert ex.value.response["Error"]["Code"] == "ClusterNotFound"
    assert re.match(r"Cluster .+ not found.", ex.value.response["Error"]["Message"])

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
    assert ex.value.response["Error"]["Code"] == "InvalidParameterCombination"
    assert (
        "FinalClusterSnapshotIdentifier is required unless SkipFinalClusterSnapshot is specified."
    ) in ex.value.response["Error"]["Message"]

    snapshot_identifier = "my_snapshot"
    client.delete_cluster(
        ClusterIdentifier=cluster_identifier,
        SkipFinalClusterSnapshot=False,
        FinalClusterSnapshotIdentifier=snapshot_identifier,
    )

    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    assert len(resp["Snapshots"]) == 1
    assert resp["Snapshots"][0]["SnapshotIdentifier"] == snapshot_identifier
    assert resp["Snapshots"][0]["SnapshotType"] == "manual"

    with pytest.raises(ClientError) as ex:
        client.describe_clusters(ClusterIdentifier=cluster_identifier)
    assert ex.value.response["Error"]["Code"] == "ClusterNotFound"
    assert re.match(r"Cluster .+ not found.", ex.value.response["Error"]["Message"])


@mock_aws
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
    assert cluster["ClusterIdentifier"] == cluster_identifier
    assert cluster["NodeType"] == "ds2.xlarge"
    # Bug: This is what AWS returns
    # assert cluster["ClusterStatus"] == "deleting"
    assert cluster["MasterUsername"] == "user"
    assert cluster["DBName"] == "test"
    endpoint = cluster["Endpoint"]
    assert re.match(
        f"{cluster_identifier}.[a-z0-9]+.us-east-1.redshift.amazonaws.com",
        endpoint["Address"],
    )
    assert endpoint["Port"] == 5439
    assert cluster["AutomatedSnapshotRetentionPeriod"] == 1
    assert len(cluster["ClusterParameterGroups"]) == 1
    param_group = cluster["ClusterParameterGroups"][0]
    assert param_group == {
        "ParameterGroupName": "default.redshift-1.0",
        "ParameterApplyStatus": "in-sync",
    }
    assert cluster["AvailabilityZone"] == "us-east-1a"
    assert cluster["ClusterVersion"] == "1.0"
    assert cluster["AllowVersionUpgrade"] is True
    assert cluster["NumberOfNodes"] == 1
    assert cluster["Encrypted"] is False
    assert cluster["EnhancedVpcRouting"] is False

    resp = client.describe_cluster_snapshots(ClusterIdentifier=cluster_identifier)
    assert len(resp["Snapshots"]) == 0

    with pytest.raises(ClientError) as ex:
        client.describe_clusters(ClusterIdentifier=cluster_identifier)
    assert ex.value.response["Error"]["Code"] == "ClusterNotFound"
    assert re.match(r"Cluster .+ not found.", ex.value.response["Error"]["Message"])


@mock_aws
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
    assert resp["Cluster"]["NumberOfNodes"] == 1

    client.modify_cluster(
        ClusterIdentifier="test", ClusterType="multi-node", NumberOfNodes=2
    )
    resp = client.describe_clusters(ClusterIdentifier="test")
    assert resp["Clusters"][0]["NumberOfNodes"] == 2

    client.modify_cluster(ClusterIdentifier="test", ClusterType="single-node")
    resp = client.describe_clusters(ClusterIdentifier="test")
    assert resp["Clusters"][0]["NumberOfNodes"] == 1

    with pytest.raises(ClientError) as ex:
        client.modify_cluster(
            ClusterIdentifier="test", ClusterType="multi-node", NumberOfNodes=1
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterCombination"
    assert (
        "Number of nodes for cluster type multi-node must be greater than or equal to 2"
    ) in ex.value.response["Error"]["Message"]

    with pytest.raises(ClientError) as ex:
        client.modify_cluster(
            ClusterIdentifier="test",
            ClusterType="invalid-cluster-type",
            NumberOfNodes=1,
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert "Invalid cluster type" in ex.value.response["Error"]["Message"]


@mock_aws
def test_get_cluster_credentials_non_existent_cluster_and_user():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.get_cluster_credentials(
            ClusterIdentifier="non-existent", DbUser="some_user"
        )
    assert ex.value.response["Error"]["Code"] == "ClusterNotFound"
    assert re.match(r"Cluster .+ not found.", ex.value.response["Error"]["Message"])


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        "Token duration must be between 900 and 3600 seconds"
        in ex.value.response["Error"]["Message"]
    )

    with pytest.raises(ClientError) as ex:
        client.get_cluster_credentials(
            ClusterIdentifier=cluster_identifier, DbUser=db_user, DurationSeconds=3601
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"
    assert (
        "Token duration must be between 900 and 3600 seconds"
        in ex.value.response["Error"]["Message"]
    )


@mock_aws
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
        (datetime.datetime.now(tzutc()) + datetime.timedelta(0, 900)).timetuple()
    )
    db_user = "some_user"
    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser=db_user
    )
    assert response["DbUser"] == f"IAM:{db_user}"
    assert time.mktime((response["Expiration"]).timetuple()) == pytest.approx(
        expected_expiration
    )
    assert len(response["DbPassword"]) == 32

    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser=db_user, AutoCreate=True
    )
    assert response["DbUser"] == f"IAMA:{db_user}"

    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser="some_other_user", AutoCreate=False
    )
    assert response["DbUser"] == "IAM:some_other_user"

    expected_expiration = time.mktime(
        (datetime.datetime.now(tzutc()) + datetime.timedelta(0, 3000)).timetuple()
    )
    response = client.get_cluster_credentials(
        ClusterIdentifier=cluster_identifier, DbUser=db_user, DurationSeconds=3000
    )
    assert time.mktime(response["Expiration"].timetuple()) == pytest.approx(
        expected_expiration
    )


@mock_aws
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
    assert cluster["ClusterIdentifier"] == "test"

    response = client.pause_cluster(ClusterIdentifier="test")
    cluster = response["Cluster"]
    assert cluster["ClusterIdentifier"] == "test"
    # Verify this call returns all properties
    assert cluster["NodeType"] == "ds2.xlarge"
    assert cluster["ClusterStatus"] == "paused"
    assert cluster["ClusterVersion"] == "1.0"
    assert cluster["AllowVersionUpgrade"] is True
    assert cluster["Endpoint"]["Port"] == 5439


@mock_aws
def test_pause_unknown_cluster():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.pause_cluster(ClusterIdentifier="test")
    err = exc.value.response["Error"]
    assert err["Code"] == "ClusterNotFound"
    assert err["Message"] == "Cluster test not found."


@mock_aws
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
    assert cluster["ClusterIdentifier"] == "test"
    # Verify this call returns all properties
    assert cluster["NodeType"] == "ds2.xlarge"
    assert cluster["ClusterStatus"] == "available"
    assert cluster["ClusterVersion"] == "1.0"
    assert cluster["AllowVersionUpgrade"] is True
    assert cluster["Endpoint"]["Port"] == 5439


@mock_aws
def test_resume_unknown_cluster():
    client = boto3.client("redshift", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.resume_cluster(ClusterIdentifier="test")
    err = exc.value.response["Error"]
    assert err["Code"] == "ClusterNotFound"
    assert err["Message"] == "Cluster test not found."
