"""Unit tests for apigatewaymanagementapi-supported APIs."""
import boto3

from moto import mock_apigatewaymanagementapi, settings
from moto.core.versions import is_werkzeug_2_3_x
from moto.apigatewaymanagementapi.models import apigatewaymanagementapi_backends
from tests import DEFAULT_ACCOUNT_ID
from unittest import SkipTest

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_apigatewaymanagementapi
def test_delete_connection():
    if settings.TEST_SERVER_MODE and not is_werkzeug_2_3_x():
        # URL matching changed between 2.2.x and 2.3.x
        # 2.3.x has no problem matching the root path '/@connections', but 2.2.x refuses
        raise SkipTest("Can't test this in older werkzeug versions")
    client = boto3.client("apigatewaymanagementapi", region_name="eu-west-1")
    # NO-OP
    client.delete_connection(ConnectionId="anything")


@mock_apigatewaymanagementapi
def test_get_connection():
    if settings.TEST_SERVER_MODE and not is_werkzeug_2_3_x():
        # URL matching changed between 2.2.x and 2.3.x
        # 2.3.x has no problem matching the root path '/@connections', but 2.2.x refuses
        raise SkipTest("Can't test this in older werkzeug versions")
    client = boto3.client("apigatewaymanagementapi", region_name="us-east-2")
    conn = client.get_connection(ConnectionId="anything")

    assert "ConnectedAt" in conn
    assert conn["Identity"] == {"SourceIp": "192.168.0.1", "UserAgent": "Moto Mocks"}
    assert "LastActiveAt" in conn


@mock_apigatewaymanagementapi
def test_post_to_connection():
    if settings.TEST_SERVER_MODE and not is_werkzeug_2_3_x():
        # URL matching changed between 2.2.x and 2.3.x
        # 2.3.x has no problem matching the root path '/@connections', but 2.2.x refuses
        raise SkipTest("Can't test this in older werkzeug versions")
    client = boto3.client("apigatewaymanagementapi", region_name="ap-southeast-1")
    client.post_to_connection(ConnectionId="anything", Data=b"my first bytes")

    if not settings.TEST_SERVER_MODE:
        backend = apigatewaymanagementapi_backends[DEFAULT_ACCOUNT_ID]["ap-southeast-1"]
        assert backend.connections["anything"].data == b"my first bytes"

    client.post_to_connection(ConnectionId="anything", Data=b"more bytes")

    if not settings.TEST_SERVER_MODE:
        backend = apigatewaymanagementapi_backends[DEFAULT_ACCOUNT_ID]["ap-southeast-1"]
        assert backend.connections["anything"].data == b"my first bytesmore bytes"
