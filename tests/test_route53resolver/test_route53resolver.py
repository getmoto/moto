"""Unit tests for route53resolver-supported APIs."""
import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_route53resolver


@mock_route53resolver
def test_route53resolver_create_resolver_endpoint():
    """Test input/output of the create_resolver_endpoint API."""
    # do test
    pass
