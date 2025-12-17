"""Unit tests for emrserverless-supported APIs."""

import re
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.emrserverless import REGION as DEFAULT_REGION
from moto.emrserverless import RELEASE_LABEL as DEFAULT_RELEASE_LABEL


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function", name="client")
def fixture_client():
    with mock_aws():
        yield boto3.client("emr-serverless", region_name=DEFAULT_REGION)


@pytest.fixture(scope="function", name="application_factory")
def fixture_application_factory(client):
    application_list = []

    if settings.TEST_SERVER_MODE:
        resp = client.create_application(
            name="test-emr-serverless-application-STARTED",
            type="SPARK",
            releaseLabel=DEFAULT_RELEASE_LABEL,
        )
        application_list.append(resp["applicationId"])

        resp = client.create_application(
            name="test-emr-serverless-application-STOPPED",
            type="SPARK",
            releaseLabel=DEFAULT_RELEASE_LABEL,
        )
        client.stop_application(applicationId=resp["applicationId"])
        application_list.append(resp["applicationId"])

    else:
        application_state = [
            "STARTED",
            "STOPPED",
            "CREATING",
            "CREATED",
            "STARTING",
            "STOPPING",
            "TERMINATED",
        ]

        for state in application_state:
            with patch("moto.emrserverless.models.APPLICATION_STATUS", state):
                resp = client.create_application(
                    name=f"test-emr-serverless-application-{state}",
                    type="SPARK",
                    releaseLabel=DEFAULT_RELEASE_LABEL,
                )

                application_list.append(resp["applicationId"])

    yield application_list


@pytest.fixture(scope="function", name="available_application")
def fixture_available_application(client):
    resp = client.create_application(
        name="test-emr-serverless-application",
        type="SPARK",
        releaseLabel=DEFAULT_RELEASE_LABEL,
    )

    yield resp["applicationId"]


@pytest.fixture(scope="function", name="job_run_factory")
def fixture_job_run_factory(client):
    app_1_resp = client.create_application(
        name="test-emr-serverless-application-1",
        type="SPARK",
        releaseLabel=DEFAULT_RELEASE_LABEL,
    )
    app_1_id = app_1_resp["applicationId"]

    job_1_resp = client.start_job_run(
        name="Test Job Run 1",
        applicationId=app_1_id,
        executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
        jobDriver={
            "sparkSubmit": {
                "entryPoint": "test.jar",
                "entryPointArguments": ["-h"],
                "sparkSubmitParameters": "--num-executors 1",
            }
        },
    )

    job_2_resp = client.start_job_run(
        name="Test Job Run 2",
        applicationId=app_1_id,
        executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
        jobDriver={
            "sparkSubmit": {
                "entryPoint": "test.jar",
                "entryPointArguments": ["-h"],
                "sparkSubmitParameters": "--num-executors 1",
            }
        },
        configurationOverrides={
            "monitoringConfiguration": {
                "s3MonitoringConfiguration": {"logUri": "s3://DOC-EXAMPLE-BUCKET/logs"}
            }
        },
        tags={"tag1": "tag1_val"},
        executionTimeoutMinutes=5,
    )

    app_2_resp = client.create_application(
        name="test-emr-serverless-application-2",
        type="SPARK",
        releaseLabel=DEFAULT_RELEASE_LABEL,
        tags={"tag1": "tag1_val"},
    )
    app_2_id = app_2_resp["applicationId"]

    job_3_resp = client.start_job_run(
        name="Test Job Run 3",
        applicationId=app_2_id,
        executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
        jobDriver={
            "sparkSubmit": {
                "entryPoint": "test.jar",
                "entryPointArguments": ["-h"],
                "sparkSubmitParameters": "--num-executors 1",
            }
        },
    )

    job_4_resp = client.start_job_run(
        name="Test Job Run 4",
        applicationId=app_2_id,
        executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
        jobDriver={
            "sparkSubmit": {
                "entryPoint": "test.jar",
                "entryPointArguments": ["-h"],
                "sparkSubmitParameters": "--num-executors 1",
            }
        },
        configurationOverrides={
            "monitoringConfiguration": {
                "s3MonitoringConfiguration": {"logUri": "s3://DOC-EXAMPLE-BUCKET/logs"}
            }
        },
        tags={"tag1": "tag1_val"},
        executionTimeoutMinutes=5,
    )

    yield {
        app_1_id: [job_1_resp["jobRunId"], job_2_resp["jobRunId"]],
        app_2_id: [job_3_resp["jobRunId"], job_4_resp["jobRunId"]],
    }


