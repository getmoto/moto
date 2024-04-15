import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_describe_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job
    assert "description" in job

    job_execution = client.describe_job_execution(jobId=job_id, thingName=name)
    assert job_execution["execution"]["jobId"] == job_id
    assert job_execution["execution"]["status"] == "QUEUED"
    assert job_execution["execution"]["forceCanceled"] is False
    assert job_execution["execution"]["statusDetails"] == {"detailsMap": {}}
    assert job_execution["execution"]["thingArn"] == thing["thingArn"]
    assert "queuedAt" in job_execution["execution"]
    assert "startedAt" in job_execution["execution"]
    assert "lastUpdatedAt" in job_execution["execution"]
    assert job_execution["execution"]["executionNumber"] == 123
    assert job_execution["execution"]["versionNumber"] == 123
    assert job_execution["execution"]["approximateSecondsBeforeTimedOut"] == 123

    job_execution = client.describe_job_execution(
        jobId=job_id, thingName=name, executionNumber=123
    )
    assert "execution" in job_execution
    assert job_execution["execution"]["jobId"] == job_id
    assert job_execution["execution"]["status"] == "QUEUED"
    assert job_execution["execution"]["forceCanceled"] is False
    assert job_execution["execution"]["statusDetails"] == {"detailsMap": {}}
    assert job_execution["execution"]["thingArn"] == thing["thingArn"]
    assert "queuedAt" in job_execution["execution"]
    assert "startedAt" in job_execution["execution"]
    assert "lastUpdatedAt" in job_execution["execution"]
    assert job_execution["execution"]["executionNumber"] == 123
    assert job_execution["execution"]["versionNumber"] == 123
    assert job_execution["execution"]["approximateSecondsBeforeTimedOut"] == 123

    with pytest.raises(ClientError) as exc:
        client.describe_job_execution(jobId=job_id, thingName=name, executionNumber=456)
    error_code = exc.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"


@mock_aws
def test_cancel_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job
    assert "description" in job

    client.cancel_job_execution(jobId=job_id, thingName=name)
    job_execution = client.describe_job_execution(jobId=job_id, thingName=name)
    assert "execution" in job_execution
    assert job_execution["execution"]["status"] == "CANCELED"


@mock_aws
def test_delete_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job
    assert "description" in job

    client.delete_job_execution(jobId=job_id, thingName=name, executionNumber=123)

    with pytest.raises(ClientError) as exc:
        client.describe_job_execution(jobId=job_id, thingName=name, executionNumber=123)
    error_code = exc.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"


@mock_aws
def test_list_job_executions_for_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job
    assert "description" in job

    job_execution = client.list_job_executions_for_job(jobId=job_id)
    assert job_execution["executionSummaries"][0]["thingArn"] == thing["thingArn"]

    job_execution = client.list_job_executions_for_job(jobId=job_id, status="QUEUED")
    assert job_execution["executionSummaries"][0]["thingArn"] == thing["thingArn"]


@mock_aws
def test_list_job_executions_for_thing():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job
    assert "description" in job

    job_execution = client.list_job_executions_for_thing(thingName=name)
    assert job_execution["executionSummaries"][0]["jobId"] == job_id

    job_execution = client.list_job_executions_for_thing(
        thingName=name, status="QUEUED"
    )
    assert job_execution["executionSummaries"][0]["jobId"] == job_id


@mock_aws
def test_list_job_executions_for_thing_paginated():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    thing = client.create_thing(thingName=name)

    for idx in range(0, 10):
        client.create_job(
            jobId=f"TestJob_{idx}",
            targets=[thing["thingArn"]],
            document=json.dumps({"field": "value"}),
        )

    res = client.list_job_executions_for_thing(thingName=name, maxResults=2)
    executions = res["executionSummaries"]
    assert len(executions) == 2

    res = client.list_job_executions_for_thing(
        thingName=name, maxResults=1, nextToken=res["nextToken"]
    )
    executions = res["executionSummaries"]
    assert len(executions) == 1

    res = client.list_job_executions_for_thing(
        thingName=name, nextToken=res["nextToken"]
    )
    executions = res["executionSummaries"]
    assert len(executions) == 7
    assert "nextToken" not in res
