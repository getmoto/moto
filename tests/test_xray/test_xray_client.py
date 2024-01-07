import os
import sys
from unittest import SkipTest

import aws_xray_sdk.core as xray_core
import aws_xray_sdk.core.patcher as xray_core_patcher
import boto3
import botocore.client
import botocore.endpoint
import requests  # noqa # pylint: disable=all

from moto import mock_aws
from moto.utilities.distutils_version import LooseVersion
from moto.xray import XRaySegment, mock_xray_client
from moto.xray.mock_client import MockEmitter

original_make_api_call = botocore.client.BaseClient._make_api_call
original_encode_headers = botocore.endpoint.Endpoint._encode_headers


original_session_request = requests.Session.request
original_session_prep_request = requests.Session.prepare_request


def check_coverage_status():
    # If the wrong version of the coverage module is loaded, skip this test
    coverage_module = sys.modules.get("coverage")
    # If Coverage is not installed, we're fine
    if not coverage_module:
        return
    coverage_version = LooseVersion(coverage_module.__version__)
    # If we have an old version of Coverage installed, we're fine
    if coverage_version < LooseVersion("5.0.0"):
        return
    # If Coverage is not enabled in this test run, we're fine
    if "COV_CORE_SOURCE" not in os.environ:
        return
    raise SkipTest("Can't run this test with Coverage 5.x")


@mock_aws
def test_xray_dynamo_request_id():
    check_coverage_status()

    # Could be ran in any order, so we need to tell sdk that its been unpatched
    xray_core_patcher._PATCHED_MODULES = set()
    xray_core.patch_all()

    client = boto3.client("dynamodb", region_name="us-east-1")

    with XRaySegment():
        resp = client.list_tables()
        assert "RequestId" in resp["ResponseMetadata"]
        id1 = resp["ResponseMetadata"]["RequestId"]

    with XRaySegment():
        client.list_tables()
        resp = client.list_tables()
        id2 = resp["ResponseMetadata"]["RequestId"]

    assert id1 != id2

    setattr(botocore.client.BaseClient, "_make_api_call", original_make_api_call)
    setattr(botocore.endpoint.Endpoint, "_encode_headers", original_encode_headers)
    setattr(requests.Session, "request", original_session_request)
    setattr(requests.Session, "prepare_request", original_session_prep_request)


def test_xray_dynamo_request_id_with_context_mgr():
    check_coverage_status()

    with mock_xray_client():
        assert isinstance(xray_core.xray_recorder._emitter, MockEmitter)
        with mock_aws():
            # Could be ran in any order, so we need to tell sdk that its been unpatched
            xray_core_patcher._PATCHED_MODULES = set()
            xray_core.patch_all()

            client = boto3.client("dynamodb", region_name="us-east-1")

            with XRaySegment():
                resp = client.list_tables()
                assert "RequestId" in resp["ResponseMetadata"]
                id1 = resp["ResponseMetadata"]["RequestId"]

            with XRaySegment():
                client.list_tables()
                resp = client.list_tables()
                id2 = resp["ResponseMetadata"]["RequestId"]

            assert id1 != id2

            setattr(
                botocore.client.BaseClient, "_make_api_call", original_make_api_call
            )
            setattr(
                botocore.endpoint.Endpoint, "_encode_headers", original_encode_headers
            )
            setattr(requests.Session, "request", original_session_request)
            setattr(requests.Session, "prepare_request", original_session_prep_request)

    # Verify we have unmocked the xray recorder
    assert not isinstance(xray_core.xray_recorder._emitter, MockEmitter)


@mock_xray_client
def test_xray_udp_emitter_patched():
    check_coverage_status()

    # Could be ran in any order, so we need to tell sdk that its been unpatched
    xray_core_patcher._PATCHED_MODULES = set()
    xray_core.patch_all()

    assert isinstance(xray_core.xray_recorder._emitter, MockEmitter)

    setattr(botocore.client.BaseClient, "_make_api_call", original_make_api_call)
    setattr(botocore.endpoint.Endpoint, "_encode_headers", original_encode_headers)
    setattr(requests.Session, "request", original_session_request)
    setattr(requests.Session, "prepare_request", original_session_prep_request)


@mock_xray_client
def test_xray_context_patched():
    check_coverage_status()

    # Could be ran in any order, so we need to tell sdk that its been unpatched
    xray_core_patcher._PATCHED_MODULES = set()
    xray_core.patch_all()

    assert xray_core.xray_recorder._context.context_missing == "LOG_ERROR"

    setattr(botocore.client.BaseClient, "_make_api_call", original_make_api_call)
    setattr(botocore.endpoint.Endpoint, "_encode_headers", original_encode_headers)
    setattr(requests.Session, "request", original_session_request)
    setattr(requests.Session, "prepare_request", original_session_prep_request)