class TestCreateApplication:
    @staticmethod
    @mock_aws
    def test_create_application(client):
        resp = client.create_application(
            name="test-emr-serverless-application",
            type="SPARK",
            releaseLabel=DEFAULT_RELEASE_LABEL,
        )

        assert resp["name"] == "test-emr-serverless-application"
        assert re.match(r"[a-z,0-9]{16}", resp["applicationId"])
        assert resp["arn"] == (
            f"arn:aws:emr-serverless:{DEFAULT_REGION}:{ACCOUNT_ID}"
            f":/applications/{resp['applicationId']}"
        )

    @staticmethod
    @mock_aws
    def test_create_application_incorrect_type(client):
        with pytest.raises(ClientError) as exc:
            client.create_application(
                name="test-emr-serverless-application",
                type="SPARK3",
                releaseLabel=DEFAULT_RELEASE_LABEL,
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == "Unsupported engine SPARK3"

    @staticmethod
    @mock_aws
    def test_create_application_incorrect_release_label(client):
        with pytest.raises(ClientError) as exc:
            client.create_application(
                name="test-emr-serverless-application",
                type="SPARK",
                releaseLabel="emr-fake",
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert err["Message"] == (
            "Type 'SPARK' is not supported for release label 'emr-fake' "
            "or release label does not exist"
        )


class TestDeleteApplication:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, application_factory):
        self.client = client
        self.application_ids = application_factory

    @pytest.mark.parametrize(
        "index,status,expectation",
        argvalues=(
            [
                (0, "STARTED", pytest.raises(ClientError)),
                (1, "STOPPED", does_not_raise()),
            ]
            if settings.TEST_SERVER_MODE
            else [
                (0, "STARTED", pytest.raises(ClientError)),
                (1, "STOPPED", does_not_raise()),
                (2, "CREATING", pytest.raises(ClientError)),
                (3, "CREATED", does_not_raise()),
                (4, "STARTING", pytest.raises(ClientError)),
                (5, "STOPPING", pytest.raises(ClientError)),
                (6, "TERMINATED", pytest.raises(ClientError)),
            ]
        ),
    )
    def test_valid_application_id(self, index, status, expectation):
        with expectation as exc:
            resp = self.client.delete_application(
                applicationId=self.application_ids[index]
            )

        if exc:
            err = exc.value.response["Error"]
            assert err["Code"] == "ValidationException"
            assert err["Message"] == (
                f"Application {self.application_ids[index]} must be in one "
                "of the following statuses [CREATED, STOPPED]. Current "
                f"status: {status}"
            )
        else:
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.delete_application(applicationId="fake_application_id")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application fake_application_id does not exist"


class TestGetApplication:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client):
        self.client = client

    @staticmethod
    def get_expected_resp(application_id, extra_configuration):
        response = {
            "applicationId": application_id,
            "name": "test-emr-serverless-application",
            "arn": f"arn:aws:emr-serverless:{DEFAULT_REGION}:{ACCOUNT_ID}:/applications/{application_id}",
            "releaseLabel": "emr-6.6.0",
            "type": "Spark",
            "state": "STARTED",
            "stateDetails": "",
            "autoStartConfiguration": {"enabled": True},
            "autoStopConfiguration": {"enabled": True, "idleTimeoutMinutes": 15},
            "tags": {},
            "createdAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
            "updatedAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
        }
        return {**response, **extra_configuration}

    @pytest.mark.parametrize(
        "extra_configuration",
        [
            {},
            {
                "initialCapacity": {
                    "Driver": {
                        "workerCount": 1,
                        "workerConfiguration": {
                            "cpu": "2 vCPU",
                            "memory": "4 GB",
                            "disk": "20 GB",
                        },
                    }
                }
            },
            {
                "maximumCapacity": {
                    "cpu": "400 vCPU",
                    "memory": "1024 GB",
                    "disk": "1000 GB",
                }
            },
            {
                "networkConfiguration": {
                    "subnetIds": ["subnet-0123456789abcdefg"],
                    "securityGroupIds": ["sg-0123456789abcdefg"],
                }
            },
            {
                "initialCapacity": {
                    "Driver": {
                        "workerCount": 1,
                        "workerConfiguration": {
                            "cpu": "2 vCPU",
                            "memory": "4 GB",
                            "disk": "20 GB",
                        },
                    }
                },
                "maximumCapacity": {
                    "cpu": "400 vCPU",
                    "memory": "1024 GB",
                    "disk": "1000 GB",
                },
                "networkConfiguration": {
                    "subnetIds": ["subnet-0123456789abcdefg"],
                    "securityGroupIds": ["sg-0123456789abcdefg"],
                },
            },
        ],
    )
    def test_filtering(self, extra_configuration):
        application_id = self.client.create_application(
            name="test-emr-serverless-application",
            type="SPARK",
            releaseLabel=DEFAULT_RELEASE_LABEL,
            **extra_configuration,
        )["applicationId"]
        expected_resp = self.get_expected_resp(application_id, extra_configuration)

        actual_resp = self.client.get_application(applicationId=application_id)[
            "application"
        ]

        assert actual_resp == expected_resp

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.get_application(applicationId="fake_application_id")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application fake_application_id does not exist"


