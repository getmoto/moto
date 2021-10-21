"""Unit tests for emrcontainers-supported APIs."""
import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_emrcontainers


@mock_emrcontainers
def test_list():
    """Test input/output of the list API."""
    # do test
    pass