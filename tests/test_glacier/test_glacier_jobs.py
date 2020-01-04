from __future__ import unicode_literals

import json
import time

from boto.glacier.layer1 import Layer1
import sure  # noqa

from moto import mock_glacier_deprecated


@mock_glacier_deprecated
def test_init_glacier_job():
    conn = Layer1(region_name="us-west-2")
    vault_name = "my_vault"
    conn.create_vault(vault_name)
    archive_id = conn.upload_archive(
        vault_name, "some stuff", "", "", "some description"
    )

    job_response = conn.initiate_job(
        vault_name, {"ArchiveId": archive_id, "Type": "archive-retrieval"}
    )
    job_id = job_response["JobId"]
    job_response["Location"].should.equal("//vaults/my_vault/jobs/{0}".format(job_id))


@mock_glacier_deprecated
def test_describe_job():
    conn = Layer1(region_name="us-west-2")
    vault_name = "my_vault"
    conn.create_vault(vault_name)
    archive_id = conn.upload_archive(
        vault_name, "some stuff", "", "", "some description"
    )
    job_response = conn.initiate_job(
        vault_name, {"ArchiveId": archive_id, "Type": "archive-retrieval"}
    )
    job_id = job_response["JobId"]

    job = conn.describe_job(vault_name, job_id)
    joboutput = json.loads(job.read().decode("utf-8"))

    joboutput.should.have.key("Tier").which.should.equal("Standard")
    joboutput.should.have.key("StatusCode").which.should.equal("InProgress")
    joboutput.should.have.key("VaultARN").which.should.equal(
        "arn:aws:glacier:us-west-2:012345678901:vaults/my_vault"
    )


@mock_glacier_deprecated
def test_list_glacier_jobs():
    conn = Layer1(region_name="us-west-2")
    vault_name = "my_vault"
    conn.create_vault(vault_name)
    archive_id1 = conn.upload_archive(
        vault_name, "some stuff", "", "", "some description"
    )["ArchiveId"]
    archive_id2 = conn.upload_archive(
        vault_name, "some other stuff", "", "", "some description"
    )["ArchiveId"]

    conn.initiate_job(
        vault_name, {"ArchiveId": archive_id1, "Type": "archive-retrieval"}
    )
    conn.initiate_job(
        vault_name, {"ArchiveId": archive_id2, "Type": "archive-retrieval"}
    )

    jobs = conn.list_jobs(vault_name)
    len(jobs["JobList"]).should.equal(2)


@mock_glacier_deprecated
def test_get_job_output():
    conn = Layer1(region_name="us-west-2")
    vault_name = "my_vault"
    conn.create_vault(vault_name)
    archive_response = conn.upload_archive(
        vault_name, "some stuff", "", "", "some description"
    )
    archive_id = archive_response["ArchiveId"]
    job_response = conn.initiate_job(
        vault_name, {"ArchiveId": archive_id, "Type": "archive-retrieval"}
    )
    job_id = job_response["JobId"]

    time.sleep(6)

    output = conn.get_job_output(vault_name, job_id)
    output.read().decode("utf-8").should.equal("some stuff")
