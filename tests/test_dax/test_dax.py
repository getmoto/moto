"""Unit tests for dax-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_cluster_minimal():
    client = boto3.client("dax", region_name="us-east-2")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    created_cluster = client.create_cluster(
        ClusterName="daxcluster",
        NodeType="dax.t3.small",
        ReplicationFactor=3,
        IamRoleArn=iam_role_arn,
    )["Cluster"]
    described_cluster = client.describe_clusters(ClusterNames=["daxcluster"])[
        "Clusters"
    ][0]

    for cluster in [created_cluster, described_cluster]:
        assert cluster["ClusterName"] == "daxcluster"
        assert (
            cluster["ClusterArn"]
            == f"arn:aws:dax:us-east-2:{ACCOUNT_ID}:cache/daxcluster"
        )
        assert cluster["TotalNodes"] == 3
        assert cluster["ActiveNodes"] == 0
        assert cluster["NodeType"] == "dax.t3.small"
        assert cluster["Status"] == "creating"
        assert cluster["ClusterDiscoveryEndpoint"] == {"Port": 8111}
        assert cluster["PreferredMaintenanceWindow"] == "thu:23:30-fri:00:30"
        assert cluster["SubnetGroup"] == "default"
        assert len(cluster["SecurityGroups"]) == 1
        assert cluster["IamRoleArn"] == iam_role_arn
        assert cluster["ParameterGroup"]["ParameterGroupName"] == "default.dax1.0"
        assert cluster["SSEDescription"] == {"Status": "DISABLED"}
        assert cluster["ClusterEndpointEncryptionType"] == "NONE"


@mock_aws
def test_create_cluster_description():
    client = boto3.client("dax", region_name="us-east-2")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    created_cluster = client.create_cluster(
        ClusterName="daxcluster",
        Description="my cluster",
        NodeType="dax.t3.small",
        ReplicationFactor=3,
        IamRoleArn=iam_role_arn,
    )["Cluster"]
    described_cluster = client.describe_clusters(ClusterNames=["daxcluster"])[
        "Clusters"
    ][0]

    for cluster in [created_cluster, described_cluster]:
        assert cluster["ClusterName"] == "daxcluster"
        assert cluster["Description"] == "my cluster"


@mock_aws
def test_create_cluster_with_sse_enabled():
    client = boto3.client("dax", region_name="us-east-2")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    created_cluster = client.create_cluster(
        ClusterName="daxcluster",
        NodeType="dax.t3.small",
        ReplicationFactor=3,
        IamRoleArn=iam_role_arn,
        SSESpecification={"Enabled": True},
        ClusterEndpointEncryptionType="TLS",
    )["Cluster"]
    described_cluster = client.describe_clusters(ClusterNames=["daxcluster"])[
        "Clusters"
    ][0]

    for cluster in [created_cluster, described_cluster]:
        assert cluster["ClusterName"] == "daxcluster"
        assert cluster["SSEDescription"] == {"Status": "ENABLED"}
        assert cluster["ClusterEndpointEncryptionType"] == "TLS"


@mock_aws
@pytest.mark.parametrize(
    "iam_role,expected",
    (
        ("n/a", "ARNs must start with 'arn:': n/a"),
        ("arn:sth", "Second colon partition not found: arn:sth"),
        ("arn:sth:aws", "Third colon vendor not found: arn:sth:aws"),
        (
            "arn:sth:aws:else",
            "Fourth colon (region/namespace delimiter) not found: arn:sth:aws:else",
        ),
        (
            "arn:sth:aws:else:eu-west-1",
            "Fifth colon (namespace/relative-id delimiter) not found: arn:sth:aws:else:eu-west-1",
        ),
    ),
)
def test_create_cluster_invalid_arn(iam_role: str, expected: str):
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName="1invalid",
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn=iam_role,
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "InvalidParameterValueException"
    assert err["Message"] == expected


@mock_aws
@pytest.mark.parametrize(
    "name", ["1invalid", "iИvalid", "in_valid", "invalid-", "in--valid"]
)
def test_create_cluster_invalid_name(name):
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName=name,
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn="arn:aws:iam::486285699788:role/apigatewayrole",
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "InvalidParameterValueException"
    assert err["Message"] == (
        "Cluster ID specified is not a valid identifier. Identifiers must begin with a letter; must contain only ASCII letters, digits, and hyphens; and must not end with a hyphen or contain two consecutive hyphens."
    )


@mock_aws
@pytest.mark.parametrize(
    "name", ["1invalid", "iИvalid", "in_valid", "invalid-", "in--valid"]
)
def test_describe_clusters_invalid_name(name):
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_clusters(ClusterNames=[name])
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert (
        err["Message"]
        == "Cluster ID specified is not a valid identifier. Identifiers must begin with a letter; must contain only ASCII letters, digits, and hyphens; and must not end with a hyphen or contain two consecutive hyphens."
    )


@mock_aws
def test_delete_cluster_unknown():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.delete_cluster(ClusterName="unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "ClusterNotFoundFault"
    assert err["Message"] == "Cluster not found."


@mock_aws
def test_delete_cluster():
    client = boto3.client("dax", region_name="eu-west-1")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    client.create_cluster(
        ClusterName="daxcluster",
        NodeType="dax.t3.small",
        ReplicationFactor=2,
        IamRoleArn=iam_role_arn,
    )
    client.delete_cluster(ClusterName="daxcluster")

    for _ in range(0, 3):
        # Cluster takes a while to delete...
        cluster = client.describe_clusters(ClusterNames=["daxcluster"])["Clusters"][0]

        assert cluster["Status"] == "deleting"
        assert cluster["TotalNodes"] == 2
        assert cluster["ActiveNodes"] == 0
        assert "Nodes" not in cluster

    with pytest.raises(ClientError) as exc:
        client.describe_clusters(ClusterNames=["daxcluster"])
    err = exc.value.response["Error"]

    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_describe_cluster_unknown():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_clusters(ClusterNames=["unknown"])
    err = exc.value.response["Error"]

    assert err["Code"] == "ClusterNotFoundFault"
    assert err["Message"] == "Cluster unknown not found."


@mock_aws
def test_describe_clusters_returns_all():
    client = boto3.client("dax", region_name="us-east-1")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    for i in range(0, 50):
        client.create_cluster(
            ClusterName=f"daxcluster{i}",
            NodeType="dax.t3.small",
            ReplicationFactor=1,
            IamRoleArn=iam_role_arn,
        )

    assert len(client.describe_clusters()["Clusters"]) == 50


@mock_aws
def test_describe_clusters_paginates():
    client = boto3.client("dax", region_name="us-east-1")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    for i in range(0, 50):
        client.create_cluster(
            ClusterName=f"daxcluster{i}",
            NodeType="dax.t3.small",
            ReplicationFactor=1,
            IamRoleArn=iam_role_arn,
        )

    resp = client.describe_clusters(MaxResults=10)
    assert len(resp["Clusters"]) == 10
    assert "NextToken" in resp

    resp = client.describe_clusters(MaxResults=10, NextToken=resp["NextToken"])
    assert len(resp["Clusters"]) == 10
    assert "NextToken" in resp

    resp = client.describe_clusters(NextToken=resp["NextToken"])
    assert len(resp["Clusters"]) == 30
    assert "NextToken" not in resp


@mock_aws
def test_describe_clusters_returns_nodes_after_some_time():
    client = boto3.client("dax", region_name="us-east-2")
    iam_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX"
    client.create_cluster(
        ClusterName="daxcluster",
        NodeType="dax.t3.small",
        ReplicationFactor=3,
        IamRoleArn=iam_role_arn,
    )

    for _ in range(0, 3):
        # Cluster takes a while to load...
        cluster = client.describe_clusters(ClusterNames=["daxcluster"])["Clusters"][0]
        assert cluster["Status"] == "creating"
        assert "Nodes" not in cluster

    # Finished loading by now
    cluster = client.describe_clusters(ClusterNames=["daxcluster"])["Clusters"][0]

    assert cluster["TotalNodes"] == 3
    assert cluster["ActiveNodes"] == 0
    assert cluster["Status"] == "available"

    # Address Info is only available when the cluster is ready
    endpoint = cluster["ClusterDiscoveryEndpoint"]
    address = endpoint["Address"]
    cluster_id = address.split(".")[1]

    assert address == f"daxcluster.{cluster_id}.dax-clusters.us-east-2.amazonaws.com"
    assert endpoint["Port"] == 8111
    assert endpoint["URL"] == f"dax://{address}"

    # Nodes are only shown when the cluster is ready
    assert len(cluster["Nodes"]) == 3

    for idx, a in enumerate(["a", "b", "c"]):
        node = cluster["Nodes"][idx]
        expected_node_address = (
            f"daxcluster-{a}.{cluster_id}.nodes.dax-clusters.us-east-2.amazonaws.com"
        )

        assert node["NodeId"] == f"daxcluster-{a}"
        assert node["Endpoint"]["Address"] == expected_node_address
        assert node["Endpoint"]["Port"] == 8111
        assert "AvailabilityZone" in node
        assert node["NodeStatus"] == "available"
        assert node["ParameterGroupStatus"] == "in-sync"


@mock_aws
def test_list_tags_unknown():
    client = boto3.client("dax", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.list_tags(ResourceName="unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_list_tags():
    client = boto3.client("dax", region_name="ap-southeast-1")
    cluster = client.create_cluster(
        ClusterName="daxcluster",
        NodeType="dax.t3.small",
        ReplicationFactor=3,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
        Tags=[
            {"Key": "tag1", "Value": "value1"},
            {"Key": "tag2", "Value": "value2"},
            {"Key": "tag3", "Value": "value3"},
        ],
    )["Cluster"]

    for name in ["daxcluster", cluster["ClusterArn"]]:
        resp = client.list_tags(ResourceName=name)

        assert "NextToken" not in resp
        assert resp["Tags"] == (
            [
                {"Key": "tag1", "Value": "value1"},
                {"Key": "tag2", "Value": "value2"},
                {"Key": "tag3", "Value": "value3"},
            ]
        )


@mock_aws
def test_increase_replication_factor_unknown():
    client = boto3.client("dax", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.increase_replication_factor(
            ClusterName="unknown", NewReplicationFactor=2
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_increase_replication_factor():
    client = boto3.client("dax", region_name="ap-southeast-1")
    name = "daxcluster"
    cluster = client.create_cluster(
        ClusterName=name,
        NodeType="dax.t3.small",
        ReplicationFactor=2,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
        Tags=[
            {"Key": "tag1", "Value": "value1"},
            {"Key": "tag2", "Value": "value2"},
            {"Key": "tag3", "Value": "value3"},
        ],
    )["Cluster"]

    assert cluster["TotalNodes"] == 2

    adjusted_cluster = client.increase_replication_factor(
        ClusterName=name, NewReplicationFactor=5
    )["Cluster"]
    described_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]

    assert adjusted_cluster["TotalNodes"] == 5
    assert described_cluster["TotalNodes"] == 5

    # Progress cluster until it's available
    for _ in range(0, 3):
        client.describe_clusters(ClusterNames=[name])

    described_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    node_ids = set([node["NodeId"] for node in described_cluster["Nodes"]])

    assert node_ids == (
        {f"{name}-a", f"{name}-b", f"{name}-c", f"{name}-d", f"{name}-e"}
    )


@mock_aws
def test_decrease_replication_factor_unknown():
    client = boto3.client("dax", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.decrease_replication_factor(
            ClusterName="unknown", NewReplicationFactor=2
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "ClusterNotFoundFault"


@mock_aws
def test_decrease_replication_factor():
    client = boto3.client("dax", region_name="eu-west-1")
    name = "daxcluster"
    client.create_cluster(
        ClusterName=name,
        NodeType="dax.t3.small",
        ReplicationFactor=5,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
    )

    adjusted_cluster = client.decrease_replication_factor(
        ClusterName=name, NewReplicationFactor=3
    )["Cluster"]
    described_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]

    assert adjusted_cluster["TotalNodes"] == 3
    assert described_cluster["TotalNodes"] == 3

    # Progress cluster until it's available
    for _ in range(0, 3):
        client.describe_clusters(ClusterNames=[name])

    described_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    node_ids = set([node["NodeId"] for node in described_cluster["Nodes"]])

    assert node_ids == ({f"{name}-a", f"{name}-b", f"{name}-c"})


@mock_aws
def test_decrease_replication_factor_specific_nodeids():
    client = boto3.client("dax", region_name="ap-southeast-1")
    name = "daxcluster"
    client.create_cluster(
        ClusterName=name,
        NodeType="dax.t3.small",
        ReplicationFactor=5,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
    )

    adjusted_cluster = client.decrease_replication_factor(
        ClusterName=name,
        NewReplicationFactor=3,
        NodeIdsToRemove=["daxcluster-b", "daxcluster-c"],
    )["Cluster"]
    described_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]

    assert adjusted_cluster["TotalNodes"] == 3
    assert described_cluster["TotalNodes"] == 3

    # Progress cluster until it's available
    for _ in range(0, 3):
        client.describe_clusters(ClusterNames=[name])

    described_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    node_ids = set([node["NodeId"] for node in described_cluster["Nodes"]])

    assert node_ids == ({f"{name}-a", f"{name}-d", f"{name}-e"})
