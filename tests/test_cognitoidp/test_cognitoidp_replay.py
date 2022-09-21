import os

import boto3
import uuid
import sure  # noqa # pylint: disable=unused-import
import pytest
import requests

from botocore.exceptions import ClientError
from moto import mock_cognitoidp, mock_iam, settings
from moto.moto_api import mock_random, recorder
from unittest import TestCase


@mock_cognitoidp
@mock_iam
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
            resp.status_code.should.equal(200)
            return resp.content
        else:
            return recorder.download_recording()

    def _replay_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/replay-recording")
        else:
            recorder.replay_recording()

    def _set_seed(self, a):
        if settings.TEST_SERVER_MODE:
            a = requests.post(f"http://localhost:5000/moto-api/seed?a={a}")
        else:
            mock_random.seed(a)

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
        # set seed to same number
        self._set_seed(self.random_seed)
        # replay recording
        self._replay_recording()
        # assert userpool is is the same - it will throw an error if it doesn't exist
        self.client.describe_user_pool(UserPoolId=self.pool_id)

    def test_different_seed(self):
        # set seed to different number
        self._set_seed(self.random_seed + 1)
        # replay recording, and recreate a userpool
        self._replay_recording()
        # assert the ID of this userpool is now different
        with pytest.raises(ClientError) as exc:
            self.client.describe_user_pool(UserPoolId=self.pool_id)
        err = exc.value.response["Error"]
        err["Code"].should.equal("ResourceNotFoundException")

        # It is created - just with a different ID
        all_pools = self.client.list_user_pools(MaxResults=5)["UserPools"]
        all_pools.should.have.length_of(1)
