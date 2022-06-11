"""Unit tests for dax-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_dax
from moto.core import ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_dax
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
        cluster["ClusterName"].should.equal("daxcluster")
        cluster["ClusterArn"].should.equal(
            f"arn:aws:dax:us-east-2:{ACCOUNT_ID}:cache/daxcluster"
        )
        cluster["TotalNodes"].should.equal(3)
        cluster["ActiveNodes"].should.equal(0)
        cluster["NodeType"].should.equal("dax.t3.small")
        cluster["Status"].should.equal("creating")
        cluster["ClusterDiscoveryEndpoint"].should.equal({"Port": 8111})
        cluster["PreferredMaintenanceWindow"].should.equal("thu:23:30-fri:00:30")
        cluster["SubnetGroup"].should.equal("default")
        cluster["SecurityGroups"].should.have.length_of(1)
        cluster["IamRoleArn"].should.equal(iam_role_arn)
        cluster.should.have.key("ParameterGroup")
        cluster["ParameterGroup"].should.have.key("ParameterGroupName").equals(
            "default.dax1.0"
        )
        cluster["SSEDescription"].should.equal({"Status": "DISABLED"})
        cluster.should.have.key("ClusterEndpointEncryptionType").equals("NONE")


@mock_dax
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
        cluster["ClusterName"].should.equal("daxcluster")
        cluster["Description"].should.equal("my cluster")


@mock_dax
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
        cluster["ClusterName"].should.equal("daxcluster")
        cluster["SSEDescription"].should.equal({"Status": "ENABLED"})
        cluster["ClusterEndpointEncryptionType"].should.equal("TLS")


@mock_dax
def test_create_cluster_invalid_arn():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName="1invalid",
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn="n/a",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal("ARNs must start with 'arn:': n/a")


@mock_dax
def test_create_cluster_invalid_arn_no_partition():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName="1invalid",
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn="arn:sth",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal("Second colon partition not found: arn:sth")


@mock_dax
def test_create_cluster_invalid_arn_no_vendor():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName="1invalid",
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn="arn:sth:aws",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal("Third colon vendor not found: arn:sth:aws")


@mock_dax
def test_create_cluster_invalid_arn_no_region():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName="1invalid",
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn="arn:sth:aws:else",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal(
        "Fourth colon (region/namespace delimiter) not found: arn:sth:aws:else"
    )


@mock_dax
def test_create_cluster_invalid_arn_no_namespace():
    client = boto3.client("dax", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_cluster(
            ClusterName="1invalid",
            NodeType="dax.t3.small",
            ReplicationFactor=3,
            IamRoleArn="arn:sth:aws:else:eu-west-1",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal(
        "Fifth colon (namespace/relative-id delimiter) not found: arn:sth:aws:else:eu-west-1"
    )


@mock_dax
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
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal(
        "Cluster ID specified is not a valid identifier. Identifiers must begin with a letter; must contain only ASCII letters, digits, and hyphens; and must not end with a hyphen or contain two consecutive hyphens."
    )


@mock_dax
@pytest.mark.parametrize(
    "name", ["1invalid", "iИvalid", "in_valid", "invalid-", "in--valid"]
)
def test_describe_clusters_invalid_name(name):
    client = boto3.client("dax", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.describe_clusters(ClusterNames=[name])
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValueException")
    err["Message"].should.equal(
        "Cluster ID specified is not a valid identifier. Identifiers must begin with a letter; must contain only ASCII letters, digits, and hyphens; and must not end with a hyphen or contain two consecutive hyphens."
    )


@mock_dax
def test_delete_cluster_unknown():
    client = boto3.client("dax", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_cluster(ClusterName="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equals("ClusterNotFoundFault")
    err["Message"].should.equal("Cluster not found.")


@mock_dax
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
        cluster["Status"].should.equal("deleting")
        cluster["TotalNodes"].should.equal(2)
        cluster["ActiveNodes"].should.equal(0)
        cluster.shouldnt.have.key("Nodes")

    with pytest.raises(ClientError) as exc:
        client.describe_clusters(ClusterNames=["daxcluster"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFoundFault")


@mock_dax
def test_describe_cluster_unknown():
    client = boto3.client("dax", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.describe_clusters(ClusterNames=["unknown"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFoundFault")
    err["Message"].should.equal("Cluster unknown not found.")


@mock_dax
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

    clusters = client.describe_clusters()["Clusters"]
    clusters.should.have.length_of(50)


@mock_dax
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
    resp["Clusters"].should.have.length_of(10)
    resp.should.have.key("NextToken")

    resp = client.describe_clusters(MaxResults=10, NextToken=resp["NextToken"])
    resp["Clusters"].should.have.length_of(10)
    resp.should.have.key("NextToken")

    resp = client.describe_clusters(NextToken=resp["NextToken"])
    resp["Clusters"].should.have.length_of(30)
    resp.shouldnt.have.key("NextToken")


@mock_dax
def test_describe_clusters_returns_nodes_after_some_time():
    client = boto3.client("dax", region_name="us-east-2")
    client.create_cluster(
        ClusterName="daxcluster",
        NodeType="dax.t3.small",
        ReplicationFactor=3,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
    )["Cluster"]

    for _ in range(0, 3):
        # Cluster takes a while to load...
        cluster = client.describe_clusters(ClusterNames=["daxcluster"])["Clusters"][0]
        cluster["Status"].should.equal("creating")
        cluster.shouldnt.have.key("Nodes")

    # Finished loading by now
    cluster = client.describe_clusters(ClusterNames=["daxcluster"])["Clusters"][0]

    cluster["ClusterName"].should.equal("daxcluster")
    cluster["ClusterArn"].should.equal(
        f"arn:aws:dax:us-east-2:{ACCOUNT_ID}:cache/daxcluster"
    )
    cluster["TotalNodes"].should.equal(3)
    cluster["ActiveNodes"].should.equal(0)
    cluster["NodeType"].should.equal("dax.t3.small")
    cluster["Status"].should.equal("available")

    # Address Info is only available when the cluster is ready
    cluster.should.have.key("ClusterDiscoveryEndpoint")
    endpoint = cluster["ClusterDiscoveryEndpoint"]
    endpoint.should.have.key("Address")
    address = endpoint["Address"]
    cluster_id = address.split(".")[1]
    address.should.equal(
        f"daxcluster.{cluster_id}.dax-clusters.us-east-2.amazonaws.com"
    )
    endpoint.should.have.key("Port").equal(8111)
    endpoint.should.have.key("URL").equal(f"dax://{address}")

    # Nodes are only shown when the cluster is ready
    cluster.should.have.key("Nodes").length_of(3)
    for idx, a in enumerate(["a", "b", "c"]):
        node = cluster["Nodes"][idx]
        node.should.have.key("NodeId").equals(f"daxcluster-{a}")
        node.should.have.key("Endpoint")
        node_address = (
            f"daxcluster-{a}.{cluster_id}.nodes.dax-clusters.us-east-2.amazonaws.com"
        )
        node["Endpoint"].should.have.key("Address").equals(node_address)
        node["Endpoint"].should.have.key("Port").equals(8111)
        node.should.contain("AvailabilityZone")
        node.should.have.key("NodeStatus").equals("available")
        node.should.have.key("ParameterGroupStatus").equals("in-sync")

    cluster["PreferredMaintenanceWindow"].should.equal("thu:23:30-fri:00:30")
    cluster["SubnetGroup"].should.equal("default")
    cluster["SecurityGroups"].should.have.length_of(1)
    cluster.should.have.key("ParameterGroup")
    cluster["ParameterGroup"].should.have.key("ParameterGroupName").equals(
        "default.dax1.0"
    )
    cluster["SSEDescription"].should.equal({"Status": "DISABLED"})
    cluster.should.have.key("ClusterEndpointEncryptionType").equals("NONE")


@mock_dax
def test_list_tags_unknown():
    client = boto3.client("dax", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.list_tags(ResourceName="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFoundFault")


@mock_dax
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

        resp.shouldnt.have.key("NextToken")
        resp.should.have.key("Tags").equals(
            [
                {"Key": "tag1", "Value": "value1"},
                {"Key": "tag2", "Value": "value2"},
                {"Key": "tag3", "Value": "value3"},
            ]
        )


@mock_dax
def test_increase_replication_factor_unknown():
    client = boto3.client("dax", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.increase_replication_factor(
            ClusterName="unknown", NewReplicationFactor=2
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFoundFault")


@mock_dax
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
    cluster["TotalNodes"].should.equal(2)

    new_cluster = client.increase_replication_factor(
        ClusterName=name, NewReplicationFactor=5
    )["Cluster"]
    new_cluster["TotalNodes"].should.equal(5)

    new_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    new_cluster["TotalNodes"].should.equal(5)

    # Progress cluster until it's available
    client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    client.describe_clusters(ClusterNames=[name])["Clusters"][0]

    cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    node_ids = set([n["NodeId"] for n in cluster["Nodes"]])
    node_ids.should.equal(
        {f"{name}-a", f"{name}-b", f"{name}-c", f"{name}-d", f"{name}-e"}
    )


@mock_dax
def test_decrease_replication_factor_unknown():
    client = boto3.client("dax", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.decrease_replication_factor(
            ClusterName="unknown", NewReplicationFactor=2
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("ClusterNotFoundFault")


@mock_dax
def test_decrease_replication_factor():
    client = boto3.client("dax", region_name="eu-west-1")

    name = "daxcluster"
    client.create_cluster(
        ClusterName=name,
        NodeType="dax.t3.small",
        ReplicationFactor=5,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
        Tags=[
            {"Key": "tag1", "Value": "value1"},
            {"Key": "tag2", "Value": "value2"},
            {"Key": "tag3", "Value": "value3"},
        ],
    )

    new_cluster = client.decrease_replication_factor(
        ClusterName=name, NewReplicationFactor=3
    )["Cluster"]
    new_cluster["TotalNodes"].should.equal(3)

    new_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    new_cluster["TotalNodes"].should.equal(3)

    # Progress cluster until it's available
    client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    client.describe_clusters(ClusterNames=[name])["Clusters"][0]

    cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    node_ids = set([n["NodeId"] for n in cluster["Nodes"]])
    node_ids.should.equal({f"{name}-a", f"{name}-b", f"{name}-c"})


@mock_dax
def test_decrease_replication_factor_specific_nodeids():
    client = boto3.client("dax", region_name="ap-southeast-1")

    name = "daxcluster"
    client.create_cluster(
        ClusterName=name,
        NodeType="dax.t3.small",
        ReplicationFactor=5,
        IamRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/aws-service-role/dax.amazonaws.com/AWSServiceRoleForDAX",
        Tags=[
            {"Key": "tag1", "Value": "value1"},
            {"Key": "tag2", "Value": "value2"},
            {"Key": "tag3", "Value": "value3"},
        ],
    )

    new_cluster = client.decrease_replication_factor(
        ClusterName=name,
        NewReplicationFactor=3,
        NodeIdsToRemove=["daxcluster-b", "daxcluster-c"],
    )["Cluster"]
    new_cluster["TotalNodes"].should.equal(3)

    new_cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    new_cluster["TotalNodes"].should.equal(3)

    # Progress cluster until it's available
    client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    client.describe_clusters(ClusterNames=[name])["Clusters"][0]

    cluster = client.describe_clusters(ClusterNames=[name])["Clusters"][0]
    node_ids = set([n["NodeId"] for n in cluster["Nodes"]])
    node_ids.should.equal({f"{name}-a", f"{name}-d", f"{name}-e"})
