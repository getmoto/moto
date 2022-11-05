"""Unit tests for emrcontainers-supported APIs."""
import re
from datetime import datetime, timezone, timedelta
from unittest import SkipTest

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError, ParamValidationError

from moto import mock_emrcontainers, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from unittest.mock import patch

from moto.emrcontainers import REGION as DEFAULT_REGION


@pytest.fixture(scope="function", name="client")
def fixture_client():
    with mock_emrcontainers():
        yield boto3.client("emr-containers", region_name=DEFAULT_REGION)


@pytest.fixture(scope="function", name="virtual_cluster_factory")
def fixture_virtual_cluster_factory(client):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    cluster_state = ["RUNNING", "TERMINATING", "TERMINATED", "ARRESTED"]

    cluster_list = []
    for i in range(len(cluster_state)):
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


@pytest.fixture(name="job_factory")
def fixture_job_factory(client, virtual_cluster_factory):
    virtual_cluster_id = virtual_cluster_factory[0]
    default_job_driver = {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://code/pi.py",
            "sparkSubmitParameters": "--conf spark.executor.instances=2 --conf spark.executor.memory=2G --conf spark.driver.memory=2G --conf spark.executor.cores=4",
        }
    }
    default_execution_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-emrcontainers"
    default_release_label = "emr-6.3.0-latest"

    job_state = [
        "PENDING",
        "SUBMITTED",
        "RUNNING",
        "FAILED",
        "CANCELLED",
        "CANCEL_PENDING",
        "COMPLETED",
    ]

    job_list = []
    for i in range(len(job_state)):
        with patch("moto.emrcontainers.models.JOB_STATUS", job_state[i]):
            resp = client.start_job_run(
                name=f"test_job_{i}",
                virtualClusterId=virtual_cluster_id,
                executionRoleArn=default_execution_role_arn,
                releaseLabel=default_release_label,
                jobDriver=default_job_driver,
            )

            job_list.append(resp["id"])

    yield job_list


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
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    @pytest.fixture(autouse=True)
    def _setup_environment(
        self, client, virtual_cluster_factory
    ):  # pylint: disable=unused-argument
        self.client = client

    @pytest.mark.parametrize(
        "list_virtual_clusters_args,job_count",
        [
            ({}, 4),
            ({"containerProviderId": "test-eks-cluster"}, 4),
            ({"containerProviderId": "foobaa"}, 0),
            ({"containerProviderType": "EKS"}, 4),
            ({"containerProviderType": "AKS"}, 0),
            ({"createdAfter": yesterday}, 4),
            ({"createdAfter": tomorrow}, 0),
            ({"createdAfter": yesterday, "states": ["RUNNING"]}, 1),
            ({"createdAfter": tomorrow, "states": ["RUNNING"]}, 0),
            (
                {
                    "createdAfter": yesterday,
                    "states": ["RUNNING", "TERMINATED"],
                    "maxResults": 1,
                },
                1,
            ),
            ({"createdBefore": yesterday}, 0),
            ({"createdBefore": tomorrow}, 4),
            ({"createdBefore": yesterday, "states": ["RUNNING"]}, 0),
            ({"createdBefore": tomorrow, "states": ["RUNNING"]}, 1),
            (
                {
                    "createdBefore": tomorrow,
                    "states": ["RUNNING", "TERMINATED"],
                    "maxResults": 1,
                },
                1,
            ),
            ({"states": ["RUNNING"]}, 1),
            ({"states": ["RUNNING", "TERMINATED"]}, 2),
            ({"states": ["FOOBAA"]}, 0),
            ({"maxResults": 1}, 1),
        ],
    )
    def test_base(self, list_virtual_clusters_args, job_count):
        resp = self.client.list_virtual_clusters(**list_virtual_clusters_args)
        assert len(resp["virtualClusters"]) == job_count

    def test_next_token(self):
        resp = self.client.list_virtual_clusters(maxResults=2)
        assert len(resp["virtualClusters"]) == 2

        resp = self.client.list_virtual_clusters(nextToken=resp["nextToken"])
        assert len(resp["virtualClusters"]) == 2


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
            id=self.job_list[2], virtualClusterId=self.virtual_cluster_id
        )

        assert resp["id"] == self.job_list[2]
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
        assert err["Message"] == "Job run 123456789abcdefghij doesn't exist."

    def test_wrong_job_state(self):
        with pytest.raises(ClientError) as exc:
            self.client.cancel_job_run(
                id=self.job_list[6], virtualClusterId=self.virtual_cluster_id
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == f"Job run {self.job_list[6]} is not in a cancellable state"
        )


