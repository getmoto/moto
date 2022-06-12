"""Unit tests for emrserverless-supported APIs."""
import contextlib
import re
from datetime import datetime, timezone
from unittest import SkipTest
from contextlib import nullcontext as does_not_raise


import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_emrserverless, settings
from moto.core import ACCOUNT_ID
from moto.emrserverless import REGION as DEFAULT_REGION
from moto.emrserverless import RELEASE_LABEL as DEFAULT_RELEASE_LABEL
from unittest.mock import patch


@pytest.fixture(scope="function")
def client():
    with mock_emrserverless():
        yield boto3.client("emr-serverless", region_name=DEFAULT_REGION)


@pytest.fixture(scope="function")
def application_factory(client):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    application_state = [
        "CREATING",
        "CREATED",
        "STARTING",
        "STARTED",
        "STOPPING",
        "STOPPED",
        "TERMINATED",
    ]

    application_list = []
    for state in application_state:
        with patch("moto.emrserverless.models.APPLICATION_STATUS", state):
            resp = client.create_application(
                name=f"test-emr-serverless-application-{state}",
                type="SPARK",
                releaseLabel=DEFAULT_RELEASE_LABEL,
            )

            application_list.append(resp["applicationId"])

    yield application_list


@pytest.fixture(scope="function")
def base_application(client):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    with patch("moto.emrserverless.models.APPLICATION_STATUS", "CREATED"):
        resp = client.create_application(
            name="test-emr-serverless-application",
            type="SPARK",
            releaseLabel=DEFAULT_RELEASE_LABEL,
        )

    yield resp["applicationId"]


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
        [
            (0, "CREATING", pytest.raises(ClientError)),
            (1, "CREATED", does_not_raise()),
            (2, "STARTING", pytest.raises(ClientError)),
            (3, "STARTED", pytest.raises(ClientError)),
            (4, "STOPPING", pytest.raises(ClientError)),
            (5, "STOPPED", does_not_raise()),
            (6, "TERMINATED", pytest.raises(ClientError)),
        ],
    )
    def test_valid_application_id(self, index, status, expectation):
        with expectation as exc:
            resp = self.client.delete_application(
                applicationId=self.application_ids[index]
            )

        if type(expectation) == contextlib.nullcontext:
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        else:
            err = exc.value.response["Error"]
            assert err["Code"] == "ValidationException"
            assert (
                err["Message"]
                == f"Application {self.application_ids[index]} must be in one of the following statuses [CREATED, STOPPED]. Current status: {status}"
            )

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
            "id": self.application_ids[1],
            "name": "test-emr-serverless-application-CREATED",
            "arn": f"arn:aws:emr-containers:us-east-1:123456789012:/applications/{self.application_ids[1]}",
            "releaseLabel": "emr-6.6.0",
            "type": "Spark",
            "state": "CREATED",
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

        assert resp["applications"][0] == expected_resp

    @pytest.mark.parametrize(
        "list_applications_args,job_count",
        [
            ({}, 7),
            ({"states": ["CREATED"]}, 1),
            ({"states": ["CREATED", "STARTING"]}, 2),
            ({"states": ["FOOBAA"]}, 0),
            ({"maxResults": 1}, 1),
        ],
    )
    def test_filtering(self, list_applications_args, job_count):
        resp = self.client.list_applications(**list_applications_args)
        assert len(resp["applications"]) == job_count

    def test_next_token(self):
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
            "name": "test-emr-serverless-application",
            "arn": f"arn:aws:emr-containers:us-east-1:123456789012:/applications/{application_id}",
            "releaseLabel": "emr-6.6.0",
            "type": "Spark",
            "state": "CREATED",
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
        [
            (0, "CREATING", pytest.raises(ClientError)),
            (1, "CREATED", does_not_raise()),
            (2, "STARTING", pytest.raises(ClientError)),
            (3, "STARTED", pytest.raises(ClientError)),
            (4, "STOPPING", pytest.raises(ClientError)),
            (5, "STOPPED", does_not_raise()),
            (6, "TERMINATED", pytest.raises(ClientError)),
        ],
    )
    def test_application_status(self, index, status, expectation):
        with expectation as exc:
            resp = self.client.update_application(
                applicationId=self.application_ids[index]
            )

        if type(expectation) == contextlib.nullcontext:
            assert resp is not None
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        else:
            err = exc.value.response["Error"]
            assert err["Code"] == "ValidationException"
            assert (
                err["Message"]
                == f"Application {self.application_ids[index]} must be in one of the following statuses [CREATED, STOPPED]. Current status: {status}"
            )

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
    def test_valid_update(self, base_application, update_configuration):
        expected_resp = self.get_expected_resp(base_application, update_configuration)

        actual_resp = self.client.update_application(
            applicationId=base_application, **update_configuration
        )["application"]

        assert actual_resp == expected_resp

    def test_invalid_application_id(self):
        with pytest.raises(ClientError) as exc:
            self.client.update_application(applicationId="fake_application_id")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application fake_application_id does not exist"
