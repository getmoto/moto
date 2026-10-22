import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_db_subnet_group_lifecycle():
    ec2 = boto3.client("ec2", region_name="us-west-2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = ec2.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24", AvailabilityZone="us-west-2a"
    )["Subnet"]
    subnet2 = ec2.create_subnet(
        VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24", AvailabilityZone="us-west-2b"
    )["Subnet"]

    client = boto3.client("docdb", region_name="us-west-2")
    group = client.create_db_subnet_group(
        DBSubnetGroupName="docdb-subnets",
        DBSubnetGroupDescription="DocDB subnets",
        SubnetIds=[subnet1["SubnetId"], subnet2["SubnetId"]],
        Tags=[{"Key": "k1", "Value": "v1"}],
    )["DBSubnetGroup"]
    assert group["DBSubnetGroupName"] == "docdb-subnets"
    assert group["DBSubnetGroupDescription"] == "DocDB subnets"
    assert group["VpcId"] == vpc["VpcId"]
    assert len(group["Subnets"]) == 2

    groups = client.describe_db_subnet_groups(DBSubnetGroupName="docdb-subnets")[
        "DBSubnetGroups"
    ]
    assert len(groups) == 1

    cluster = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        DBSubnetGroupName="docdb-subnets",
    )["DBCluster"]
    assert cluster["DBSubnetGroup"] == "docdb-subnets"

    modified = client.modify_db_subnet_group(
        DBSubnetGroupName="docdb-subnets",
        DBSubnetGroupDescription="updated",
        SubnetIds=[subnet1["SubnetId"]],
    )["DBSubnetGroup"]
    assert modified["DBSubnetGroupDescription"] == "updated"
    assert len(modified["Subnets"]) == 1

    client.delete_db_cluster(DBClusterIdentifier="cluster-id")
    client.delete_db_subnet_group(DBSubnetGroupName="docdb-subnets")
    with pytest.raises(ClientError) as exc:
        client.describe_db_subnet_groups(DBSubnetGroupName="docdb-subnets")
    err = exc.value.response["Error"]
    assert err["Code"] == "DBSubnetGroupNotFoundFault"
