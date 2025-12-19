"""Unit tests for cloudhsmv2-supported APIs."""

import json
from datetime import datetime

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_list_tags():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    resource_id = "cluster-1234"
    client.tag_resource(
        ResourceId=resource_id,
        TagList=[
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Project", "Value": "Security"},
        ],
    )

    response = client.list_tags(ResourceId=resource_id)
    assert len(response["TagList"]) == 2
    assert {"Key": "Environment", "Value": "Production"} in response["TagList"]
    assert {"Key": "Project", "Value": "Security"} in response["TagList"]
    assert "NextToken" not in response


@mock_aws
def test_tag_resource():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")
    resource_id = "cluster-1234"

    response = client.tag_resource(
        ResourceId=resource_id,
        TagList=[
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Project", "Value": "Security"},
        ],
    )

    tags = client.list_tags(ResourceId=resource_id)["TagList"]
    assert len(tags) == 2
    assert {"Key": "Environment", "Value": "Production"} in tags
    assert {"Key": "Project", "Value": "Security"} in tags

    response = client.tag_resource(
        ResourceId=resource_id,
        TagList=[{"Key": "Environment", "Value": "Development"}],
    )

    assert "ResponseMetadata" in response

    tags = client.list_tags(ResourceId=resource_id)["TagList"]
    assert len(tags) == 2
    assert {"Key": "Environment", "Value": "Development"} in tags
    assert {"Key": "Project", "Value": "Security"} in tags


@mock_aws
def test_list_tags_empty_resource():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    response = client.list_tags(ResourceId="non-existent-resource")
    assert response["TagList"] == []
    assert "NextToken" not in response


@mock_aws
def test_untag_resource():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")
    resource_id = "cluster-1234"

    client.tag_resource(
        ResourceId=resource_id,
        TagList=[
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Project", "Value": "Security"},
            {"Key": "Team", "Value": "DevOps"},
        ],
    )

    initial_tags = client.list_tags(ResourceId=resource_id)["TagList"]
    assert len(initial_tags) == 3

    response = client.untag_resource(
        ResourceId=resource_id, TagKeyList=["Environment", "Team"]
    )
    assert "ResponseMetadata" in response

    remaining_tags = client.list_tags(ResourceId=resource_id)["TagList"]
    assert len(remaining_tags) == 1
    assert {"Key": "Project", "Value": "Security"} in remaining_tags


@mock_aws
def test_create_cluster():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    response = client.create_cluster(
        BackupRetentionPolicy={"Type": "DAYS", "Value": "7"},
        HsmType="hsm1.medium",
        SubnetIds=["subnet-12345678"],
        TagList=[{"Key": "Environment", "Value": "Production"}],
    )

    cluster = response["Cluster"]
    assert cluster["BackupPolicy"] == "DEFAULT"
    assert cluster["BackupRetentionPolicy"] == {"Type": "DAYS", "Value": "7"}
    assert "ClusterId" in cluster
    assert isinstance(cluster["CreateTimestamp"], datetime)
    assert cluster["HsmType"] == "hsm1.medium"
    assert cluster["State"] == "ACTIVE"
    assert cluster["SubnetMapping"] == {"us-east-1": "subnet-12345678"}
    assert cluster["TagList"] == [{"Key": "Environment", "Value": "Production"}]
    assert "VpcId" in cluster

    clusters = client.describe_clusters()["Clusters"]
    assert len(clusters) == 1
    assert clusters[0]["ClusterId"] == cluster["ClusterId"]


@mock_aws
def test_delete_cluster():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    response = client.create_cluster(
        HsmType="hsm1.medium",
        SubnetIds=["subnet-12345678"],
        NetworkType="IPV4",
        Mode="FIPS",
    )
    cluster_id = response["Cluster"]["ClusterId"]

    delete_response = client.delete_cluster(ClusterId=cluster_id)

    deleted_cluster = delete_response["Cluster"]
    assert deleted_cluster["ClusterId"] == cluster_id
    assert deleted_cluster["State"] == "DELETED"
    assert deleted_cluster["StateMessage"] == "Cluster deleted"

    clusters = client.describe_clusters()["Clusters"]
    assert len(clusters) == 0


@mock_aws
def test_describe_clusters_no_clusters():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")
    response = client.describe_clusters()

    assert response["Clusters"] == []
    assert "NextToken" not in response


