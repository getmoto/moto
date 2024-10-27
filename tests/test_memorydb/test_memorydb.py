"""Unit tests for memorydb-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def create_subnet_group(client, region_name):
    """Return valid Subnet group."""
    ec2 = boto3.resource("ec2", region_name=region_name)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    subnet_group = client.create_subnet_group(
        SubnetGroupName="my_subnet_group",
        Description="This is my subnet group",
        SubnetIds=[subnet1.id, subnet2.id],
    )
    return subnet_group


@mock_aws
def test_create_cluster():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    resp = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    cluster = resp["Cluster"]
    assert "Name" in cluster
    assert "Status" in cluster
    assert "NumberOfShards" in cluster


@mock_aws
def test_create_duplicate_cluster_fails():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    client.create_cluster(
        ClusterName="foo-bar",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    with pytest.raises(ClientError) as ex:
        client.create_cluster(
            ClusterName="foo-bar", NodeType="db.t4g.small", ACLName="open-access"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterAlreadyExistsFault"


@mock_aws
def test_create_subnet_group():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    subnet_group = create_subnet_group(client, "ap-southeast-1")
    sg = subnet_group["SubnetGroup"]
    assert "Name" in sg
    assert "Description" in sg
    assert "VpcId" in sg
    assert "Subnets" in sg
    assert "ARN" in sg


@mock_aws
def test_create_cluster_with_subnet_group():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    subnet_group = create_subnet_group(client, "ap-southeast-1")
    resp = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        SubnetGroupName=subnet_group["SubnetGroup"]["Name"],
        ACLName="open-access",
    )
    subnet_group = resp["Cluster"]["SubnetGroupName"] == "my_subnet_group"


@mock_aws
def test_create_duplicate_subnet_group_fails():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    create_subnet_group(client, "ap-southeast-1")
    with pytest.raises(ClientError) as ex:
        create_subnet_group(client, "ap-southeast-1")
    err = ex.value.response["Error"]
    assert err["Code"] == "SubnetGroupAlreadyExistsFault"


@mock_aws
def test_create_invalid_subnet_group_fails():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as ex:
        client.create_subnet_group(SubnetGroupName="foo-bar", SubnetIds=["foo", "bar"])
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidSubnetError"


@mock_aws
def test_create_snapshot():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    subnet_group = create_subnet_group(client, "ap-southeast-1")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        Description="Test memorydb cluster",
        NodeType="db.t4g.small",
        SubnetGroupName=subnet_group["SubnetGroup"]["Name"],
        ACLName="open-access",
    )
    resp = client.create_snapshot(
        ClusterName=cluster["Cluster"]["Name"],
        SnapshotName="my-snapshot-1",
        KmsKeyId=f"arn:aws:kms:ap-southeast-1:{ACCOUNT_ID}:key/51d81fab-b138-4bd2-8a09-07fd6d37224d",
        Tags=[
            {"Key": "foo", "Value": "bar"},
        ],
    )
    snapshot = resp["Snapshot"]
    assert "Name" in snapshot
    assert "Status" in snapshot
    assert "Source" in snapshot
    assert "KmsKeyId" in snapshot
    assert "ARN" in snapshot
    assert "ClusterConfiguration" in snapshot
    assert "DataTiering" in snapshot


@mock_aws
def test_create_snapshot_with_non_existing_cluster_fails():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as ex:
        client.create_snapshot(ClusterName="foobar", SnapshotName="my-snapshot-1")
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_create_duplicate_snapshot_fails():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    client.create_snapshot(
        ClusterName=cluster["Cluster"]["Name"], SnapshotName="my-snapshot-1"
    )
    with pytest.raises(ClientError) as ex:
        client.create_snapshot(
            ClusterName=cluster["Cluster"]["Name"], SnapshotName="my-snapshot-1"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "SnapshotAlreadyExistsFault"


@mock_aws
def test_describe_clusters():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
    resp = client.describe_clusters()
    assert "Clusters" in resp
    assert len(resp["Clusters"]) == 2
    assert "Shards" not in resp["Clusters"][0]


@mock_aws
def test_describe_clusters_with_shard_details():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
    resp = client.describe_clusters(
        ClusterName="test-memory-db-1",
        ShowShardDetails=True,
    )
    assert resp["Clusters"][0]["Name"] == "test-memory-db-1"
    assert len(resp["Clusters"]) == 1
    assert "Shards" in resp["Clusters"][0]


@mock_aws
def test_describe_clusters_with_cluster_name():
    client = boto3.client("memorydb", region_name="ap-southeast-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
    resp = client.describe_clusters(
        ClusterName="test-memory-db-1",
    )
    assert resp["Clusters"][0]["Name"] == "test-memory-db-1"
    assert len(resp["Clusters"]) == 1


@mock_aws
def test_describe_snapshots():
    client = boto3.client("memorydb", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
        client.create_snapshot(
            ClusterName=f"test-memory-db-{i}", SnapshotName=f"my-snapshot-{i}"
        )
    resp = client.describe_snapshots()
    assert "Snapshots" in resp
    assert len(resp["Snapshots"]) == 2
    assert resp["Snapshots"][0]["Name"] == "my-snapshot-1"


@mock_aws
def test_describe_snapshots_with_cluster_name():
    client = boto3.client("memorydb", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
        client.create_snapshot(
            ClusterName=f"test-memory-db-{i}", SnapshotName=f"my-snapshot-{i}"
        )
    resp = client.describe_snapshots(ClusterName="test-memory-db-2")
    assert len(resp["Snapshots"]) == 1
    assert resp["Snapshots"][0]["ClusterConfiguration"]["Name"] == "test-memory-db-2"
    assert "Shards" not in resp["Snapshots"][0]["ClusterConfiguration"]


@mock_aws
def test_describe_snapshots_with_shard_details():
    client = boto3.client("memorydb", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
        client.create_snapshot(
            ClusterName=f"test-memory-db-{i}", SnapshotName=f"my-snapshot-{i}"
        )
    resp = client.describe_snapshots(ClusterName="test-memory-db-2", ShowDetail=True)
    assert len(resp["Snapshots"]) == 1
    assert resp["Snapshots"][0]["ClusterConfiguration"]["Name"] == "test-memory-db-2"
    assert "Shards" in resp["Snapshots"][0]["ClusterConfiguration"]


@mock_aws
def test_describe_snapshots_with_snapshot_name():
    client = boto3.client("memorydb", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_cluster(
            ClusterName=f"test-memory-db-{i}",
            NodeType="db.t4g.small",
            ACLName="open-access",
        )
        client.create_snapshot(
            ClusterName=f"test-memory-db-{i}", SnapshotName=f"my-snapshot-{i}"
        )
    resp = client.describe_snapshots(
        SnapshotName="my-snapshot-1",
    )
    assert len(resp["Snapshots"]) == 1
    assert resp["Snapshots"][0]["Name"] == "my-snapshot-1"


@mock_aws
def test_describe_snapshots_with_snapshot_and_cluster():
    client = boto3.client("memorydb", region_name="eu-west-1")

    client.create_cluster(
        ClusterName="test-memory-db", NodeType="db.t4g.small", ACLName="open-access"
    )
    for i in range(1, 3):
        client.create_snapshot(
            ClusterName="test-memory-db", SnapshotName=f"my-snapshot-{i}"
        )
    resp = client.describe_snapshots(
        ClusterName="test-memory-db",
        SnapshotName="my-snapshot-1",
    )
    assert len(resp["Snapshots"]) == 1
    assert resp["Snapshots"][0]["Name"] == "my-snapshot-1"


@mock_aws
def test_describe_snapshots_with_invalid_cluster():
    client = boto3.client("memorydb", region_name="eu-west-1")

    resp = client.describe_snapshots(
        ClusterName="foobar",
    )
    assert len(resp["Snapshots"]) == 0


@mock_aws
def test_describe_snapshots_invalid_snapshot_fails():
    client = boto3.client("memorydb", region_name="eu-west-1")

    with pytest.raises(ClientError) as ex:
        client.describe_snapshots(SnapshotName="foobar")
    err = ex.value.response["Error"]
    assert err["Code"] == "SnapshotNotFoundFault"


@mock_aws
def test_describe_snapshots_with_cluster_and_invalid_snapshot_fails():
    client = boto3.client("memorydb", region_name="eu-west-1")

    client.create_cluster(
        ClusterName="test-memory-db", NodeType="db.t4g.small", ACLName="open-access"
    )
    client.create_snapshot(ClusterName="test-memory-db", SnapshotName="my-snapshot")

    with pytest.raises(ClientError) as ex:
        client.describe_snapshots(ClusterName="test-memory-db", SnapshotName="foobar")
    err = ex.value.response["Error"]
    assert err["Code"] == "SnapshotNotFoundFault"


@mock_aws
def test_describe_subnet_groups():
    client = boto3.client("memorydb", region_name="eu-west-1")
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    for i in range(1, 3):
        client.create_subnet_group(
            SubnetGroupName=f"my_subnet_group-{i}",
            Description="This is my subnet group",
            SubnetIds=[subnet1.id, subnet2.id],
        )
    resp = client.describe_subnet_groups()
    assert "SubnetGroups" in resp
    assert len(resp["SubnetGroups"]) == 3  # Including default subnet group


@mock_aws
def test_describe_subnet_groups_with_subnet_group_name():
    client = boto3.client("memorydb", region_name="eu-west-1")
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/24")
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    for i in range(1, 3):
        client.create_subnet_group(
            SubnetGroupName=f"my_subnet_group-{i}",
            Description="This is my subnet group",
            SubnetIds=[subnet1.id, subnet2.id],
        )
    resp = client.describe_subnet_groups(SubnetGroupName="my_subnet_group-1")
    assert len(resp["SubnetGroups"]) == 1
    assert resp["SubnetGroups"][0]["Name"] == "my_subnet_group-1"


@mock_aws
def test_describe_subnet_groups_invalid_subnetgroupname_fails():
    client = boto3.client("memorydb", region_name="eu-west-1")
    with pytest.raises(ClientError) as ex:
        client.describe_subnet_groups(SubnetGroupName="foobar")
    err = ex.value.response["Error"]
    assert err["Code"] == "SubnetGroupNotFoundFault"


@mock_aws
def test_list_tags():
    client = boto3.client("memorydb", region_name="us-east-2")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
        Tags=[
            {"Key": "foo", "Value": "bar"},
        ],
    )
    resp = client.list_tags(ResourceArn=cluster["Cluster"]["ARN"])
    assert "TagList" in resp
    assert len(resp["TagList"]) == 1
    assert "foo" in resp["TagList"][0]["Key"]
    assert "bar" in resp["TagList"][0]["Value"]


@mock_aws
def test_list_tags_invalid_cluster_fails():
    client = boto3.client("memorydb", region_name="us-east-2")
    with pytest.raises(ClientError) as ex:
        client.list_tags(
            ResourceArn=f"arn:aws:memorydb:us-east-1:{ACCOUNT_ID}:cluster/foobar",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_tag_resource():
    client = boto3.client("memorydb", region_name="us-east-2")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
        Tags=[
            {"Key": "key1", "Value": "value1"},
        ],
    )
    resp = client.tag_resource(
        ResourceArn=cluster["Cluster"]["ARN"],
        Tags=[
            {"Key": "key2", "Value": "value2"},
        ],
    )
    assert "TagList" in resp
    assert len(resp["TagList"]) == 2
    assert "key2" in resp["TagList"][1]["Key"]
    assert "value2" in resp["TagList"][1]["Value"]


@mock_aws
def test_tag_resource_invalid_cluster_fails():
    client = boto3.client("memorydb", region_name="us-east-2")
    with pytest.raises(ClientError) as ex:
        client.tag_resource(
            ResourceArn=f"arn:aws:memorydb:us-east-1:{ACCOUNT_ID}:cluster/foobar",
            Tags=[{"Key": "key2", "Value": "value2"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_untag_resource():
    client = boto3.client("memorydb", region_name="us-east-2")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
        Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}],
    )
    resp = client.untag_resource(
        ResourceArn=cluster["Cluster"]["ARN"],
        TagKeys=[
            "key1",
        ],
    )
    assert "TagList" in resp
    assert len(resp["TagList"]) == 1
    assert "key2" in resp["TagList"][0]["Key"]
    assert "value2" in resp["TagList"][0]["Value"]


@mock_aws
def test_untag_resource_invalid_cluster_fails():
    client = boto3.client("memorydb", region_name="us-east-2")
    with pytest.raises(ClientError) as ex:
        client.untag_resource(
            ResourceArn=f"arn:aws:memorydb:us-east-1:{ACCOUNT_ID}:cluster/foobar",
            TagKeys=["key1"],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_untag_resource_invalid_keys_fails():
    client = boto3.client("memorydb", region_name="us-east-2")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
        Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}],
    )
    with pytest.raises(ClientError) as ex:
        client.untag_resource(
            ResourceArn=cluster["Cluster"]["ARN"], TagKeys=["key3", "key4"]
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "TagNotFoundFault"


@mock_aws
def test_update_cluster_replica_count():
    client = boto3.client("memorydb", region_name="eu-west-1")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    desc_before_update = client.describe_clusters(ShowShardDetails=True)
    assert desc_before_update["Clusters"][0]["Shards"][0]["NumberOfNodes"] == 2
    client.update_cluster(
        ClusterName=cluster["Cluster"]["Name"],
        Description="Good cluster",
        MaintenanceWindow="thu:23:00-thu:01:30",
        ReplicaConfiguration={"ReplicaCount": 2},
    )
    desc_after_update = client.describe_clusters(ShowShardDetails=True)
    cluster_after_update = desc_after_update["Clusters"][0]
    assert cluster_after_update["Description"] == "Good cluster"
    assert cluster_after_update["MaintenanceWindow"] == "thu:23:00-thu:01:30"
    assert cluster_after_update["Shards"][0]["NumberOfNodes"] == 3


@mock_aws
def test_update_cluster_shards():
    client = boto3.client("memorydb", region_name="eu-west-1")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    desc_before_update = client.describe_clusters(ShowShardDetails=True)
    assert desc_before_update["Clusters"][0]["NumberOfShards"] == 1
    client.update_cluster(
        ClusterName=cluster["Cluster"]["Name"],
        ShardConfiguration={"ShardCount": 2},
    )
    desc_after_update = client.describe_clusters(ShowShardDetails=True)
    assert desc_after_update["Clusters"][0]["NumberOfShards"] == 2


@mock_aws
def test_update_invalid_cluster_fails():
    client = boto3.client("memorydb", region_name="eu-west-1")
    with pytest.raises(ClientError) as ex:
        client.update_cluster(
            ClusterName="foobar",
            Description="Good cluster",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_delete_cluster():
    client = boto3.client("memorydb", region_name="eu-west-1")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    desc_resp_before = client.describe_clusters()
    assert len(desc_resp_before["Clusters"]) == 1
    resp = client.delete_cluster(
        ClusterName=cluster["Cluster"]["Name"],
    )
    assert resp["Cluster"]["Name"] == cluster["Cluster"]["Name"]
    desc_resp_after = client.describe_clusters()
    assert len(desc_resp_after["Clusters"]) == 0


@mock_aws
def test_delete_cluster_with_snapshot():
    client = boto3.client("memorydb", region_name="eu-west-1")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    desc_resp_before = client.describe_snapshots()
    assert len(desc_resp_before["Snapshots"]) == 0
    resp = client.delete_cluster(
        ClusterName=cluster["Cluster"]["Name"],
        FinalSnapshotName="test-memory-db-snapshot",
    )
    assert resp["Cluster"]["Name"] == cluster["Cluster"]["Name"]
    desc_resp_after = client.describe_snapshots()
    assert len(desc_resp_after["Snapshots"]) == 1
    assert desc_resp_after["Snapshots"][0]["Name"] == "test-memory-db-snapshot"


@mock_aws
def test_delete_invalid_cluster_fails():
    client = boto3.client("memorydb", region_name="eu-west-1")
    with pytest.raises(ClientError) as ex:
        client.delete_cluster(
            ClusterName="foobar",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_delete_snapshot():
    client = boto3.client("memorydb", region_name="us-east-2")
    cluster = client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        ACLName="open-access",
    )
    snapshot = client.create_snapshot(
        ClusterName=cluster["Cluster"]["Name"],
        SnapshotName="my-snapshot-1",
    )
    desc_resp_before = client.describe_snapshots()
    assert len(desc_resp_before["Snapshots"]) == 1
    resp = client.delete_snapshot(SnapshotName=snapshot["Snapshot"]["Name"])
    assert "Snapshot" in resp
    desc_resp_after = client.describe_snapshots()
    assert len(desc_resp_after["Snapshots"]) == 0


@mock_aws
def test_delete_invalid_snapshot_fails():
    client = boto3.client("memorydb", region_name="us-east-2")
    with pytest.raises(ClientError) as ex:
        client.delete_snapshot(SnapshotName="foobar")
    err = ex.value.response["Error"]
    assert err["Code"] == "SnapshotNotFoundFault"


@mock_aws
def test_delete_subnet_group():
    client = boto3.client("memorydb", region_name="us-east-2")
    subnet_group = create_subnet_group(client, "us-east-2")
    sg = subnet_group["SubnetGroup"]
    response = client.describe_subnet_groups()
    assert len(response["SubnetGroups"]) == 2
    resp = client.delete_subnet_group(SubnetGroupName=sg["Name"])
    assert "SubnetGroup" in resp
    response = client.describe_subnet_groups()
    assert len(response["SubnetGroups"]) == 1  # default subnet group


@mock_aws
def test_delete_subnet_group_default_fails():
    client = boto3.client("memorydb", region_name="us-east-2")

    with pytest.raises(ClientError) as ex:
        client.delete_subnet_group(SubnetGroupName="default")
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"


@mock_aws
def test_delete_subnet_group_in_use_fails():
    client = boto3.client("memorydb", region_name="us-east-2")
    subnet_group = create_subnet_group(client, "us-east-2")
    client.create_cluster(
        ClusterName="test-memory-db",
        NodeType="db.t4g.small",
        SubnetGroupName=subnet_group["SubnetGroup"]["Name"],
        ACLName="open-access",
    )
    with pytest.raises(ClientError) as ex:
        client.delete_subnet_group(SubnetGroupName=subnet_group["SubnetGroup"]["Name"])
    err = ex.value.response["Error"]
    assert err["Code"] == "SubnetGroupInUseFault"
