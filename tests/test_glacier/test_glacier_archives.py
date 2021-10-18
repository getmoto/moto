import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_glacier


@mock_glacier
def test_upload_archive():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="asdf")

    res = client.upload_archive(
        vaultName="asdf", archiveDescription="my archive", body=b"body of archive"
    )
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)
    headers = res["ResponseMetadata"]["HTTPHeaders"]

    headers.should.have.key("x-amz-archive-id")
    headers.should.have.key("x-amz-sha256-tree-hash")

    res.should.have.key("checksum")
    res.should.have.key("archiveId")


@mock_glacier
def test_delete_archive():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="asdf")

    archive = client.upload_archive(vaultName="asdf", body=b"body of archive")

    delete = client.delete_archive(vaultName="asdf", archiveId=archive["archiveId"])
    delete["ResponseMetadata"]["HTTPStatusCode"].should.equal(204)

    with pytest.raises(Exception):
        # Not ideal - but this will throw an error if the archvie does not exist
        # Which is a good indication that the deletion went through
        client.initiate_job(
            vaultName="myname",
            jobParameters={
                "ArchiveId": archive["archiveId"],
                "Type": "archive-retrieval",
            },
        )
