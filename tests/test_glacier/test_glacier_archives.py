import boto3
import os
import pytest

from moto import mock_glacier
from botocore.exceptions import ClientError


@mock_glacier
def test_upload_archive():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="asdf")

    res = client.upload_archive(
        vaultName="asdf", archiveDescription="my archive", body=b"body of archive"
    )
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201
    headers = res["ResponseMetadata"]["HTTPHeaders"]

    assert "x-amz-archive-id" in headers
    assert "x-amz-sha256-tree-hash" in headers

    assert "checksum" in res
    assert "archiveId" in res


@mock_glacier
def test_upload_zip_archive():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="asdf")

    path = "test.gz"
    with open(os.path.join(os.path.dirname(__file__), path), mode="rb") as archive:
        content = archive.read()

        res = client.upload_archive(vaultName="asdf", body=content)

        assert res["ResponseMetadata"]["HTTPStatusCode"] == 201
        assert "checksum" in res


@mock_glacier
def test_delete_archive():
    client = boto3.client("glacier", region_name="us-west-2")
    client.create_vault(vaultName="asdf")

    archive = client.upload_archive(vaultName="asdf", body=b"body of archive")

    delete = client.delete_archive(vaultName="asdf", archiveId=archive["archiveId"])
    assert delete["ResponseMetadata"]["HTTPStatusCode"] == 204

    with pytest.raises(ClientError) as exc:
        # Not ideal - but this will throw an error if the archive does not exist
        # Which is a good indication that the deletion went through
        client.initiate_job(
            vaultName="myname",
            jobParameters={
                "ArchiveId": archive["archiveId"],
                "Type": "archive-retrieval",
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "VaultNotFound"
