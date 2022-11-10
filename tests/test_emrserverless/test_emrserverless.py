"""Unit tests for emrserverless-supported APIs."""
import re
from datetime import datetime, timezone
from contextlib import contextmanager

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_emrserverless, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.emrserverless import REGION as DEFAULT_REGION
from moto.emrserverless import RELEASE_LABEL as DEFAULT_RELEASE_LABEL
from unittest.mock import patch


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function", name="client")
def fixture_client():
    with mock_emrserverless():
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


class TestCreateApplication:
    @staticmethod
    @mock_emrserverless
    def test_create_application(client):
        resp = client.create_application(
            name="test-emr-serverless-application",
            type="SPARK",
            releaseLabel=DEFAULT_RELEASE_LABEL,
        )

        assert resp["name"] == "test-emr-serverless-application"
        assert re.match(r"[a-z,0-9]{16}", resp["applicationId"])
        assert (
            resp["arn"]
            == f"arn:aws:emr-containers:us-east-1:{ACCOUNT_ID}:/applications/{resp['applicationId']}"
        )

    @staticmethod
    @mock_emrserverless
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
    @mock_emrserverless
    def test_create_application_incorrect_release_label(client):
        with pytest.raises(ClientError) as exc:
            client.create_application(
                name="test-emr-serverless-application",
                type="SPARK",
                releaseLabel="emr-fake",
            )

        err = exc.value.response["Error"]

        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == "Type 'SPARK' is not supported for release label 'emr-fake' or release label does not exist"
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
            assert (
                err["Message"]
                == f"Application {self.application_ids[index]} must be in one of the following statuses [CREATED, STOPPED]. Current status: {status}"
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
            "arn": f"arn:aws:emr-containers:us-east-1:123456789012:/applications/{application_id}",
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
            "arn": f"arn:aws:emr-containers:us-east-1:123456789012:/applications/{self.application_ids[0]}",
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
            "arn": f"arn:aws:emr-containers:us-east-1:123456789012:/applications/{application_id}",
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
            assert (
                err["Message"]
                == f"Application {self.application_ids[index]} must be in one of the following statuses [CREATED, STOPPED]. Current status: {status}"
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
