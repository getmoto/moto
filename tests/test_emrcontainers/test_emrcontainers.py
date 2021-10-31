"""Unit tests for emrcontainers-supported APIs."""
import re
from datetime import datetime, timezone, timedelta
from unittest import SkipTest

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError, ParamValidationError

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
        with patch(
            "moto.emrcontainers.models.VIRTUAL_CLUSTER_STATUS", cluster_state[i]
        ):
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


@pytest.fixture()
def job_factory(client, virtual_cluster_factory):
    virtual_cluster_id = virtual_cluster_factory[0]
    default_job_driver = {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://code/pi.py",
            "sparkSubmitParameters": "--conf spark.executor.instances=2 --conf spark.executor.memory=2G --conf spark.driver.memory=2G --conf spark.executor.cores=4",
        }
    }
    default_execution_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-emrcontainers"
    default_release_label = "emr-6.3.0-latest"

    resp = client.start_job_run(
        name="test_job",
        virtualClusterId=virtual_cluster_id,
        executionRoleArn=default_execution_role_arn,
        releaseLabel=default_release_label,
        jobDriver=default_job_driver,
    )

    yield [resp["id"]]


class TestStartJobRun:
    default_job_driver = {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://code/pi.py",
            "sparkSubmitParameters": "--conf spark.executor.instances=2 --conf spark.executor.memory=2G --conf spark.driver.memory=2G --conf spark.executor.cores=4",
        }
    }

    default_configuration_overrides = {
        "applicationConfiguration": [
            {
                "classification": "spark-defaults",
                "properties": {"spark.dynamicAllocation.enabled": "false"},
            }
        ],
        "monitoringConfiguration": {
            "cloudWatchMonitoringConfiguration": {
                "logGroupName": "/emr-containers/jobs",
                "logStreamNamePrefix": "demo",
            },
            "s3MonitoringConfiguration": {"logUri": "s3://joblogs"},
        },
    }

    default_execution_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-emrcontainers"

    default_release_label = "emr-6.3.0-latest"

    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, virtual_cluster_factory):
        self.client = client
        self.virtual_cluster_id = virtual_cluster_factory[0]

    def test_start(self):
        resp = self.client.start_job_run(
            name="test_job",
            virtualClusterId=self.virtual_cluster_id,
            executionRoleArn=self.default_execution_role_arn,
            releaseLabel=self.default_release_label,
            jobDriver=self.default_job_driver,
            configurationOverrides=self.default_configuration_overrides,
        )

        assert re.match(r"[a-z,0-9]{19}", resp["id"])
        assert resp["name"] == "test_job"
        assert (
            resp["arn"]
            == f"arn:aws:emr-containers:us-east-1:{ACCOUNT_ID}:/virtualclusters/{self.virtual_cluster_id}/jobruns/{resp['id']}"
        )
        assert resp["virtualClusterId"] == self.virtual_cluster_id

    def test_invalid_execution_role_arn(self):
        with pytest.raises(ParamValidationError) as exc:
            self.client.start_job_run(
                name="test_job",
                virtualClusterId="foobaa",
                executionRoleArn="foobaa",
                releaseLabel="foobaa",
                jobDriver={},
            )

        assert exc.typename == "ParamValidationError"
        assert (
            "Parameter validation failed:\nInvalid length for parameter executionRoleArn, value: 6, valid min length: 20"
            in exc.value.args
        )

    def test_invalid_virtual_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.start_job_run(
                name="test_job",
                virtualClusterId="foobaa",
                executionRoleArn=self.default_execution_role_arn,
                releaseLabel="foobaa",
                jobDriver={},
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Virtual cluster foobaa doesn't exist."

    def test_invalid_release_label(self):
        with pytest.raises(ClientError) as exc:
            self.client.start_job_run(
                name="test_job",
                virtualClusterId=self.virtual_cluster_id,
                executionRoleArn=self.default_execution_role_arn,
                releaseLabel="foobaa",
                jobDriver={},
            )
        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Release foobaa doesn't exist."


class TestCancelJobRun:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, virtual_cluster_factory, job_factory):
        self.client = client
        self.virtual_cluster_id = virtual_cluster_factory[0]
        self.job_list = job_factory

    def test_valid_id_valid_cluster_id(self):
        resp = self.client.cancel_job_run(
            id=self.job_list[0], virtualClusterId=self.virtual_cluster_id
        )

        assert resp["id"] == self.job_list[0]
        assert resp["virtualClusterId"] == self.virtual_cluster_id

    def test_invalid_id_invalid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.cancel_job_run(id="foobaa", virtualClusterId="foobaa")

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "Invalid job run short id"

    def test_invalid_id_valid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.cancel_job_run(
                id="foobaa", virtualClusterId=self.virtual_cluster_id
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "Invalid job run short id"

    def test_valid_id_invalid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.cancel_job_run(id=self.job_list[0], virtualClusterId="foobaa")

        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == f"Job run {self.job_list[0]} doesn't exist."

    def test_non_existing_id_invalid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.cancel_job_run(
                id="123456789abcdefghij", virtualClusterId=self.virtual_cluster_id
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == f"Job run 123456789abcdefghij doesn't exist."
