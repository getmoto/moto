"""Unit tests for glue-supported APIs."""
from random import randint
from uuid import uuid4

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ParamValidationError

from moto import mock_glue


@mock_glue
def test_create_job():
    client = create_glue_client()
    job_name = str(uuid4())
    response = client.create_job(
        Name=job_name, Role="test_role", Command=dict(Name="test_command")
    )
    assert response["Name"] == job_name


@mock_glue
def test_create_job_default_argument_not_provided():
    client = create_glue_client()
    with pytest.raises(ParamValidationError) as exc:
        client.create_job(Role="test_role", Command=dict(Name="test_command"))

    exc.value.kwargs["report"].should.equal(
        'Missing required parameter in input: "Name"'
    )


@mock_glue
def test_list_jobs():
    client = create_glue_client()
    expected_jobs = randint(1, 15)
    for _ in range(expected_jobs):
        create_test_job(client)
    response = client.list_jobs()
    response["JobNames"].should.have.length_of(expected_jobs)


@mock_glue
def test_list_jobs_with_max_results():
    client = create_glue_client()
    for _ in range(4):
        create_test_job(client)
    response = client.list_jobs(MaxResults=2)
    response["JobNames"].should.have.length_of(2)
    response["NextToken"].should.equal(2)


@mock_glue
def test_list_jobs_from_next_token():
    client = create_glue_client()
    for _ in range(10):
        create_test_job(client)
    response = client.list_jobs(NextToken="7")
    response["JobNames"].should.have.length_of(3)


@mock_glue
def test_list_jobs_with_max_results_greater_than_actual_results():
    client = create_glue_client()
    for _ in range(4):
        create_test_job(client)
    response = client.list_jobs(MaxResults=10)
    response["JobNames"].should.have.length_of(4)
    response["NextToken"].should.equal(4)


@mock_glue
def test_list_jobs_with_tags():
    client = create_glue_client()
    create_test_job(client)
    create_test_job(client, {"string": "string"})
    response = client.list_jobs(Tags={"string": "string"})
    response["JobNames"].should.have.length_of(1)


def create_glue_client():
    return boto3.client("glue", region_name="us-east-1")


def create_test_job(client, tags=None):
    job_name = str(uuid4())
    client.create_job(
        Name=job_name,
        Role="test_role",
        Command=dict(Name="test_command"),
        Tags=tags or {},
    )
