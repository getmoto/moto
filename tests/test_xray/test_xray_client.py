from moto import mock_xray_client, XRaySegment, mock_dynamodb
import sure  # noqa # pylint: disable=unused-import
import boto3

from moto.xray.mock_client import MockEmitter
import aws_xray_sdk.core as xray_core
import aws_xray_sdk.core.patcher as xray_core_patcher

import botocore.client
import botocore.endpoint

original_make_api_call = botocore.client.BaseClient._make_api_call
original_encode_headers = botocore.endpoint.Endpoint._encode_headers

import requests  # noqa # pylint: disable=all

original_session_request = requests.Session.request
original_session_prep_request = requests.Session.prepare_request


@mock_xray_client
@mock_dynamodb
def test_xray_dynamo_request_id():
    # Could be ran in any order, so we need to tell sdk that its been unpatched
    xray_core_patcher._PATCHED_MODULES = set()
    xray_core.patch_all()

    client = boto3.client("dynamodb", region_name="us-east-1")

    with XRaySegment():
        resp = client.list_tables()
        resp["ResponseMetadata"].should.contain("RequestId")
        id1 = resp["ResponseMetadata"]["RequestId"]

    with XRaySegment():
        client.list_tables()
        resp = client.list_tables()
        id2 = resp["ResponseMetadata"]["RequestId"]

    id1.should_not.equal(id2)

    setattr(botocore.client.BaseClient, "_make_api_call", original_make_api_call)
    setattr(botocore.endpoint.Endpoint, "_encode_headers", original_encode_headers)
    setattr(requests.Session, "request", original_session_request)
    setattr(requests.Session, "prepare_request", original_session_prep_request)


def test_xray_dynamo_request_id_with_context_mgr():
    with mock_xray_client():
        assert isinstance(xray_core.xray_recorder._emitter, MockEmitter)
        with mock_dynamodb():
            # Could be ran in any order, so we need to tell sdk that its been unpatched
            xray_core_patcher._PATCHED_MODULES = set()
            xray_core.patch_all()

            client = boto3.client("dynamodb", region_name="us-east-1")

            with XRaySegment():
                resp = client.list_tables()
                resp["ResponseMetadata"].should.contain("RequestId")
                id1 = resp["ResponseMetadata"]["RequestId"]

            with XRaySegment():
                client.list_tables()
                resp = client.list_tables()
                id2 = resp["ResponseMetadata"]["RequestId"]

            id1.should_not.equal(id2)

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
    # Could be ran in any order, so we need to tell sdk that its been unpatched
    xray_core_patcher._PATCHED_MODULES = set()
    xray_core.patch_all()

    xray_core.xray_recorder._context.context_missing.should.equal("LOG_ERROR")

    setattr(botocore.client.BaseClient, "_make_api_call", original_make_api_call)
    setattr(botocore.endpoint.Endpoint, "_encode_headers", original_encode_headers)
    setattr(requests.Session, "request", original_session_request)
    setattr(requests.Session, "prepare_request", original_session_prep_request)
