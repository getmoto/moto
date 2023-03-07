import boto3
from moto import mock_neptune


@mock_neptune
def test_add_tags_to_cluster():
    conn = boto3.client("neptune", region_name="us-west-2")
    resp = conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        Engine="neptune",
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    cluster_arn = resp["DBCluster"]["DBClusterArn"]

    conn.add_tags_to_resource(
        ResourceName=cluster_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    tags.should.equal([{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}])

    conn.remove_tags_from_resource(ResourceName=cluster_arn, TagKeys=["k1"])

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    tags.should.equal([{"Key": "k2", "Value": "v2"}])
