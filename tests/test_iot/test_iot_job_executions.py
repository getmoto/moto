import boto3
import json
import pytest

from botocore.exceptions import ClientError
from moto import mock_iot


@mock_iot
def test_describe_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    job_execution = client.describe_job_execution(jobId=job_id, thingName=name)
    job_execution.should.have.key("execution")
    job_execution["execution"].should.have.key("jobId").which.should.equal(job_id)
    job_execution["execution"].should.have.key("status").which.should.equal("QUEUED")
    job_execution["execution"].should.have.key("forceCanceled").which.should.equal(
        False
    )
    job_execution["execution"].should.have.key("statusDetails").which.should.equal(
        {"detailsMap": {}}
    )
    job_execution["execution"].should.have.key("thingArn").which.should.equal(
        thing["thingArn"]
    )
    job_execution["execution"].should.have.key("queuedAt")
    job_execution["execution"].should.have.key("startedAt")
    job_execution["execution"].should.have.key("lastUpdatedAt")
    job_execution["execution"].should.have.key("executionNumber").which.should.equal(
        123
    )
    job_execution["execution"].should.have.key("versionNumber").which.should.equal(123)
    job_execution["execution"].should.have.key(
        "approximateSecondsBeforeTimedOut"
    ).which.should.equal(123)

    job_execution = client.describe_job_execution(
        jobId=job_id, thingName=name, executionNumber=123
    )
    job_execution.should.have.key("execution")
    job_execution["execution"].should.have.key("jobId").which.should.equal(job_id)
    job_execution["execution"].should.have.key("status").which.should.equal("QUEUED")
    job_execution["execution"].should.have.key("forceCanceled").which.should.equal(
        False
    )
    job_execution["execution"].should.have.key("statusDetails").which.should.equal(
        {"detailsMap": {}}
    )
    job_execution["execution"].should.have.key("thingArn").which.should.equal(
        thing["thingArn"]
    )
    job_execution["execution"].should.have.key("queuedAt")
    job_execution["execution"].should.have.key("startedAt")
    job_execution["execution"].should.have.key("lastUpdatedAt")
    job_execution["execution"].should.have.key("executionNumber").which.should.equal(
        123
    )
    job_execution["execution"].should.have.key("versionNumber").which.should.equal(123)
    job_execution["execution"].should.have.key(
        "approximateSecondsBeforeTimedOut"
    ).which.should.equal(123)

    with pytest.raises(ClientError) as exc:
        client.describe_job_execution(jobId=job_id, thingName=name, executionNumber=456)
    error_code = exc.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")


@mock_iot
def test_cancel_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    client.cancel_job_execution(jobId=job_id, thingName=name)
    job_execution = client.describe_job_execution(jobId=job_id, thingName=name)
    job_execution.should.have.key("execution")
    job_execution["execution"].should.have.key("status").which.should.equal("CANCELED")


@mock_iot
def test_delete_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    client.delete_job_execution(jobId=job_id, thingName=name, executionNumber=123)

    with pytest.raises(ClientError) as exc:
        client.describe_job_execution(jobId=job_id, thingName=name, executionNumber=123)
    error_code = exc.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")


@mock_iot
def test_list_job_executions_for_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    job_execution = client.list_job_executions_for_job(jobId=job_id)
    job_execution.should.have.key("executionSummaries")
    job_execution["executionSummaries"][0].should.have.key(
        "thingArn"
    ).which.should.equal(thing["thingArn"])

    job_execution = client.list_job_executions_for_job(jobId=job_id, status="QUEUED")
    job_execution.should.have.key("executionSummaries")
    job_execution["executionSummaries"][0].should.have.key(
        "thingArn"
    ).which.should.equal(thing["thingArn"])


@mock_iot
def test_list_job_executions_for_thing():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    job_execution = client.list_job_executions_for_thing(thingName=name)
    job_execution.should.have.key("executionSummaries")
    job_execution["executionSummaries"][0].should.have.key("jobId").which.should.equal(
        job_id
    )

    job_execution = client.list_job_executions_for_thing(
        thingName=name, status="QUEUED"
    )
    job_execution.should.have.key("executionSummaries")
    job_execution["executionSummaries"][0].should.have.key("jobId").which.should.equal(
        job_id
    )


@mock_iot
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
    executions.should.have.length_of(2)
    res.should.have.key("nextToken")

    res = client.list_job_executions_for_thing(
        thingName=name, maxResults=1, nextToken=res["nextToken"]
    )
    executions = res["executionSummaries"]
    executions.should.have.length_of(1)
    res.should.have.key("nextToken")

    res = client.list_job_executions_for_thing(
        thingName=name, nextToken=res["nextToken"]
    )
    executions = res["executionSummaries"]
    executions.should.have.length_of(7)
    res.shouldnt.have.key("nextToken")
