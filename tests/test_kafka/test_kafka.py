"""Unit tests for kafka-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


FAKE_TAGS = {"TestKey": "TestValue", "TestKey2": "TestValue2"}


@mock_aws
def test_create_cluster_v2():
    client = boto3.client("kafka", region_name="ap-southeast-1")
    s_cluster_name = "TestServerlessCluster"
    p_cluster_name = "TestProvisionedCluster"

    s_response = client.create_cluster_v2(
        ClusterName=s_cluster_name,
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

    p_response = client.create_cluster_v2(
        ClusterName=p_cluster_name,
        Provisioned={
            "BrokerNodeGroupInfo": {
                "InstanceType": "kafka.m5.large",
                "ClientSubnets": ["subnet-0123456789abcdef0"],
                "SecurityGroups": ["sg-0123456789abcdef0"],
            },
            "KafkaVersion": "2.8.1",
            "NumberOfBrokerNodes": 3,
        },
        Tags=FAKE_TAGS,
    )

    assert s_response["ClusterArn"].startswith("arn:aws:kafka")
    assert s_response["ClusterName"] == s_cluster_name
    assert s_response["State"] == "CREATING"

    assert p_response["ClusterArn"].startswith("arn:aws:kafka")
    assert p_response["ClusterName"] == p_cluster_name
    assert p_response["State"] == "CREATING"

    clusters = client.list_clusters_v2()
    assert len(clusters["ClusterInfoList"]) == 2
    assert clusters["ClusterInfoList"][0]["ClusterName"] == s_cluster_name
    assert clusters["ClusterInfoList"][0]["ClusterType"] == "SERVERLESS"
    assert clusters["ClusterInfoList"][1]["ClusterName"] == p_cluster_name
    assert clusters["ClusterInfoList"][1]["ClusterType"] == "PROVISIONED"

    s_resp = client.describe_cluster_v2(ClusterArn=s_response["ClusterArn"])
    s_cluster_info = s_resp["ClusterInfo"]
    p_resp = client.describe_cluster_v2(ClusterArn=p_response["ClusterArn"])
    p_cluster_info = p_resp["ClusterInfo"]

    assert s_cluster_info["ClusterName"] == s_cluster_name
    assert s_cluster_info["State"] == "CREATING"
    assert s_cluster_info["ClusterType"] == "SERVERLESS"
    assert s_cluster_info["Serverless"]["VpcConfigs"][0]["SubnetIds"] == [
        "subnet-0123456789abcdef0"
    ]
    assert s_cluster_info["Serverless"]["VpcConfigs"][0]["SecurityGroupIds"] == [
        "sg-0123456789abcdef0"
    ]
    assert s_cluster_info["Tags"] == FAKE_TAGS

    assert p_cluster_info["ClusterName"] == p_cluster_name
    assert p_cluster_info["State"] == "CREATING"
    assert p_cluster_info["ClusterType"] == "PROVISIONED"
    assert (
        p_cluster_info["Provisioned"]["BrokerNodeGroupInfo"]["InstanceType"]
        == "kafka.m5.large"
    )


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


@mock_aws
def test_list_clusters_v2():
    client = boto3.client("kafka", region_name="ap-southeast-1")
    s_cluster_name = "TestServerlessCluster"
    p_cluster_name = "TestProvisionedCluster"

    client.create_cluster_v2(
        ClusterName=s_cluster_name,
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

    client.create_cluster_v2(
        ClusterName=p_cluster_name,
        Provisioned={
            "BrokerNodeGroupInfo": {
                "InstanceType": "kafka.m5.large",
                "ClientSubnets": ["subnet-0123456789abcdef0"],
                "SecurityGroups": ["sg-0123456789abcdef0"],
            },
            "KafkaVersion": "2.8.1",
            "NumberOfBrokerNodes": 3,
        },
        Tags=FAKE_TAGS,
    )

    clusters = client.list_clusters_v2()

    assert len(clusters["ClusterInfoList"]) == 2
    for cluster in clusters["ClusterInfoList"]:
        assert "ActiveOperationArn" in cluster
        assert "ClusterType" in cluster
        assert "ClusterArn" in cluster
        assert "ClusterName" in cluster
        assert "CreationTime" in cluster
        assert "CurrentVersion" in cluster
        assert "State" in cluster
        assert "StateInfo" in cluster
        assert "Tags" in cluster

        cluster_type = cluster["ClusterType"]
        assert cluster_type[0].upper() + cluster_type[1:].lower() in cluster


@mock_aws
def test_put_cluster_policy():
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

    cluster_arn = create_resp["ClusterArn"]

    policy_doc = """
        {
            "Version":"2012-10-17",
            "Statement":[
                {"Effect":"Allow",
                "Principal":"*",
                "Action":"kafka:*",
                "Resource":"*"}
                ]
            }

    """

    put_resp = client.put_cluster_policy(
        ClusterArn=cluster_arn,
        CurrentVersion="",
        Policy=policy_doc,
    )

    assert "CurrentVersion" in put_resp
    first_version = put_resp["CurrentVersion"]
    assert first_version != ""

    # Verify get_cluser_policy
    get_resp = client.get_cluster_policy(ClusterArn=cluster_arn)
    assert get_resp["Policy"] == policy_doc
    assert get_resp["CurrentVersion"] == first_version

    # Update policy
    updated_policy_doc = """
        {
            "Version":"2012-10-17",
            "Statement":[
                {"Effect":"Allow",
                "Principal":"*",
                "Action":"kafka:*",
                "Resource":"*"}
                ]
            }

    """

    put_resp2 = client.put_cluster_policy(
        ClusterArn=cluster_arn,
        CurrentVersion=first_version,
        Policy=updated_policy_doc,
    )
    second_version = put_resp2["CurrentVersion"]
    assert second_version != first_version  # version should update

    # get updated policy
    get_resp2 = client.get_cluster_policy(ClusterArn=cluster_arn)
    assert get_resp2["Policy"] == updated_policy_doc
    assert get_resp2["CurrentVersion"] == second_version

    # update old version. Should raise error
    with pytest.raises(ClientError) as exc:
        client.put_cluster_policy(
            ClusterArn=cluster_arn,
            CurrentVersion=first_version,
            Policy=policy_doc,
        )
    resp = exc.value.response
    error = resp["Error"]
    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 400
    assert error["Code"] == "BadRequestException"
    assert (
        error["Message"]
        == f"Version mismatch: expected {second_version}, got {first_version}"
    )


@mock_aws
def test_put_cluster_policy_not_found():
    client = boto3.client("kafka", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.put_cluster_policy(
            ClusterArn="INVALID_ARN",
            CurrentVersion="",
            Policy="",
        )
    resp = exc.value.response
    error = resp["Error"]
    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 400
    assert error["Code"] == "BadRequestException"
    assert error["Message"] == "Resource not found: INVALID_ARN"


@mock_aws
def test_get_cluster_policy_not_found():
    client = boto3.client("kafka", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.get_cluster_policy(ClusterArn="INVALID_ARN")
    resp = exc.value.response
    error = resp["Error"]
    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 400
    assert error["Code"] == "NotFoundException"
    assert error["Message"] == "Resource not found: INVALID_ARN"


@mock_aws
def test_delete_cluster_policy():
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
    cluster_arn = create_resp["ClusterArn"]

    policy_doc = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"kafka:*","Resource":"*"}]}'
    client.put_cluster_policy(
        ClusterArn=cluster_arn,
        CurrentVersion="",
        Policy=policy_doc,
    )

    get_resp = client.get_cluster_policy(ClusterArn=cluster_arn)
    assert get_resp["Policy"] == policy_doc

    delete_resp = client.delete_cluster_policy(ClusterArn=cluster_arn)
    assert delete_resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    get_resp = client.get_cluster_policy(ClusterArn=cluster_arn)
    assert get_resp["Policy"] == ""
    assert get_resp["CurrentVersion"] == ""


@mock_aws
def test_delete_cluster_policy_not_found():
    client = boto3.client("kafka", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.delete_cluster_policy(ClusterArn="INVALID_ARN")
    resp = exc.value.response
    error = resp["Error"]
    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 400
    assert error["Code"] == "NotFoundException"
    assert error["Message"] == "Resource not found: INVALID_ARN"
