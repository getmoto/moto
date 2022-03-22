"""
Ensure that the responses module plays nice with our mocks
"""

import boto3
import requests
import responses
from moto import mock_s3, settings
from unittest import SkipTest, TestCase


class TestResponsesModule(TestCase):
    def setUp(self):
        if settings.TEST_SERVER_MODE:
            raise SkipTest("No point in testing responses-decorator in ServerMode")

    @mock_s3
    @responses.activate
    def test_moto_first(self):

        """
        Verify we can activate a user-defined `responses` on top of our Moto mocks
        """
        self.moto_responses_compatibility()

    @responses.activate
    @mock_s3
    def test_moto_second(self):
        """
        Verify we can load Moto after activating a `responses`-mock
        """
        self.moto_responses_compatibility()

    def moto_responses_compatibility(self):
        responses.add(
            responses.GET, url="http://127.0.0.1/lkdsfjlkdsa", json={"a": "4"}
        )
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="mybucket")
        s3.put_object(Bucket="mybucket", Key="name", Body="value")
        s3.get_object(Bucket="mybucket", Key="name")["Body"].read()
        with requests.get("http://127.0.0.1/lkdsfjlkdsa") as r:
            assert r.json() == {"a": "4"}

    @responses.activate
    def test_moto_as_late_as_possible(self):
        """
        Verify we can load moto after registering a response
        """
        responses.add(
            responses.GET, url="http://127.0.0.1/lkdsfjlkdsa", json={"a": "4"}
        )
        with mock_s3():
            s3 = boto3.client("s3")
            s3.create_bucket(Bucket="mybucket")
            s3.put_object(Bucket="mybucket", Key="name", Body="value")
            # This mock exists within Moto
            with requests.get("http://127.0.0.1/lkdsfjlkdsa") as r:
                assert r.json() == {"a": "4"}

        # And outside of Moto
        with requests.get("http://127.0.0.1/lkdsfjlkdsa") as r:
            assert r.json() == {"a": "4"}