class TestListApplication:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, application_factory):
        self.client = client
        self.application_ids = application_factory

    def test_response_context(self):
        resp = self.client.list_applications()
        expected_resp = {
            "id": self.application_ids[0],
            "name": "test-emr-serverless-application-STARTED",
            "arn": (
                f"arn:aws:emr-serverless:{DEFAULT_REGION}:{ACCOUNT_ID}"
                f":/applications/{self.application_ids[0]}"
            ),
            "releaseLabel": "emr-6.6.0",
            "type": "Spark",
            "state": "STARTED",
            "stateDetails": "",
            "createdAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
            "updatedAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
        }

        actual_resp = [
            app for app in resp["applications"] if app["id"] == expected_resp["id"]
        ][0]

        assert actual_resp == expected_resp

    @pytest.mark.parametrize(
        "list_applications_args,job_count",
        argvalues=(
            [
                ({}, 2),
                ({"states": ["STARTED"]}, 1),
                ({"states": ["STARTED", "STOPPED"]}, 2),
                ({"states": ["FOOBAA"]}, 0),
                ({"maxResults": 1}, 1),
            ]
            if settings.TEST_SERVER_MODE
            else [
                ({}, 7),
                ({"states": ["CREATED"]}, 1),
                ({"states": ["CREATED", "STARTING"]}, 2),
                ({"states": ["FOOBAA"]}, 0),
                ({"maxResults": 1}, 1),
            ]
        ),
    )
    def test_filtering(self, list_applications_args, job_count):
        resp = self.client.list_applications(**list_applications_args)
        assert len(resp["applications"]) == job_count

    def test_next_token(self):
        if settings.TEST_SERVER_MODE:
            resp = self.client.list_applications(maxResults=1)
            assert len(resp["applications"]) == 1

            resp = self.client.list_applications(nextToken=resp["nextToken"])
            assert len(resp["applications"]) == 1
        else:
            resp = self.client.list_applications(maxResults=2)
            assert len(resp["applications"]) == 2

            resp = self.client.list_applications(nextToken=resp["nextToken"])
            assert len(resp["applications"]) == 5


class TestStartApplication:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, application_factory):
        self.client = client
        self.application_ids = application_factory

    def test_valid_application_id(self):
        resp = self.client.start_application(applicationId=self.application_ids[1])
        assert resp is not None
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.start_application(applicationId="fake_application_id")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application fake_application_id does not exist"


class TestStopApplication:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, application_factory):
        self.client = client
        self.application_ids = application_factory

    def test_valid_application_id(self):
        resp = self.client.stop_application(applicationId=self.application_ids[1])
        assert resp is not None
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.stop_application(applicationId="fake_application_id")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application fake_application_id does not exist"


