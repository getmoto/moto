"""Unit tests for emrserverless-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_emrserverless
from moto.emrserverless import REGION as DEFAULT_REGION
from moto.emrserverless import RELEASE_LABEL as DEFAULT_RELEASE_LABEL


@pytest.fixture(scope="function")
def client():
    with mock_emrserverless():
        yield boto3.client("emr-serverless", region_name=DEFAULT_REGION)


class TestEmrServerlessApplication:
    @staticmethod
    @mock_emrserverless
    def test_create_application(client):
        resp = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )

        assert resp["name"] == "test-emr-serverless"
        assert sorted(resp.keys()) == sorted(
            ["ResponseMetadata", "applicationId", "name", "arn"]
        )

    @staticmethod
    @mock_emrserverless
    def test_list_applications(client):
        # TODO: Move this to a fixture
        client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        resp = client.list_applications()
        assert len(resp["applications"]) == 1

        app_info = resp["applications"][0]
        for key in ["state", "createdAt", "releaseLabel"]:
            assert key in app_info
        assert "initialCapacity" not in app_info
        assert app_info["state"] == "STARTED"
        assert app_info["releaseLabel"] == DEFAULT_RELEASE_LABEL

    @staticmethod
    @mock_emrserverless
    def test_get_application(client):
        app_info = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        resp = client.get_application(applicationId=app_info["applicationId"])
        assert "initialCapacity" in resp["application"]
        assert "maximumCapacity" in resp["application"]

    @staticmethod
    @mock_emrserverless
    def test_delete_application(client):
        app_info = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        app_id = app_info["applicationId"]
        client.stop_application(applicationId=app_id)

        # App should now be in "stopped" state
        resp = client.get_application(applicationId=app_id)
        assert resp is not None
        assert resp["application"]["state"] == "STOPPED"

        resp = client.delete_application(applicationId=app_id)
        assert resp is not None
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    @staticmethod
    @mock_emrserverless
    def test_delete_unstopped_application(client):
        app_info = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        app_id = app_info["applicationId"]
        with pytest.raises(ClientError) as exc:
            resp = client.delete_application(applicationId=app_id)
            assert resp is not None

        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert "must be in one of the following statuses" in err["Message"]


class TestEmrServerlessJob:
    @staticmethod
    @mock_emrserverless
    def test_create_job_with_invalid_app(client):
        with pytest.raises(ClientError) as exc:
            resp = client.start_job_run(
                applicationId="DOES_NOT_EXIST",
                executionRoleArn="aws:arn:ACCOUNT_ID:somerole",
            )
            assert resp is not None

        err = exc.value.response["Error"]

        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Application DOES_NOT_EXIST does not exist"

    @staticmethod
    @mock_emrserverless
    def test_create_job(client):
        resp = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        assert resp["name"] == "test-emr-serverless"

        resp = client.start_job_run(
            applicationId=resp["applicationId"],
            executionRoleArn="aws:arn:ACCOUNT_ID:somerole",
        )
        assert resp is not None
        assert sorted(resp.keys()) == sorted(
            ["ResponseMetadata", "applicationId", "arn", "jobRunId"]
        )

    @staticmethod
    @mock_emrserverless
    def test_list_jobs(client):
        # TODO: Move this to a fixture
        app_resp = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        assert app_resp is not None
        application_id = app_resp["applicationId"]

        job_resp = client.start_job_run(
            applicationId=application_id,
            executionRoleArn="aws:arn:ACCOUNT_ID:somerole",
        )
        assert job_resp is not None

        list_resp = client.list_job_runs(
            applicationId=application_id,
        )
        assert list_resp is not None
        assert len(list_resp["jobRuns"]) == 1

    @staticmethod
    @mock_emrserverless
    def test_get_job_run(client):
        app_info = client.create_application(
            name="test-emr-serverless", type="SPARK", releaseLabel=DEFAULT_RELEASE_LABEL
        )
        job_resp = client.start_job_run(
            applicationId=app_info["applicationId"],
            executionRoleArn="aws:arn:ACCOUNT_ID:somerole",
        )

        job = client.get_job_run(
            applicationId=app_info["applicationId"], jobRunId=job_resp["jobRunId"]
        )
