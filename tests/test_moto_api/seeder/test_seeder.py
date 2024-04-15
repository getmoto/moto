import unittest

import boto3
import requests

import moto


# https://github.com/getmoto/moto/issues/6592
class TestDifferentAccountsDoesNotBreakSeeding:
    def setup_method(self) -> None:
        if not moto.settings.TEST_DECORATOR_MODE:
            raise unittest.SkipTest(
                "Seed behaviour only needs to be tested in DecoratorMode"
            )
        self.mock = moto.mock_aws()
        self.mock.start()

        requests.post("http://motoapi.amazonaws.com/moto-api/seed?a=42")

        self.sts_client = boto3.client("sts", "us-east-1")
        self.ec2_client = boto3.client("ec2", "us-east-1")

        self.session_client = self.sts_client.assume_role(
            RoleArn="arn:aws:iam::111111111111:role/my-role",
            RoleSessionName="role-session-name",
        )

        self.session = boto3.session.Session(
            aws_access_key_id=self.session_client["Credentials"]["AccessKeyId"],
            aws_secret_access_key=self.session_client["Credentials"]["SecretAccessKey"],
            aws_session_token=self.session_client["Credentials"]["SessionToken"],
        )

    def teardown_method(self) -> None:
        self.mock.stop()

    def test_0(self) -> None:
        # We seeded Moto in the setup-method
        # So our instances should have a fixed InstanceId
        instances = self.ec2_client.run_instances(MaxCount=1, MinCount=1)["Instances"]

        instance_ids = [instance["InstanceId"] for instance in instances]
        assert instance_ids == ["i-73bd4755d05ad7853"]

    def test_1(self) -> None:
        # Create some data in a different account (111111111111)
        self.sts_client.assume_role(
            RoleArn="arn:aws:iam::111111111111:role/my-role",
            RoleSessionName="role-session-name",
        )

    def test_2(self) -> None:
        # The fact that some data now exists in a different account (111111111111)
        # should not change the fixed InstanceId-value
        self.test_0()
