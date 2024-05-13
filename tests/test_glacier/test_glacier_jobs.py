import time

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_initiate_job():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="myname")

    archive = client.upload_archive(vaultName="myname", body=b"body of archive")

    job = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive["archiveId"], "Type": "archive-retrieval"},
    )
    assert job["ResponseMetadata"]["HTTPStatusCode"] == 202

    headers = job["ResponseMetadata"]["HTTPHeaders"]
    assert "x-amz-job-id" in headers
    # Should be an exact match, but Flask adds 'http' to the start of the Location-header
    assert headers["location"] == "//vaults/myname/jobs/" + headers["x-amz-job-id"]

    # Don't think this is correct - the spec says no body is returned, only headers
    # https://docs.aws.amazon.com/amazonglacier/latest/dev/api-initiate-job-post.html
    assert "jobId" in job
    assert "location" in job


@mock_aws
def test_describe_job():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="myname")

    archive = client.upload_archive(vaultName="myname", body=b"body of archive")

    job = client.initiate_job(
        vaultName="myname",
        jobParameters={"ArchiveId": archive["archiveId"], "Type": "archive-retrieval"},
    )
    job_id = job["jobId"]

    describe = client.describe_job(vaultName="myname", jobId=job_id)
    assert describe["JobId"] == job_id
    assert describe["Action"] == "ArchiveRetrieval"
    assert describe["ArchiveId"] == archive["archiveId"]
    assert (
        describe["VaultARN"] == f"arn:aws:glacier:us-west-2:{ACCOUNT_ID}:vaults/myname"
    )
    assert "CreationDate" in describe
    assert describe["Completed"] is False
    assert describe["StatusCode"] == "InProgress"
    assert describe["ArchiveSizeInBytes"] == 0
    assert describe["InventorySizeInBytes"] == 0
    assert describe["Tier"] == "Standard"


@mock_aws
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
    assert job1["jobId"] in found_jobs
    assert job2["jobId"] in found_jobs

    found_job1 = [j for j in jobs if j["JobId"] == job1["jobId"]][0]
    assert found_job1["ArchiveId"] == archive1["archiveId"]
    found_job2 = [j for j in jobs if j["JobId"] == job2["jobId"]][0]
    assert found_job2["ArchiveId"] == archive2["archiveId"]

    # Verify all jobs follow the correct format
    for job in jobs:
        assert "JobId" in job
        assert "Action" in job
        assert "ArchiveId" in job
        assert "VaultARN" in job
        assert "CreationDate" in job
        assert "ArchiveSizeInBytes" in job
        assert "Completed" in job
        assert "StatusCode" in job
        assert "InventorySizeInBytes" in job
        assert "Tier" in job


@mock_aws
def test_get_job_output():
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

    assert output["status"] == 200
    assert output["contentType"] == "application/octet-stream"
    assert "body" in output

    body = output["body"].read().decode("utf-8")
    assert body == "contents of archive"
