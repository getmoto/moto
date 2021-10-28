"""Test different server responses."""
import re

import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

import moto.server as server
from moto import mock_emrcontainers
from moto.core import ACCOUNT_ID


@pytest.fixture(scope="function")
def client():
    with mock_emrcontainers():
        backend = server.create_backend_app("emr-containers")
        yield backend.test_client()


@pytest.fixture(scope="function")
def virtual_cluster_factory(client):

    cluster_list = []
    for i in range(4):
        resp = client.create_virtual_cluster(
            name="test-emr-virtual-cluster",
            containerProvider={
                "type": "EKS",
                "id": "test-eks-cluster",
                "info": {"eksInfo": {"namespace": f"emr-container-{i}"}},
            },
        )

        cluster_list.append(resp["id"])

    client.delete_virtual_cluster(cluster_list[0], cluster_list[2])

    yield cluster_list


class TestCreateVirtualCluster:
    @staticmethod
    @mock_emrcontainers
    def test_create_virtual_cluster(client):
        resp = client.create_virtual_cluster(
            name="test-emr-virtual-cluster",
            containerProvider={
                "type": "EKS",
                "id": "test-eks-cluster",
                "info": {"eksInfo": {"namespace": "emr-container"}},
            },
        )

        cluster_count = len(client.list_virtual_clusters()["virtualClusters"])

        assert resp["name"] == "test-emr-virtual-cluster"
        assert re.match(r"[a-z,0-9]{25}", resp["id"])
        assert (
            resp["arn"]
            == f"arn:aws:emr-containers:us-east-1:{ACCOUNT_ID}:/virtualclusters/{resp['id']}"
        )
        assert cluster_count == 1

    @staticmethod
    @mock_emrcontainers
    def test_create_virtual_cluster_on_same_namespace(client):
        client.create_virtual_cluster(
            name="test-emr-virtual-cluster",
            containerProvider={
                "type": "EKS",
                "id": "test-eks-cluster",
                "info": {"eksInfo": {"namespace": "emr-container"}},
            },
        )

        with pytest.raises(ClientError) as exc:
            client.create_virtual_cluster(
                name="test-emr-virtual-cluster",
                containerProvider={
                    "type": "EKS",
                    "id": "test-eks-cluster",
                    "info": {"eksInfo": {"namespace": "emr-container"}},
                },
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert (
            err["Message"] == "A virtual cluster already exists in the given namespace"
        )
