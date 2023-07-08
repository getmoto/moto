import os

import boto3
import uuid
import pytest
import requests

from botocore.exceptions import ClientError
from moto import mock_cognitoidp, settings
from moto.moto_api import recorder
from unittest import TestCase


@mock_cognitoidp
class TestCreateUserPoolWithPredeterminedID(TestCase):
    def _reset_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/reset-recording")
        else:
            recorder.reset_recording()

    def _start_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/start-recording")
        else:
            recorder.start_recording()

    def _stop_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/stop-recording")
        else:
            recorder.stop_recording()

    def _download_recording(self):
        if settings.TEST_SERVER_MODE:
            resp = requests.get(
                "http://localhost:5000/moto-api/recorder/download-recording"
            )
            assert resp.status_code == 200
            return resp.content.decode("utf-8")
        else:
            return recorder.download_recording()

    def _upload_recording(self, logs):
        if settings.TEST_SERVER_MODE:
            requests.post(
                "http://localhost:5000/moto-api/recorder/upload-recording", data=logs
            )
        else:
            recorder.upload_recording(logs)

    def _replay_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/replay-recording")
        else:
            recorder.replay_recording()

    def _set_seed(self, a):
        if settings.TEST_SERVER_MODE:
            requests.post(f"http://localhost:5000/moto-api/seed?a={a}")
        else:
            requests.post(f"http://motoapi.amazonaws.com/moto-api/seed?a={a}")

    def setUp(self) -> None:
        self.client = boto3.client("cognito-idp", "us-west-2")
        self.random_seed = 42

        # start recording
        self._reset_recording()
        self._start_recording()
        # Create UserPool
        name = str(uuid.uuid4())
        value = str(uuid.uuid4())
        self._set_seed(self.random_seed)
        resp = self.client.create_user_pool(
            PoolName=name, LambdaConfig={"PreSignUp": value}
        )
        self.pool_id = resp["UserPool"]["Id"]

        # stop recording
        self._stop_recording()
        # delete user pool
        self.client.delete_user_pool(UserPoolId=self.pool_id)

    def tearDown(self) -> None:
        self._stop_recording()
        try:
            os.remove("moto_recording")
        except:  # noqa: E722 Do not use bare except
            pass

    def test_same_seed(self):
        # replay recording
        self._replay_recording()
        # assert userpool is is the same - it will throw an error if it doesn't exist
        self.client.describe_user_pool(UserPoolId=self.pool_id)

    def test_different_seed(self):
        # set seed to different number
        logs = self._download_recording()
        logs = logs.replace("/seed?a=42", "/seed?a=43")
        self._upload_recording(logs)
        # replay recording, and recreate a userpool
        self._replay_recording()
        # assert the ID of this userpool is now different
        with pytest.raises(ClientError) as exc:
            self.client.describe_user_pool(UserPoolId=self.pool_id)
        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"

        # It is created - just with a different ID
        all_pools = self.client.list_user_pools(MaxResults=5)["UserPools"]
        assert len(all_pools) == 1
