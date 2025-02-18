import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_cloudhsmv2_list_tags():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    resource_id = "cluster-1234"
    tag_list = [
        {"Key": "Environment", "Value": "Production"},
        {"Key": "Project", "Value": "Security"},
    ]

    res = test_client.post(
        "/",
        data=json.dumps({"ResourceId": resource_id, "TagList": tag_list}),
        headers={"X-Amz-Target": "CloudHsmV2.TagResource"},
    )
    assert res.status_code == 200

    res = test_client.post(
        "/",
        data=json.dumps({"ResourceId": resource_id}),
        headers={"X-Amz-Target": "CloudHsmV2.ListTags"},
    )
    assert res.status_code == 200

    response_data = json.loads(res.data.decode("utf-8"))
    assert "TagList" in response_data
    assert len(response_data["TagList"]) == 2
    assert {"Key": "Environment", "Value": "Production"} in response_data["TagList"]
    assert {"Key": "Project", "Value": "Security"} in response_data["TagList"]


@mock_aws
def test_cloudhsmv2_create_cluster():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    cluster_data = {
        "HsmType": "hsm1.medium",
        "SubnetIds": ["subnet-12345678"],
        "TagList": [{"Key": "Environment", "Value": "Production"}],
    }

    res = test_client.post(
        "/",
        data=json.dumps(cluster_data),
        headers={"X-Amz-Target": "CloudHsmV2.CreateCluster"},
    )

    assert res.status_code == 200
    response_data = json.loads(res.data.decode("utf-8"))
    assert "Cluster" in response_data
    assert response_data["Cluster"]["HsmType"] == "hsm1.medium"
    assert response_data["Cluster"]["State"] == "ACTIVE"
    assert response_data["Cluster"]["TagList"] == [
        {"Key": "Environment", "Value": "Production"}
    ]


@mock_aws
def test_cloudhsmv2_describe_clusters():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    cluster_data = {
        "HsmType": "hsm1.medium",
        "SubnetIds": ["subnet-12345678"],
    }
    test_client.post(
        "/",
        data=json.dumps(cluster_data),
        headers={"X-Amz-Target": "CloudHsmV2.CreateCluster"},
    )

    res = test_client.post(
        "/",
        data="{}",
        headers={"X-Amz-Target": "CloudHsmV2.DescribeClusters"},
    )

    assert res.status_code == 200
    response_data = json.loads(res.data.decode("utf-8"))
    assert "Clusters" in response_data
    assert len(response_data["Clusters"]) == 1
    assert response_data["Clusters"][0]["HsmType"] == "hsm1.medium"


@mock_aws
def test_cloudhsmv2_untag_resource():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    resource_id = "cluster-1234"
    tag_list = [
        {"Key": "Environment", "Value": "Production"},
        {"Key": "Project", "Value": "Security"},
        {"Key": "Team", "Value": "DevOps"},
    ]

    test_client.post(
        "/",
        data=json.dumps({"ResourceId": resource_id, "TagList": tag_list}),
        headers={"X-Amz-Target": "CloudHsmV2.TagResource"},
    )

    res = test_client.post(
        "/",
        data=json.dumps(
            {"ResourceId": resource_id, "TagKeyList": ["Environment", "Team"]}
        ),
        headers={"X-Amz-Target": "CloudHsmV2.UntagResource"},
    )
    assert res.status_code == 200

    res = test_client.post(
        "/",
        data=json.dumps({"ResourceId": resource_id}),
        headers={"X-Amz-Target": "CloudHsmV2.ListTags"},
    )
    response_data = json.loads(res.data.decode("utf-8"))
    assert len(response_data["TagList"]) == 1
    assert {"Key": "Project", "Value": "Security"} in response_data["TagList"]


@mock_aws
def test_cloudhsmv2_delete_cluster():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    cluster_data = {
        "HsmType": "hsm1.medium",
        "SubnetIds": ["subnet-12345678"],
    }
    res = test_client.post(
        "/",
        data=json.dumps(cluster_data),
        headers={"X-Amz-Target": "CloudHsmV2.CreateCluster"},
    )
    cluster_id = json.loads(res.data.decode("utf-8"))["Cluster"]["ClusterId"]

    res = test_client.post(
        "/",
        data=json.dumps({"ClusterId": cluster_id}),
        headers={"X-Amz-Target": "CloudHsmV2.DeleteCluster"},
    )

    assert res.status_code == 200
    response_data = json.loads(res.data.decode("utf-8"))
    assert response_data["Cluster"]["State"] == "DELETED"
    assert response_data["Cluster"]["StateMessage"] == "Cluster deleted"


@mock_aws
def test_cloudhsmv2_describe_backups():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    cluster_data = {
        "HsmType": "hsm1.medium",
        "SubnetIds": ["subnet-12345678"],
    }
    test_client.post(
        "/",
        data=json.dumps(cluster_data),
        headers={"X-Amz-Target": "CloudHsmV2.CreateCluster"},
    )

    res = test_client.post(
        "/",
        data="{}",
        headers={"X-Amz-Target": "CloudHsmV2.DescribeBackups"},
    )

    assert res.status_code == 200
    response_data = json.loads(res.data.decode("utf-8"))
    assert "Backups" in response_data
    assert len(response_data["Backups"]) == 1
    assert response_data["Backups"][0]["BackupState"] == "READY"
    assert response_data["Backups"][0]["HsmType"] == "hsm1.medium"


@mock_aws
def test_cloudhsmv2_resource_policy():
    backend = server.create_backend_app("cloudhsmv2")
    test_client = backend.test_client()

    cluster_data = {
        "HsmType": "hsm1.medium",
        "SubnetIds": ["subnet-12345678"],
    }
    test_client.post(
        "/",
        data=json.dumps(cluster_data),
        headers={"X-Amz-Target": "CloudHsmV2.CreateCluster"},
    )

    res = test_client.post(
        "/",
        data="{}",
        headers={"X-Amz-Target": "CloudHsmV2.DescribeBackups"},
    )
    backup_arn = json.loads(res.data.decode("utf-8"))["Backups"][0]["BackupArn"]

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
    res = test_client.post(
        "/",
        data=json.dumps({"ResourceArn": backup_arn, "Policy": json.dumps(policy)}),
        headers={"X-Amz-Target": "CloudHsmV2.PutResourcePolicy"},
    )

    assert res.status_code == 200
    response_data = json.loads(res.data.decode("utf-8"))
    assert response_data["ResourceArn"] == backup_arn
    assert json.loads(response_data["Policy"]) == policy

    res = test_client.post(
        "/",
        data=json.dumps({"ResourceArn": backup_arn}),
        headers={"X-Amz-Target": "CloudHsmV2.GetResourcePolicy"},
    )

    assert res.status_code == 200
    response_data = json.loads(res.data.decode("utf-8"))
    assert json.loads(response_data["Policy"]) == policy
