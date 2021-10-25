"""Unit tests for emrcontainers-supported APIs."""
import re

import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_emrcontainers
from boto3 import Session


from moto.emrcontainers import REGION as DEFAULT_REGION

REGION = Session().region_name or DEFAULT_REGION


@mock_emrcontainers
def test_list():
    """Test input/output of the list API."""
    # do test
    pass


@mock_emrcontainers
def test_create_virtual_cluster():
    conn = boto3.client("emr-containers", region_name="us-east-1")

    resp = conn.create_virtual_cluster(
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


@mock_emrcontainers
def test_delete_virtual_cluster():
    conn = boto3.client("emr-containers", region_name="us-east-1")

    resp = conn.describe_job_run(id="ddddd", virtualClusterId = "ddddd")

    assert resp == "test-emr-virtual-cluster"


@mock_emrcontainers
def test_list_virtual_clusters():
    conn = boto3.client("emr-containers", region_name="us-east-1")

    conn.create_virtual_cluster(
        name="test-emr-virtual-cluster_1",
        containerProvider={
            "type": "EKS",
            "id": "test-eks-cluster",
            "info": {"eksInfo": {"namespace": "emr-container"}},
        },
        clientToken="string",
    )

    conn.create_virtual_cluster(
        name="test-emr-virtual-cluster_2",
        containerProvider={
            "type": "EKS",
            "id": "test-eks-cluster",
            "info": {"eksInfo": {"namespace": "emr-container"}},
        },
        clientToken="string",
    )

    resp = conn.list_virtual_clusters()

    assert resp == 3
