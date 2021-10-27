"""Unit tests for emrcontainers-supported APIs."""
import re
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from moto import mock_emrcontainers
from unittest.mock import patch
from boto3 import Session
from moto.emrcontainers import REGION as DEFAULT_REGION

REGION = Session().region_name or DEFAULT_REGION


@pytest.fixture(scope="function")
def client():
    with mock_emrcontainers():
        yield boto3.client("emr-containers", region_name=REGION)


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
                clientToken="string",
            )

            cluster_list.append(resp["id"])

    yield cluster_list


def test_create_virtual_cluster(client):
    resp = client.create_virtual_cluster(
        name="test-emr-virtual-cluster",
        containerProvider={
            "type": "EKS",
            "id": "test-eks-cluster",
            "info": {"eksInfo": {"namespace": "emr-container"}},
        },
        clientToken="string",
    )

    assert resp["name"] == "test-emr-virtual-cluster"
    assert re.match(r"[a-z,0-9]{25}", resp["id"])
    assert (
        resp["arn"]
        == f"arn:aws:emr-containers:us-east-1:123456789012:/virtualclusters/{resp['id']}"
    )


def test_delete_virtual_cluster(client, virtual_cluster_factory):
    cluster_list = virtual_cluster_factory

    resp = client.delete_virtual_cluster(id=cluster_list[0])

    assert resp["id"] == cluster_list[0]


# def test_list_virtual_clusters(client, virtual_cluster_factory):
#
#     resp = client.list_virtual_clusters()
#
#     assert resp == 3
