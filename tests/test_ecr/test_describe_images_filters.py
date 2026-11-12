import json

import boto3
import pytest

from moto import mock_aws

from .test_ecr_helpers import _create_image_manifest


@pytest.mark.parametrize(
    "image_filter, expected_kinds",
    [
        (None, {"tagged", "untagged"}),
        ({}, {"tagged", "untagged"}),
        ({"tagStatus": "ANY"}, {"tagged", "untagged"}),
        ({"tagStatus": "TAGGED"}, {"tagged"}),
        ({"tagStatus": "UNTAGGED"}, {"untagged"}),
    ],
)
@mock_aws
def test_describe_images_tag_status(image_filter, expected_kinds):
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
    images = client.describe_images(repositoryName="images", **kwargs)["imageDetails"]
    expected = {"tagged": tagged, "untagged": untagged}
    assert {image["imageDigest"] for image in images} == {
        expected[kind] for kind in expected_kinds
    }
    for image in images:
        if image["imageDigest"] == tagged:
            assert set(image["imageTags"]) == {"latest", "v1"}
        else:
            assert "imageTags" not in image

    # Filtering must not change image metadata or the unfiltered inventory.
    assert len(client.describe_images(repositoryName="images")["imageDetails"]) == 2
    selected = client.describe_images(
        repositoryName="images", imageIds=[{"imageDigest": tagged}]
    )["imageDetails"]
    assert {image["imageDigest"] for image in selected} == {tagged}
    assert set(selected[0]["imageTags"]) == {"latest", "v1"}


@pytest.mark.parametrize("tag_status", ["TAGGED", "UNTAGGED", "ANY"])
@mock_aws
def test_describe_images_tag_status_empty_repository(tag_status):
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="empty")
    client.create_repository(repositoryName="other")
    client.put_image(
        repositoryName="other",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )
    assert (
        client.describe_images(
            repositoryName="empty", filter={"tagStatus": tag_status}
        )["imageDetails"]
        == []
    )


@mock_aws
def test_describe_images_tag_status_after_tagging_image():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="images")
    manifest = json.dumps(_create_image_manifest())
    client.put_image(repositoryName="images", imageManifest=manifest)
    assert (
        client.describe_images(repositoryName="images", filter={"tagStatus": "TAGGED"})[
            "imageDetails"
        ]
        == []
    )

    client.put_image(repositoryName="images", imageManifest=manifest, imageTag="latest")
    assert (
        client.describe_images(
            repositoryName="images", filter={"tagStatus": "UNTAGGED"}
        )["imageDetails"]
        == []
    )
    assert client.describe_images(
        repositoryName="images", filter={"tagStatus": "TAGGED"}
    )["imageDetails"][0]["imageTags"] == ["latest"]
