import json

import boto3
import pytest

from moto import mock_aws

from .test_ecr_helpers import _create_image_manifest


@pytest.mark.parametrize(
    "image_filter, expected_tags",
    [
        (None, {"latest", "v1", None}),
        ({}, {"latest", "v1", None}),
        ({"tagStatus": "ANY"}, {"latest", "v1", None}),
        ({"tagStatus": "TAGGED"}, {"latest", "v1"}),
        ({"tagStatus": "UNTAGGED"}, {None}),
    ],
)
@mock_aws
def test_list_images_tag_status(image_filter, expected_tags):
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="images")
    manifest = json.dumps(_create_image_manifest())
    tagged = client.put_image(
        repositoryName="images", imageManifest=manifest, imageTag="latest"
    )["image"]["imageId"]["imageDigest"]
    client.put_image(repositoryName="images", imageManifest=manifest, imageTag="v1")
    untagged = client.put_image(
        repositoryName="images", imageManifest=json.dumps(_create_image_manifest())
    )["image"]["imageId"]["imageDigest"]

    kwargs = {"filter": image_filter} if image_filter is not None else {}
    images = client.list_images(repositoryName="images", **kwargs)["imageIds"]

    expected = {(untagged if tag is None else tagged, tag) for tag in expected_tags}
    assert len(images) == len(expected)
    assert {
        (image["imageDigest"], image.get("imageTag")) for image in images
    } == expected
    # Filtering must not mutate the repository's image or tag lists.
    assert len(client.list_images(repositoryName="images")["imageIds"]) == 3


@pytest.mark.parametrize("tag_status", ["TAGGED", "UNTAGGED", "ANY"])
@mock_aws
def test_list_images_tag_status_empty_repository(tag_status):
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="empty")
    client.create_repository(repositoryName="other")
    client.put_image(
        repositoryName="other",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )
    assert (
        client.list_images(repositoryName="empty", filter={"tagStatus": tag_status})[
            "imageIds"
        ]
        == []
    )


@mock_aws
def test_list_images_tag_status_after_tagging_image():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="images")
    manifest = json.dumps(_create_image_manifest())
    digest = client.put_image(repositoryName="images", imageManifest=manifest)["image"][
        "imageId"
    ]["imageDigest"]
    assert (
        client.list_images(repositoryName="images", filter={"tagStatus": "TAGGED"})[
            "imageIds"
        ]
        == []
    )
    assert (
        len(
            client.list_images(
                repositoryName="images", filter={"tagStatus": "UNTAGGED"}
            )["imageIds"]
        )
        == 1
    )

    client.put_image(repositoryName="images", imageManifest=manifest, imageTag="latest")
    assert (
        client.list_images(repositoryName="images", filter={"tagStatus": "UNTAGGED"})[
            "imageIds"
        ]
        == []
    )
    assert client.list_images(repositoryName="images", filter={"tagStatus": "TAGGED"})[
        "imageIds"
    ] == [{"imageDigest": digest, "imageTag": "latest"}]