class TestUpdateApplication:
    @pytest.fixture(autouse=True)
    def _setup_environment(self, client, application_factory):
        self.client = client
        self.application_ids = application_factory

    @staticmethod
    def get_expected_resp(application_id, extra_configuration):
        response = {
            "applicationId": application_id,
            "name": "test-emr-serverless-application-STOPPED",
            "arn": f"arn:aws:emr-serverless:{DEFAULT_REGION}:{ACCOUNT_ID}:/applications/{application_id}",
            "releaseLabel": "emr-6.6.0",
            "type": "Spark",
            "state": "STOPPED",
            "stateDetails": "",
            "autoStartConfiguration": {"enabled": True},
            "autoStopConfiguration": {"enabled": True, "idleTimeoutMinutes": 15},
            "tags": {},
            "createdAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
            "updatedAt": (
                datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .replace(tzinfo=timezone.utc)
            ),
        }
        return {**response, **extra_configuration}

    @pytest.mark.parametrize(
        "index,status,expectation",
        argvalues=(
            [
                (0, "STARTED", pytest.raises(ClientError)),
                (1, "STOPPED", does_not_raise()),
            ]
            if settings.TEST_SERVER_MODE
            else [
                (0, "STARTED", pytest.raises(ClientError)),
                (1, "STOPPED", does_not_raise()),
                (2, "CREATING", pytest.raises(ClientError)),
                (3, "CREATED", does_not_raise()),
                (4, "STARTING", pytest.raises(ClientError)),
                (5, "STOPPING", pytest.raises(ClientError)),
                (6, "TERMINATED", pytest.raises(ClientError)),
            ]
        ),
    )
    def test_application_status(self, index, status, expectation):
        with expectation as exc:
            resp = self.client.update_application(
                applicationId=self.application_ids[index]
            )

        if exc:
            err = exc.value.response["Error"]
            assert err["Code"] == "ValidationException"
            assert err["Message"] == (
                f"Application {self.application_ids[index]} must be in one "
                "of the following statuses [CREATED, STOPPED]. Current "
                f"status: {status}"
            )
        else:
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    @pytest.mark.parametrize(
        "update_configuration",
        [
            {},
            {
                "initialCapacity": {
                    "Driver": {
                        "workerCount": 1,
                        "workerConfiguration": {
                            "cpu": "2 vCPU",
                            "memory": "4 GB",
                            "disk": "20 GB",
                        },
                    }
                }
            },
            {
                "maximumCapacity": {
                    "cpu": "400 vCPU",
                    "memory": "1024 GB",
                    "disk": "1000 GB",
                }
            },
            {"autoStartConfiguration": {"enabled": False}},
            {
                "autoStopConfiguration": {
                    "enabled": False,
                    "idleTimeoutMinutes": 5,
                }
            },
            {
                "networkConfiguration": {
                    "subnetIds": ["subnet-0123456789abcdefg"],
                    "securityGroupIds": ["sg-0123456789abcdefg"],
                }
            },
            {
                "initialCapacity": {
                    "Driver": {
                        "workerCount": 1,
                        "workerConfiguration": {
                            "cpu": "2 vCPU",
                            "memory": "4 GB",
                            "disk": "20 GB",
                        },
                    }
                },
                "maximumCapacity": {
                    "cpu": "400 vCPU",
                    "memory": "1024 GB",
                    "disk": "1000 GB",
                },
                "autoStartConfiguration": {"enabled": False},
                "autoStopConfiguration": {
                    "enabled": False,
                    "idleTimeoutMinutes": 5,
                },
                "networkConfiguration": {
                    "subnetIds": ["subnet-0123456789abcdefg"],
                    "securityGroupIds": ["sg-0123456789abcdefg"],
                },
            },
        ],
    )
    def test_valid_update(self, update_configuration):
        expected_resp = self.get_expected_resp(
            self.application_ids[1], update_configuration
        )

        actual_resp = self.client.update_application(
            applicationId=self.application_ids[1], **update_configuration
        )["application"]

        assert actual_resp == expected_resp

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.update_application(applicationId="fake_application_id")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application fake_application_id does not exist"