class TestListJobRuns:
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    @pytest.fixture(autouse=True)
    def _setup_environment(
        self, client, virtual_cluster_factory, job_factory
    ):  # pylint: disable=unused-argument
        self.client = client
        self.virtual_cluster_id = virtual_cluster_factory[0]

    @pytest.mark.parametrize(
        "list_job_runs_arg,job_count",
        [
            ({}, 7),
            ({"createdAfter": yesterday}, 7),
            ({"createdAfter": tomorrow}, 0),
            ({"createdAfter": yesterday, "states": ["RUNNING"]}, 1),
            ({"createdAfter": tomorrow, "states": ["RUNNING"]}, 0),
            (
                {
                    "createdAfter": yesterday,
                    "states": ["RUNNING", "TERMINATED"],
                    "maxResults": 1,
                },
                1,
            ),
            ({"createdBefore": yesterday}, 0),
            ({"createdBefore": tomorrow}, 7),
            (
                {
                    "createdBefore": tomorrow,
                    "states": ["RUNNING", "TERMINATED"],
                    "maxResults": 1,
                },
                1,
            ),
            ({"name": "test_job_1"}, 1),
            ({"name": "foobaa"}, 0),
            ({"states": ["RUNNING"]}, 1),
            ({"states": ["RUNNING", "COMPLETED"]}, 2),
            ({"states": ["FOOBAA"]}, 0),
            ({"maxResults": 1}, 1),
        ],
    )
    def test_base(self, list_job_runs_arg, job_count):
        resp = self.client.list_job_runs(
            virtualClusterId=self.virtual_cluster_id, **list_job_runs_arg
        )
        assert len(resp["jobRuns"]) == job_count

    def test_invalid_virtual_cluster_id(self):
        resp = self.client.list_job_runs(virtualClusterId="foobaa")
        assert len(resp["jobRuns"]) == 0

    def test_next_token(self):
        resp = self.client.list_job_runs(
            virtualClusterId=self.virtual_cluster_id, maxResults=2
        )
        assert len(resp["jobRuns"]) == 2

        resp = self.client.list_job_runs(
            virtualClusterId=self.virtual_cluster_id, nextToken=resp["nextToken"]
        )
        assert len(resp["jobRuns"]) == 5


class TestDescribeJobRun:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, virtual_cluster_factory, job_factory):
        self.client = client
        self.virtual_cluster_id = virtual_cluster_factory[0]
        self.job_list = job_factory

    def test_valid_id_valid_cluster_id(self):
        self.client.cancel_job_run(
            id=self.job_list[2], virtualClusterId=self.virtual_cluster_id
        )
        resp = self.client.describe_job_run(
            id=self.job_list[2], virtualClusterId=self.virtual_cluster_id
        )

        expected = {
            "arn": f"arn:aws:emr-containers:us-east-1:{ACCOUNT_ID}:/virtualclusters/{self.virtual_cluster_id}/jobruns/{self.job_list[2]}",
            "createdAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
            "executionRoleArn": f"arn:aws:iam::{ACCOUNT_ID}:role/iamrole-emrcontainers",
            "finishedAt": (
                datetime.today()
                .replace(hour=0, minute=1, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
            "id": self.job_list[2],
            "jobDriver": {
                "sparkSubmitJobDriver": {
                    "entryPoint": "s3://code/pi.py",
                    "sparkSubmitParameters": "--conf "
                    "spark.executor.instances=2 "
                    "--conf "
                    "spark.executor.memory=2G "
                    "--conf "
                    "spark.driver.memory=2G "
                    "--conf "
                    "spark.executor.cores=4",
                }
            },
            "name": "test_job_2",
            "releaseLabel": "emr-6.3.0-latest",
            "state": "CANCELLED",
            "stateDetails": "JobRun CANCELLED successfully.",
            "virtualClusterId": self.virtual_cluster_id,
        }

        assert expected.items() <= resp["jobRun"].items()

    def test_invalid_id_invalid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.describe_job_run(id="foobaa", virtualClusterId="foobaa")

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "Invalid job run short id"

    def test_invalid_id_valid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.describe_job_run(
                id="foobaa", virtualClusterId=self.virtual_cluster_id
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "Invalid job run short id"

    def test_valid_id_invalid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.describe_job_run(id=self.job_list[0], virtualClusterId="foobaa")

        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == f"Job run {self.job_list[0]} doesn't exist."

    def test_non_existing_id_invalid_cluster_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.describe_job_run(
                id="123456789abcdefghij", virtualClusterId=self.virtual_cluster_id
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Job run 123456789abcdefghij doesn't exist."
