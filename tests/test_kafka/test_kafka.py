"""Unit tests for kafka-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


FAKE_TAGS = {"TestKey": "TestValue", "TestKey2": "TestValue2"}


@mock_aws
def test_create_cluster_v2():
    client = boto3.client("kafka", region_name="ap-southeast-1")
    cluster_name = "TestServerlessCluster"

    response = client.create_cluster_v2(
        ClusterName=cluster_name,
        Serverless={
            "VpcConfigs": [
                {
                    "SubnetIds": ["subnet-0123456789abcdef0"],
                    "SecurityGroupIds": ["sg-0123456789abcdef0"],
                }
            ]
        },
        Tags=FAKE_TAGS,
    )

    assert response["ClusterArn"].startswith("arn:aws:kafka")
    assert response["ClusterName"] == cluster_name
    assert response["State"] == "CREATING"

    clusters = client.list_clusters_v2()
    assert len(clusters["ClusterInfoList"]) == 1
    assert clusters["ClusterInfoList"][0]["ClusterName"] == cluster_name
    assert clusters["ClusterInfoList"][0]["ClusterType"] == "SERVERLESS"

    resp = client.describe_cluster_v2(ClusterArn=response["ClusterArn"])
    cluster_info = resp["ClusterInfo"]

    assert cluster_info["ClusterName"] == cluster_name
    assert cluster_info["State"] == "CREATING"
    assert cluster_info["ClusterType"] == "SERVERLESS"
    assert cluster_info["Serverless"]["VpcConfigs"][0]["SubnetIds"] == [
        "subnet-0123456789abcdef0"
    ]
    assert cluster_info["Serverless"]["VpcConfigs"][0]["SecurityGroupIds"] == [
        "sg-0123456789abcdef0"
    ]
    assert cluster_info["Tags"] == FAKE_TAGS


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("kafka", region_name="us-east-2")
    create_resp = client.create_cluster(
        ClusterName="TestCluster",
        BrokerNodeGroupInfo={
            "InstanceType": "kafka.m5.large",
            "ClientSubnets": ["subnet-0123456789abcdef0"],
            "SecurityGroups": ["sg-0123456789abcdef0"],
        },
        KafkaVersion="2.8.1",
        NumberOfBrokerNodes=3,
        Tags=FAKE_TAGS,
    )

    TempTags = {"TestKey3": "TestValue3"}

    client.tag_resource(
        ResourceArn=create_resp["ClusterArn"],
        Tags=TempTags,
    )

    tags = client.list_tags_for_resource(ResourceArn=create_resp["ClusterArn"])
    assert tags["Tags"] == {**FAKE_TAGS, **TempTags}

    client.untag_resource(
        ResourceArn=create_resp["ClusterArn"],
        TagKeys=["TestKey3"],
    )

    tags = client.list_tags_for_resource(ResourceArn=create_resp["ClusterArn"])

    assert tags["Tags"] == FAKE_TAGS


@mock_aws
def test_create_cluster():
    client = boto3.client("kafka", region_name="eu-west-1")
    cluster_name = "TestCluster"
    response = client.create_cluster(
        ClusterName=cluster_name,
        BrokerNodeGroupInfo={
            "InstanceType": "kafka.m5.large",
            "ClientSubnets": ["subnet-0123456789abcdef0"],
            "SecurityGroups": ["sg-0123456789abcdef0"],
        },
        KafkaVersion="2.8.1",
        NumberOfBrokerNodes=3,
        Tags=FAKE_TAGS,
    )

    assert response["ClusterArn"].startswith("arn:aws:kafka")
    assert response["ClusterName"] == cluster_name
    assert response["State"] == "CREATING"

    clusters = client.list_clusters()
    assert len(clusters["ClusterInfoList"]) == 1
    assert clusters["ClusterInfoList"][0]["ClusterName"] == cluster_name

    resp = client.describe_cluster(ClusterArn=response["ClusterArn"])
    assert resp["ClusterInfo"]["ClusterName"] == cluster_name
    assert resp["ClusterInfo"]["State"] == "CREATING"
    assert resp["ClusterInfo"]["CurrentBrokerSoftwareInfo"]["KafkaVersion"] == "2.8.1"
    assert resp["ClusterInfo"]["NumberOfBrokerNodes"] == 3
    assert (
        resp["ClusterInfo"]["BrokerNodeGroupInfo"]["InstanceType"] == "kafka.m5.large"
    )
    assert resp["ClusterInfo"]["BrokerNodeGroupInfo"]["ClientSubnets"] == [
        "subnet-0123456789abcdef0"
    ]
    assert resp["ClusterInfo"]["BrokerNodeGroupInfo"]["SecurityGroups"] == [
        "sg-0123456789abcdef0"
    ]
    assert resp["ClusterInfo"]["Tags"] == FAKE_TAGS


@mock_aws
def test_delete_cluster():
    client = boto3.client("kafka", region_name="us-east-2")
    create_resp = client.create_cluster(
        ClusterName="TestCluster",
        BrokerNodeGroupInfo={
            "InstanceType": "kafka.m5.large",
            "ClientSubnets": ["subnet-0123456789abcdef0"],
            "SecurityGroups": ["sg-0123456789abcdef0"],
        },
        KafkaVersion="2.8.1",
        NumberOfBrokerNodes=3,
        Tags=FAKE_TAGS,
    )

    client.delete_cluster(ClusterArn=create_resp["ClusterArn"])
    clusters = client.list_clusters()
    assert len(clusters["ClusterInfoList"]) == 0
