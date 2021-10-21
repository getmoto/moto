"""Unit tests for emrcontainers-supported APIs."""
import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_emrcontainers
from boto3 import Session


from moto.emrcontainers import REGION as DEFAULT_REGION

REGION = Session().region_name or DEFAULT_REGION


@mock_emrcontainers
def test_list():
    """Test input/output of the list API."""
    # do test
    pass


@mock_emrcontainers
def test_create_virtual_cluster_generates_valid_cluster_arn():
    conn = boto3.client("emr-containers", region_name="us-east-1")

    resp = conn.create_virtual_cluster(
        name="string",
        containerProvider={
            "type": "EKS",
            "id": "string",
            "info": {"eksInfo": {"namespace": "string"}},
        },
        clientToken="string",
        tags={"string": "string"},
    )
    assert resp == "foo"
