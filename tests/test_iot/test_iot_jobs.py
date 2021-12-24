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
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job1.should.have.key("jobId").which.should.equal(job_id)
    job1.should.have.key("jobArn")
    job1.should.have.key("description")

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

    job2.should.have.key("jobId").which.should.equal(job_id + "1")
    job2.should.have.key("jobArn")
    job2.should.have.key("description")

    jobs = client.list_jobs()
    jobs.should.have.key("jobs")
    jobs.should_not.have.key("nextToken")
    jobs["jobs"][0].should.have.key("jobId").which.should.equal(job_id)
    jobs["jobs"][1].should.have.key("jobId").which.should.equal(job_id + "1")


@mock_iot
def test_describe_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("documentSource")
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobArn")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("job").which.should.have.key("targets")
    job.should.have.key("job").which.should.have.key("jobProcessDetails")
    job.should.have.key("job").which.should.have.key("lastUpdatedAt")
    job.should.have.key("job").which.should.have.key("createdAt")
    job.should.have.key("job").which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key("job").which.should.have.key(
        "targetSelection"
    ).which.should.equal("CONTINUOUS")
    job.should.have.key("job").which.should.have.key("presignedUrlConfig")
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("roleArn").which.should.equal(
        "arn:aws:iam::1:role/service-role/iot_job_role"
    )
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("expiresInSec").which.should.equal(123)
    job.should.have.key("job").which.should.have.key(
        "jobExecutionsRolloutConfig"
    ).which.should.have.key("maximumPerMinute").which.should.equal(10)


@mock_iot
def test_describe_job_1():
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
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobArn")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("job").which.should.have.key("targets")
    job.should.have.key("job").which.should.have.key("jobProcessDetails")
    job.should.have.key("job").which.should.have.key("lastUpdatedAt")
    job.should.have.key("job").which.should.have.key("createdAt")
    job.should.have.key("job").which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key("job").which.should.have.key(
        "targetSelection"
    ).which.should.equal("CONTINUOUS")
    job.should.have.key("job").which.should.have.key("presignedUrlConfig")
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("roleArn").which.should.equal(
        "arn:aws:iam::1:role/service-role/iot_job_role"
    )
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("expiresInSec").which.should.equal(123)
    job.should.have.key("job").which.should.have.key(
        "jobExecutionsRolloutConfig"
    ).which.should.have.key("maximumPerMinute").which.should.equal(10)


@mock_iot
def test_delete_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)

    client.delete_job(jobId=job_id)

    client.list_jobs()["jobs"].should.have.length_of(0)


@mock_iot
def test_cancel_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)

    job = client.cancel_job(jobId=job_id, reasonCode="Because", comment="You are")
    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("job").which.should.have.key("status").which.should.equal(
        "CANCELED"
    )
    job.should.have.key("job").which.should.have.key(
        "forceCanceled"
    ).which.should.equal(False)
    job.should.have.key("job").which.should.have.key("reasonCode").which.should.equal(
        "Because"
    )
    job.should.have.key("job").which.should.have.key("comment").which.should.equal(
        "You are"
    )


@mock_iot
def test_get_job_document_with_document_source():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

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

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job_document = client.get_job_document(jobId=job_id)
    job_document.should.have.key("document").which.should.equal("")


@mock_iot
def test_get_job_document_with_document():
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
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job_document = client.get_job_document(jobId=job_id)
    job_document.should.have.key("document").which.should.equal('{"field": "value"}')