@mock_aws
def test_describe_clusters_with_filters():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    cluster1 = client.create_cluster(
        HsmType="hsm1.medium",
        SubnetIds=["subnet-12345678"],
        NetworkType="IPV4",
        Mode="FIPS",
    )

    client.create_cluster(
        HsmType="hsm1.medium",
        SubnetIds=["subnet-87654321"],
        NetworkType="IPV4",
        Mode="FIPS",
    )

    response = client.describe_clusters(
        Filters={"clusterIds": [cluster1["Cluster"]["ClusterId"]]}
    )
    assert len(response["Clusters"]) == 1
    assert response["Clusters"][0]["ClusterId"] == cluster1["Cluster"]["ClusterId"]

    # Test filtering by state
    response = client.describe_clusters(Filters={"states": ["ACTIVE"]})
    assert len(response["Clusters"]) == 2


@mock_aws
def test_describe_clusters_pagination():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    for i in range(3):
        client.create_cluster(
            HsmType="hsm1.medium",
            SubnetIds=[f"subnet-{i}"],
            NetworkType="IPV4",
            Mode="FIPS",
        )

    response = client.describe_clusters(MaxResults=2)
    assert len(response["Clusters"]) == 2
    assert "NextToken" in response

    # Get remaining clusters using NextToken
    response2 = client.describe_clusters(MaxResults=2, NextToken=response["NextToken"])
    assert len(response2["Clusters"]) == 1
    assert "NextToken" not in response2


@mock_aws
def test_get_resource_policy():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    client.create_cluster(HsmType="hsm1.medium", SubnetIds=["subnet-12345678"])

    backup_response = client.describe_backups()
    backup_arn = backup_response["Backups"][0]["BackupArn"]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EnableSharing",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": ["cloudhsmv2:DescribeBackups"],
                "Resource": backup_arn,
            }
        ],
    }

    client.put_resource_policy(ResourceArn=backup_arn, Policy=json.dumps(policy))
    response = client.get_resource_policy(ResourceArn=backup_arn)

    assert "Policy" in response
    assert json.loads(response["Policy"]) == policy


@mock_aws
def test_describe_backups():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    cluster = client.create_cluster(
        HsmType="hsm1.medium",
        SubnetIds=["subnet-12345678"],
    )
    cluster_id = cluster["Cluster"]["ClusterId"]

    response = client.describe_backups()
    assert "Backups" in response
    assert len(response["Backups"]) == 1

    backup = response["Backups"][0]
    assert backup["ClusterId"] == cluster_id
    assert backup["HsmType"] == "hsm1.medium"
    assert backup["BackupState"] == "READY"

    filtered_response = client.describe_backups(Filters={"clusterIds": [cluster_id]})
    assert len(filtered_response["Backups"]) == 1
    assert filtered_response["Backups"][0]["ClusterId"] == cluster_id


@mock_aws
def test_put_resource_policy():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    client.create_cluster(HsmType="hsm1.medium", SubnetIds=["subnet-12345678"])

    backup_response = client.describe_backups()
    backup_arn = backup_response["Backups"][0]["BackupArn"]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EnableSharing",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": ["cloudhsmv2:DescribeBackups"],
                "Resource": backup_arn,
            }
        ],
    }

    response = client.put_resource_policy(
        ResourceArn=backup_arn, Policy=json.dumps(policy)
    )

    assert "ResourceArn" in response
    assert "Policy" in response
    assert response["ResourceArn"] == backup_arn
    assert json.loads(response["Policy"]) == policy


@mock_aws
def test_describe_backups_pagination():
    client = boto3.client("cloudhsmv2", region_name="us-east-1")

    # Create a cluster which will automatically create a backup
    for i in range(3):
        client.create_cluster(
            HsmType="hsm1.medium",
            SubnetIds=[f"subnet-{i}"],
            NetworkType="IPV4",
            Mode="FIPS",
        )

    assert len(client.describe_backups()["Backups"]) == 3

    # Test pagination with MaxResults
    response = client.describe_backups(MaxResults=2)
    assert len(response["Backups"]) == 2
    assert "NextToken" in response

    # Get remaining backups using NextToken
    response2 = client.describe_backups(MaxResults=2, NextToken=response["NextToken"])
    assert len(response2["Backups"]) == 1
    assert "NextToken" not in response2
