"""Unit tests for emrcontainers-supported APIs."""
import re
from datetime import datetime, timezone

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError, ValidationError

from moto import mock_emrcontainers
from unittest.mock import patch

from moto.emrcontainers import REGION as DEFAULT_REGION


@pytest.fixture(scope="function")
def client():
    with mock_emrcontainers():
        yield boto3.client("emr-containers", region_name=DEFAULT_REGION)


@pytest.fixture(scope="function")
def virtual_cluster_factory(client):
    cluster_state = ["RUNNING", "TERMINATING", "TERMINATED", "ARRESTED"]

    cluster_list = []
    for i in range(4):
        with patch("moto.emrcontainers.models.ACTIVE_STATUS", cluster_state[i]):
            resp = client.create_virtual_cluster(
                name="test-emr-virtual-cluster",
                containerProvider={
                    "type": "EKS",
                    "id": "test-eks-cluster",
                    "info": {"eksInfo": {"namespace": "emr-container"}},
                },
            )

            cluster_list.append(resp["id"])

    yield cluster_list


@mock_emrcontainers
def test_create_virtual_cluster():
    client = boto3.client("emr-containers", region_name=DEFAULT_REGION)
    resp = client.create_virtual_cluster(
        name="test-emr-virtual-cluster",
        containerProvider={
            "type": "EKS",
            "id": "test-eks-cluster",
            "info": {"eksInfo": {"namespace": "emr-container"}},
        },
    )

    assert resp["name"] == "test-emr-virtual-cluster"
    assert re.match(r"[a-z,0-9]{25}", resp["id"])
    assert (
        resp["arn"]
        == f"arn:aws:emr-containers:us-east-1:123456789012:/virtualclusters/{resp['id']}"
    )


@mock_emrcontainers
def test_create_virtual_cluster_on_same_namespace():
    client = boto3.client("emr-containers", region_name=DEFAULT_REGION)

    client.create_virtual_cluster(
        name="test-emr-virtual-cluster",
        containerProvider={
            "type": "EKS",
            "id": "test-eks-cluster",
            "info": {"eksInfo": {"namespace": "emr-container"}},
        },
    )

    with pytest.raises(
        ClientError, match="A virtual cluster already exists in the given namespace"
    ):
        client.create_virtual_cluster(
            name="test-emr-virtual-cluster",
            containerProvider={
                "type": "EKS",
                "id": "test-eks-cluster",
                "info": {"eksInfo": {"namespace": "emr-container"}},
            },
        )


def test_delete_virtual_cluster(client, virtual_cluster_factory):
    cluster_list = virtual_cluster_factory

    resp = client.delete_virtual_cluster(id=cluster_list[0])

    assert resp["id"] == cluster_list[0]


def test_describe_virtual_cluster(client, virtual_cluster_factory):
    cluster_list = virtual_cluster_factory
    virtual_cluster_id = cluster_list[0]

    resp = client.describe_virtual_cluster(id=virtual_cluster_id)

    expected_resp = {
        "arn": f"arn:aws:emr-containers:us-east-1:123456789012:/virtualclusters/{virtual_cluster_id}",
        "containerProvider": {
            "id": "test-eks-cluster",
            "info": {"eksInfo": {"namespace": "emr-container"}},
            "type": "EKS",
        },
        "createdAt": (
            datetime.today()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=timezone.utc)
        ),
        "id": virtual_cluster_id,
        "name": "test-emr-virtual-cluster",
        "state": "RUNNING",
    }

    assert resp["virtualCluster"] == expected_resp


# def test_list_virtual_clusters(client, virtual_cluster_factory):
#
#     resp = client.list_virtual_clusters()
#
#     assert resp == 3
