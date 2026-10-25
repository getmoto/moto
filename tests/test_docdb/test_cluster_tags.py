import boto3

from moto import mock_aws


@mock_aws
def test_add_tags_to_cluster():
    conn = boto3.client("docdb", region_name="us-west-2")
    resp = conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    cluster_arn = resp["DBCluster"]["DBClusterArn"]

    conn.add_tags_to_resource(
        ResourceName=cluster_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    conn.remove_tags_from_resource(ResourceName=cluster_arn, TagKeys=["k1"])

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_aws
def test_add_tags_to_instance():
    conn = boto3.client("docdb", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    resp = conn.create_db_instance(
        DBInstanceIdentifier="instance-id",
        DBClusterIdentifier="db-primary-1",
        Engine="docdb",
        DBInstanceClass="db.r5.large",
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    instance_arn = resp["DBInstance"]["DBInstanceArn"]

    conn.add_tags_to_resource(
        ResourceName=instance_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = conn.list_tags_for_resource(ResourceName=instance_arn)["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]
