import unittest

import boto3
from moto import mock_s3


@mock_s3
class ClassDecoratorTest(unittest.TestCase):
    """
    https://github.com/getmoto/moto/issues/3535
    An update to the mock-package introduced a failure during teardown.
    This test is in place to catch any similar failures with our
    mocking approach.
    """

    def test_instantiation_succeeds(self):
        assert boto3.client("s3", region_name="us-east-1") is not None
