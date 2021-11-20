"""Unit tests for glue-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ParamValidationError

from moto import mock_glue


@mock_glue
def test_create_job():
    client = boto3.client("glue", region_name="us-east-1")
    response = client.create_job(
        Name="test_name", Role="test_role", Command=dict(Name="test_command")
    )
    assert response["Name"] == "test_name"


@mock_glue
def test_create_job_default_argument_not_provided():
    client = boto3.client("glue", region_name="us-east-1")
    with pytest.raises(ParamValidationError) as exc:
        client.create_job(Role="test_role", Command=dict(Name="test_command"))

    exc.value.kwargs["report"].should.equal(
        'Missing required parameter in input: "Name"'
    )
