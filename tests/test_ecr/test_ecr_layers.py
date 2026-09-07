import hashlib

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

ECR_REGION = "us-east-1"
ECR_REPO = "test-repo"


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


@mock_aws
def test_layer_upload_flow():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    # initiate
    initiated = client.initiate_layer_upload(repositoryName=ECR_REPO)
    upload_id = initiated["uploadId"]
    assert upload_id
    assert initiated["partSize"] > 0

    # upload a single part
    blob = b"a-fake-image-layer"
    part = client.upload_layer_part(
        repositoryName=ECR_REPO,
        uploadId=upload_id,
        partFirstByte=0,
        partLastByte=len(blob) - 1,
        layerPartBlob=blob,
    )
    assert part["uploadId"] == upload_id
    assert part["repositoryName"] == ECR_REPO
    assert part["registryId"] == ACCOUNT_ID
    assert part["lastByteReceived"] == len(blob) - 1

    # complete
    expected_digest = _sha256(blob)
    completed = client.complete_layer_upload(
        repositoryName=ECR_REPO,
        uploadId=upload_id,
        layerDigests=[expected_digest],
    )
    assert completed["layerDigest"] == expected_digest
    assert completed["uploadId"] == upload_id
    assert completed["registryId"] == ACCOUNT_ID

    # the layer is now available
    availability = client.batch_check_layer_availability(
        repositoryName=ECR_REPO, layerDigests=[expected_digest]
    )
    assert availability["failures"] == []
    assert len(availability["layers"]) == 1
    layer = availability["layers"][0]
    assert layer["layerDigest"] == expected_digest
    assert layer["layerAvailability"] == "AVAILABLE"
    assert layer["layerSize"] == len(blob)
    assert layer["mediaType"]


@mock_aws
def test_layer_upload_multiple_parts():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    upload_id = client.initiate_layer_upload(repositoryName=ECR_REPO)["uploadId"]

    part1 = b"first-part-"
    part2 = b"second-part"
    client.upload_layer_part(
        repositoryName=ECR_REPO,
        uploadId=upload_id,
        partFirstByte=0,
        partLastByte=len(part1) - 1,
        layerPartBlob=part1,
    )
    last = client.upload_layer_part(
        repositoryName=ECR_REPO,
        uploadId=upload_id,
        partFirstByte=len(part1),
        partLastByte=len(part1) + len(part2) - 1,
        layerPartBlob=part2,
    )
    assert last["lastByteReceived"] == len(part1) + len(part2) - 1

    completed = client.complete_layer_upload(
        repositoryName=ECR_REPO,
        uploadId=upload_id,
        layerDigests=[_sha256(part1 + part2)],
    )
    assert completed["layerDigest"] == _sha256(part1 + part2)


@mock_aws
def test_batch_check_layer_availability_missing_and_invalid():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    missing = "sha256:" + "a" * 64
    invalid = "not-a-valid-digest"
    result = client.batch_check_layer_availability(
        repositoryName=ECR_REPO, layerDigests=[missing, invalid]
    )
    assert result["layers"] == []
    codes = {f["layerDigest"]: f["failureCode"] for f in result["failures"]}
    assert codes[missing] == "MissingLayerDigest"
    assert codes[invalid] == "InvalidLayerDigest"


@mock_aws
def test_upload_layer_part_unknown_upload():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    with pytest.raises(ClientError) as exc:
        client.upload_layer_part(
            repositoryName=ECR_REPO,
            uploadId="does-not-exist",
            partFirstByte=0,
            partLastByte=1,
            layerPartBlob=b"xx",
        )
    assert exc.value.response["Error"]["Code"] == "UploadNotFoundException"


@mock_aws
def test_complete_layer_upload_unknown_upload():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    with pytest.raises(ClientError) as exc:
        client.complete_layer_upload(
            repositoryName=ECR_REPO,
            uploadId="does-not-exist",
            layerDigests=["sha256:" + "b" * 64],
        )
    assert exc.value.response["Error"]["Code"] == "UploadNotFoundException"


@mock_aws
def test_initiate_layer_upload_unknown_repository():
    client = boto3.client("ecr", region_name=ECR_REGION)

    with pytest.raises(ClientError) as exc:
        client.initiate_layer_upload(repositoryName="does-not-exist")
    assert exc.value.response["Error"]["Code"] == "RepositoryNotFoundException"
