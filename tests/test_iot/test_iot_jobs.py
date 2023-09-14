import boto3
import json

from moto import mock_iot


@mock_iot
def test_create_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing# job document
    #     job_document = {
    #         "field": "value"
    #     }
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


@mock_iot
def test_list_jobs():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing# job document
    #     job_document = {
    #         "field": "value"
    #     }
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    # job document
    job_document = {"field": "value"}

    job1 = client.create_job(
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

    assert job1["jobId"] == job_id
    assert "jobArn" in job1
    assert "description" in job1

    job2 = client.create_job(
        jobId=job_id + "1",
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

    assert job2["jobId"] == job_id + "1"
    assert "jobArn" in job2
    assert "description" in job2

    jobs = client.list_jobs()
    assert "jobs" in jobs
    assert "nextToken" not in jobs
    assert jobs["jobs"][0]["jobId"] == job_id
    assert jobs["jobs"][1]["jobId"] == job_id + "1"


@mock_iot
def test_describe_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job

    resp = client.describe_job(jobId=job_id)
    assert "documentSource" in resp

    job = resp["job"]
    assert "jobArn" in job
    assert job["jobId"] == job_id
    assert "targets" in job
    assert "jobProcessDetails" in job
    assert "lastUpdatedAt" in job
    assert "createdAt" in job
    assert "jobExecutionsRolloutConfig" in job
    assert job["targetSelection"] == "CONTINUOUS"
    assert "presignedUrlConfig" in job
    assert (
        job["presignedUrlConfig"]["roleArn"]
        == "arn:aws:iam::1:role/service-role/iot_job_role"
    )
    assert job["presignedUrlConfig"]["expiresInSec"] == 123
    assert job["jobExecutionsRolloutConfig"]["maximumPerMinute"] == 10


@mock_iot
def test_describe_job_1():
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
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job

    job = client.describe_job(jobId=job_id)["job"]
    assert "jobArn" in job
    assert job["jobId"] == job_id
    assert "targets" in job
    assert "jobProcessDetails" in job
    assert "lastUpdatedAt" in job
    assert "createdAt" in job
    assert job["targetSelection"] == "CONTINUOUS"
    assert (
        job["presignedUrlConfig"]["roleArn"]
        == "arn:aws:iam::1:role/service-role/iot_job_role"
    )
    assert job["presignedUrlConfig"]["expiresInSec"] == 123
    assert job["jobExecutionsRolloutConfig"]["maximumPerMinute"] == 10


@mock_iot
def test_delete_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job

    job = client.describe_job(jobId=job_id)["job"]
    assert job["jobId"] == job_id

    client.delete_job(jobId=job_id)

    assert client.list_jobs()["jobs"] == []


@mock_iot
def test_cancel_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job

    job = client.describe_job(jobId=job_id)["job"]
    assert job["jobId"] == job_id

    job = client.cancel_job(jobId=job_id, reasonCode="Because", comment="You are")
    assert job["jobId"] == job_id
    assert "jobArn" in job

    job = client.describe_job(jobId=job_id)["job"]
    assert job["jobId"] == job_id
    assert job["status"] == "CANCELED"
    assert job["forceCanceled"] is False
    assert job["reasonCode"] == "Because"
    assert job["comment"] == "You are"


@mock_iot
def test_get_job_document_with_document_source():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job

    job_document = client.get_job_document(jobId=job_id)
    assert job_document["document"] == ""


@mock_iot
def test_get_job_document_with_document():
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
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    assert job["jobId"] == job_id
    assert "jobArn" in job

    job_document = client.get_job_document(jobId=job_id)
    assert job_document["document"] == '{"field": "value"}'