class TestStartJobRun:
    @pytest.fixture(autouse=True)
    def _setup_environment(
        self, client, application_factory, available_application, job_run_factory
    ):
        self.client = client
        self.application_ids: list[str] = application_factory
        self.job_run_lookup: dict[str, list[dict]] = job_run_factory
        self.available_application: str = available_application

    def test_start_job_run(self):
        application_id = self.available_application
        resp = self.client.start_job_run(
            applicationId=application_id,
            executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
            jobDriver={
                "sparkSubmit": {
                    "entryPoint": "test.jar",
                    "entryPointArguments": ["-h"],
                    "sparkSubmitParameters": "--num-executors 1",
                }
            },
            configurationOverrides={
                "monitoringConfiguration": {
                    "s3MonitoringConfiguration": {
                        "logUri": "s3://DOC-EXAMPLE-BUCKET/logs"
                    }
                }
            },
            tags={"tag1": "tag1_val"},
            executionTimeoutMinutes=10,
            name="Test Job Run",
        )

        assert isinstance(resp, dict)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert resp["applicationId"] == application_id
        assert resp["arn"].startswith(
            f"arn:aws:emr-serverless:{DEFAULT_REGION}:{ACCOUNT_ID}:/applications/{application_id}/jobruns/"
        )
        assert re.match(r"[a-z,0-9]{16}", resp["jobRunId"])

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.start_job_run(
                applicationId="fake_application_id",
                executionRoleArn="arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
                jobDriver={
                    "sparkSubmit": {
                        "entryPoint": "test.jar",
                        "entryPointArguments": ["-h"],
                        "sparkSubmitParameters": "--num-executors 1",
                    }
                },
            )

            err = exc.value.response["Error"]
            assert err["Code"] == "ResourceNotFoundException"
            assert err["Message"] == "Application fake_application_id does not exist"

    def test_cross_account_role(self):
        with pytest.raises(ClientError) as exc:
            different_account_id = "999999999999"
            self.client.start_job_run(
                applicationId=self.application_ids[0],
                executionRoleArn=f"arn:aws:iam::{different_account_id}:role/emr-serverless-role",
                jobDriver={
                    "sparkSubmit": {
                        "entryPoint": "test.jar",
                        "entryPointArguments": ["-h"],
                        "sparkSubmitParameters": "--num-executors 1",
                    }
                },
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "AccessDeniedException"
        assert err["Message"] == "Cross-account pass role is not allowed."

    def test_run_timeout(self):
        with pytest.raises(ClientError) as exc:
            self.client.start_job_run(
                applicationId=self.application_ids[0],
                executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/emr-serverless-role",
                jobDriver={
                    "sparkSubmit": {
                        "entryPoint": "test.jar",
                        "entryPointArguments": ["-h"],
                        "sparkSubmitParameters": "--num-executors 1",
                    }
                },
                executionTimeoutMinutes=4,
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert err["Message"] == "RunTimeout must be at least 5 minutes."


class TestGetJobRun:
    @pytest.fixture(autouse=True)
    def _setup_environment(
        self, client, application_factory, available_application, job_run_factory
    ):
        self.client = client
        self.application_ids: list[str] = application_factory
        self.job_run_lookup: dict[str, list[dict]] = job_run_factory
        self.available_application: str = available_application

    def test_job_not_belongs_to_other_application(self):
        app_1_id, app_2_id, *_ = self.job_run_lookup.keys()
        app_2_job_run_ids = self.job_run_lookup[app_2_id]
        for run_id in app_2_job_run_ids:
            # Use application 1 ID and job run from application 2
            with pytest.raises(ClientError) as exc:
                _ = self.client.get_job_run(applicationId=app_1_id, jobRunId=run_id)
            err = exc.value.response["Error"]
            assert err["Code"] == "ResourceNotFoundException"

    def test_get_job_run(self):
        for app_id, run_ids in self.job_run_lookup.items():
            for run_id in run_ids:
                resp = self.client.get_job_run(applicationId=app_id, jobRunId=run_id)
                assert resp is not None
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
                assert resp["jobRun"]["applicationId"] == app_id
                assert resp["jobRun"]["jobRunId"] == run_id

    def test_invalid_application_id(self):
        for _, run_ids in self.job_run_lookup.items():
            fake_app_id = "fakeapp"
            for run_id in run_ids:
                with pytest.raises(ClientError) as exc:
                    self.client.get_job_run(applicationId=fake_app_id, jobRunId=run_id)
                err = exc.value.response["Error"]
                assert err["Code"] == "ResourceNotFoundException"

    def test_invalid_job_run_id(self):
        for app_id, _ in self.job_run_lookup.items():
            job_run_id = "fakejobrun"
            with pytest.raises(ClientError) as exc:
                self.client.get_job_run(applicationId=app_id, jobRunId=job_run_id)
            err = exc.value.response["Error"]
            assert err["Code"] == "ResourceNotFoundException"


class TestListJobRun:
    @pytest.fixture(autouse=True)
    def _setup_environment(
        self, client, application_factory, available_application, job_run_factory
    ):
        self.client = client
        self.application_ids: list[str] = application_factory
        self.job_run_lookup: dict[str, list[dict]] = job_run_factory
        self.available_application: str = available_application

    def test_list_job_runs(self):
        for app_id, run_ids in self.job_run_lookup.items():
            resp = self.client.list_job_runs(applicationId=app_id)
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert len(resp["jobRuns"]) == len(run_ids)
            assert all(run["applicationId"] == app_id for run in resp["jobRuns"])
            assert all(run["id"] in run_ids for run in resp["jobRuns"])

    def test_invalid_application_id(self):
        fake_app_id = "fakeapp"
        with pytest.raises(ClientError) as exc:
            self.client.list_job_runs(applicationId=fake_app_id)
        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"

    def test_application_states(self):
        for app_id, run_ids in self.job_run_lookup.items():
            resp = self.client.list_job_runs(applicationId=app_id, states=["COMPLETED"])
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert all(run["applicationId"] == app_id for run in resp["jobRuns"])
            assert all(
                run["id"] in run_ids
                for run in resp["jobRuns"]
                if run["state"] == "COMPLETED"
            )

    def test_created_filters(self):
        for app_id, _ in self.job_run_lookup.items():
            resp = self.client.list_job_runs(
                applicationId=app_id,
                createdAtAfter=datetime(2024, 1, 1),
                createdAtBefore=datetime(2024, 1, 2),
            )
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert len(resp["jobRuns"]) == 0

    def test_created_after(self):
        for app_id, run_ids in self.job_run_lookup.items():
            resp = self.client.list_job_runs(
                applicationId=app_id, createdAtAfter=datetime(2024, 1, 1)
            )
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert len(resp["jobRuns"]) == len(run_ids)

    def test_max_results(self):
        for app_id, _ in self.job_run_lookup.items():
            resp = self.client.list_job_runs(applicationId=app_id, maxResults=1)
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
            assert len(resp["jobRuns"]) == 1

    def test_invalid_job_run_id(self):
        for app_id, _ in self.job_run_lookup.items():
            job_run_id = "fakejobrun"
            with pytest.raises(ClientError) as exc:
                self.client.cancel_job_run(applicationId=app_id, jobRunId=job_run_id)
            err = exc.value.response["Error"]
            assert err["Code"] == "ResourceNotFoundException"


class TestCancelJobRun:
    @pytest.fixture(autouse=True)
    def _setup_environment(
        self, client, application_factory, available_application, job_run_factory
    ):
        self.client = client
        self.application_ids: list[str] = application_factory
        self.job_run_lookup: dict[str, list[dict]] = job_run_factory
        self.available_application: str = available_application

    def test_cancel_job_run(self):
        for app_id, run_ids in self.job_run_lookup.items():
            for run_id in run_ids:
                resp = self.client.cancel_job_run(applicationId=app_id, jobRunId=run_id)
                assert resp is not None
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
                assert resp["applicationId"] == app_id
                assert resp["jobRunId"] == run_id

    def test_invalid_application_id(self):
        for _, run_ids in self.job_run_lookup.items():
            fake_app_id = "fakeapp"
            for run_id in run_ids:
                with pytest.raises(ClientError) as exc:
                    self.client.get_job_run(applicationId=fake_app_id, jobRunId=run_id)
                err = exc.value.response["Error"]
                assert err["Code"] == "ResourceNotFoundException"

    def test_invalid_job_run_id(self):
        for app_id, _ in self.job_run_lookup.items():
            job_run_id = "fakejobrun"
            with pytest.raises(ClientError) as exc:
                self.client.cancel_job_run(applicationId=app_id, jobRunId=job_run_id)
            err = exc.value.response["Error"]
            assert err["Code"] == "ResourceNotFoundException"
