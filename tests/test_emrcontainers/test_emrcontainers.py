"""Unit tests for emrcontainers-supported APIs."""
import re
from datetime import datetime, timezone, timedelta
from unittest import SkipTest

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_emrcontainers, settings
from moto.core import ACCOUNT_ID
from unittest.mock import patch

from moto.emrcontainers import REGION as DEFAULT_REGION


@pytest.fixture(scope="function")
def client():
    with mock_emrcontainers():
        yield boto3.client("emr-containers", region_name=DEFAULT_REGION)


@pytest.fixture(scope="function")
def virtual_cluster_factory(client):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    cluster_state = ["RUNNING", "TERMINATING", "TERMINATED", "ARRESTED"]

    cluster_list = []
    for i in range(4):
        with patch("moto.emrcontainers.models.ACTIVE_STATUS", cluster_state[i]):
            resp = client.create_virtual_cluster(
                name="test-emr-virtual-cluster",
                containerProvider={
                    "type": "EKS",
                    "id": "test-eks-cluster",
                    "info": {"eksInfo": {"namespace": f"emr-container-{i}"}},
                },
            )

            cluster_list.append(resp["id"])

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


class TestDeleteVirtualCluster:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, virtual_cluster_factory):
        self.client = client
        self.virtual_cluster_ids = virtual_cluster_factory

    def test_existing_virtual_cluster(self):
        resp = self.client.delete_virtual_cluster(id=self.virtual_cluster_ids[0])
        assert resp["id"] == self.virtual_cluster_ids[0]

    def test_non_existing_virtual_cluster(self):
        with pytest.raises(ClientError) as exc:
            self.client.delete_virtual_cluster(id="foobaa")

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "VirtualCluster does not exist"


class TestDescribeVirtualCluster:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, virtual_cluster_factory):
        self.client = client
        self.virtual_cluster_ids = virtual_cluster_factory

    def test_existing_virtual_cluster(self):
        resp = self.client.describe_virtual_cluster(id=self.virtual_cluster_ids[0])

        expected_resp = {
            "arn": f"arn:aws:emr-containers:us-east-1:{ACCOUNT_ID}:/virtualclusters/{self.virtual_cluster_ids[0]}",
            "containerProvider": {
                "id": "test-eks-cluster",
                "info": {"eksInfo": {"namespace": "emr-container-0"}},
                "type": "EKS",
            },
            "createdAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
            "id": self.virtual_cluster_ids[0],
            "name": "test-emr-virtual-cluster",
            "state": "RUNNING",
        }

        assert resp["virtualCluster"] == expected_resp

    def test_non_existing_virtual_cluster(self):
        with pytest.raises(ClientError) as exc:
            self.client.describe_virtual_cluster(id="foobaa")

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "Virtual cluster foobaa doesn't exist."


class TestListVirtualClusters:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, virtual_cluster_factory):
        self.client = client

    def test_base(self):
        resp = self.client.list_virtual_clusters()
        assert len(resp["virtualClusters"]) == 4

    def test_valid_container_provider_id(self):
        resp = self.client.list_virtual_clusters(containerProviderId="test-eks-cluster")
        assert len(resp["virtualClusters"]) == 4

    def test_invalid_container_provider_id(self):
        resp = self.client.list_virtual_clusters(containerProviderId="foobaa")
        assert len(resp["virtualClusters"]) == 0

    def test_valid_container_provider_type(self):
        resp = self.client.list_virtual_clusters(containerProviderType="EKS")
        assert len(resp["virtualClusters"]) == 4

    def test_invalid_container_provider_type(self):
        resp = self.client.list_virtual_clusters(containerProviderType="AKS")
        assert len(resp["virtualClusters"]) == 0

    def test_created_after_yesterday(self):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        resp = self.client.list_virtual_clusters(createdAfter=yesterday)
        assert len(resp["virtualClusters"]) == 4

    def test_created_after_tomorrow(self):
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        resp = self.client.list_virtual_clusters(createdAfter=tomorrow)
        assert len(resp["virtualClusters"]) == 0

    def test_created_after_yesterday_running_state(self):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        resp = self.client.list_virtual_clusters(
            createdAfter=yesterday, states=["RUNNING"]
        )
        assert len(resp["virtualClusters"]) == 1

    def test_created_after_tomorrow_running_state(self):
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        resp = self.client.list_virtual_clusters(
            createdAfter=tomorrow, states=["RUNNING"]
        )
        assert len(resp["virtualClusters"]) == 0

    def test_created_after_yesterday_two_state_limit(self):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        resp = self.client.list_virtual_clusters(
            createdAfter=yesterday, states=["RUNNING", "TERMINATED"], maxResults=1
        )
        assert len(resp["virtualClusters"]) == 1

    def test_created_before_yesterday(self):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        resp = self.client.list_virtual_clusters(createdBefore=yesterday)
        assert len(resp["virtualClusters"]) == 0

    def test_created_before_tomorrow(self):
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        resp = self.client.list_virtual_clusters(createdBefore=tomorrow)
        assert len(resp["virtualClusters"]) == 4

    def test_created_before_yesterday_running_state(self):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        resp = self.client.list_virtual_clusters(
            createdBefore=yesterday, states=["RUNNING"]
        )
        assert len(resp["virtualClusters"]) == 0

    def test_created_before_tomorrow_running_state(self):
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        resp = self.client.list_virtual_clusters(
            createdBefore=tomorrow, states=["RUNNING"]
        )
        assert len(resp["virtualClusters"]) == 1

    def test_created_before_tomorrow_two_state_limit(self):
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        resp = self.client.list_virtual_clusters(
            createdBefore=tomorrow, states=["RUNNING", "TERMINATED"], maxResults=1
        )
        assert len(resp["virtualClusters"]) == 1

    def test_states_one_state(self):
        resp = self.client.list_virtual_clusters(states=["RUNNING"])
        assert len(resp["virtualClusters"]) == 1

    def test_states_two_state(self):
        resp = self.client.list_virtual_clusters(states=["RUNNING", "TERMINATED"])
        assert len(resp["virtualClusters"]) == 2

    def test_states_invalid_state(self):
        resp = self.client.list_virtual_clusters(states=["FOOBAA"])
        assert len(resp["virtualClusters"]) == 0

    def test_max_result(self):
        resp = self.client.list_virtual_clusters(maxResults=1)
        assert len(resp["virtualClusters"]) == 1

    def test_next_token(self):
        resp = self.client.list_virtual_clusters(maxResults=2)
        assert len(resp["virtualClusters"]) == 2

        resp = self.client.list_virtual_clusters(nextToken=resp["nextToken"])
        assert len(resp["virtualClusters"]) == 2
