import boto3
import sure  # noqa # pylint: disable=unused-import
import time

from moto import mock_glacier
from moto.core import ACCOUNT_ID


@mock_glacier
def test_initiate_job():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="myname")

    archive = client.upload_archive(vaultName="myname", body=b"body of archive")

    job = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive["archiveId"], "Type": "archive-retrieval"},
    )
    job["ResponseMetadata"]["HTTPStatusCode"].should.equal(202)

    headers = job["ResponseMetadata"]["HTTPHeaders"]
    headers.should.have.key("x-amz-job-id")
    # Should be an exact match, but Flask adds 'http' to the start of the Location-header
    headers.should.have.key("location").match(
        "//vaults/myname/jobs/" + headers["x-amz-job-id"]
    )

    # Don't think this is correct - the spec says no body is returned, only headers
    # https://docs.aws.amazon.com/amazonglacier/latest/dev/api-initiate-job-post.html
    job.should.have.key("jobId")
    job.should.have.key("location")


@mock_glacier
def test_describe_job_boto3():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="myname")

    archive = client.upload_archive(vaultName="myname", body=b"body of archive")

    job = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive["archiveId"], "Type": "archive-retrieval"},
    )
    job_id = job["jobId"]

    describe = client.describe_job(vaultName="myname", jobId=job_id)
    describe.should.have.key("JobId").equal(job_id)
    describe.should.have.key("Action").equal("ArchiveRetrieval")
    describe.should.have.key("ArchiveId").equal(archive["archiveId"])
    describe.should.have.key("VaultARN").equal(
        f"arn:aws:glacier:us-west-2:{ACCOUNT_ID}:vaults/myname"
    )
    describe.should.have.key("CreationDate")
    describe.should.have.key("Completed").equal(False)
    describe.should.have.key("StatusCode").equal("InProgress")
    describe.should.have.key("ArchiveSizeInBytes").equal(0)
    describe.should.have.key("InventorySizeInBytes").equal(0)
    describe.should.have.key("Tier").equal("Standard")


@mock_glacier
def test_list_jobs():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="myname")

    archive1 = client.upload_archive(vaultName="myname", body=b"first archive")
    archive2 = client.upload_archive(vaultName="myname", body=b"second archive")

    job1 = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive1["archiveId"], "Type": "archive-retrieval"},
    )

    job2 = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive2["archiveId"], "Type": "archive-retrieval"},
    )
    jobs = client.list_jobs(vaultName="myname")["JobList"]

    # Verify the created jobs are in this list
    found_jobs = [j["JobId"] for j in jobs]
    found_jobs.should.contain(job1["jobId"])
    found_jobs.should.contain(job2["jobId"])

    found_job1 = [j for j in jobs if j["JobId"] == job1["jobId"]][0]
    found_job1.should.have.key("ArchiveId").equal(archive1["archiveId"])
    found_job2 = [j for j in jobs if j["JobId"] == job2["jobId"]][0]
    found_job2.should.have.key("ArchiveId").equal(archive2["archiveId"])

    # Verify all jobs follow the correct format
    for job in jobs:
        job.should.have.key("JobId")
        job.should.have.key("Action")
        job.should.have.key("ArchiveId")
        job.should.have.key("VaultARN")
        job.should.have.key("CreationDate")
        job.should.have.key("ArchiveSizeInBytes")
        job.should.have.key("Completed")
        job.should.have.key("StatusCode")
        job.should.have.key("InventorySizeInBytes")
        job.should.have.key("Tier")


@mock_glacier
def test_get_job_output_boto3():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="myname")

    archive = client.upload_archive(vaultName="myname", body=b"contents of archive")

    job = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive["archiveId"], "Type": "archive-retrieval"},
    )

    output = None
    start = time.time()
    while (time.time() - start) < 10:
        try:
            output = client.get_job_output(vaultName="myname", jobId=job["jobId"])
            break
        except Exception:
            time.sleep(1)

    output.shouldnt.be.none
    output.should.have.key("status").equal(200)
    output.should.have.key("contentType").equal("application/octet-stream")
    output.should.have.key("body")

    body = output["body"].read().decode("utf-8")
    body.should.equal("contents of archive")
