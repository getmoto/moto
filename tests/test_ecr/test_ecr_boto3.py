from __future__ import unicode_literals

import hashlib
import json
from datetime import datetime

import pytest
from freezegun import freeze_time
import os
from random import random

import re
import sure  # noqa

import boto3
from botocore.exceptions import ClientError
from dateutil.tz import tzlocal

from moto import mock_ecr
from unittest import SkipTest

from moto.core import ACCOUNT_ID


def _create_image_digest(contents=None):
    if not contents:
        contents = "docker_image{0}".format(int(random() * 10 ** 6))
    return "sha256:%s" % hashlib.sha256(contents.encode("utf-8")).hexdigest()


def _create_image_manifest():
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 7023,
            "digest": _create_image_digest("config"),
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": _create_image_digest("layer1"),
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 16724,
                "digest": _create_image_digest("layer2"),
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 73109,
                # randomize image digest
                "digest": _create_image_digest(),
            },
        ],
    }


@mock_ecr
def test_create_repository():
    # given
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"

    # when
    response = client.create_repository(repositoryName=repo_name)

    # then
    repo = response["repository"]
    repo["repositoryName"].should.equal(repo_name)
    repo["repositoryArn"].should.equal(
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{repo_name}"
    )
    repo["registryId"].should.equal(ACCOUNT_ID)
    repo["repositoryUri"].should.equal(
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}"
    )
    repo["createdAt"].should.be.a(datetime)
    repo["imageTagMutability"].should.equal("MUTABLE")
    repo["imageScanningConfiguration"].should.equal({"scanOnPush": False})
    repo["encryptionConfiguration"].should.equal({"encryptionType": "AES256"})


@mock_ecr
def test_create_repository_with_non_default_config():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    kms_key = f"arn:aws:kms:{region_name}:{ACCOUNT_ID}:key/51d81fab-b138-4bd2-8a09-07fd6d37224d"

    # when
    response = client.create_repository(
        repositoryName=repo_name,
        imageTagMutability="IMMUTABLE",
        imageScanningConfiguration={"scanOnPush": True},
        encryptionConfiguration={"encryptionType": "KMS", "kmsKey": kms_key},
        tags=[{"Key": "key-1", "Value": "value-1"}],
    )

    # then
    repo = response["repository"]
    repo["repositoryName"].should.equal(repo_name)
    repo["repositoryArn"].should.equal(
        f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{repo_name}"
    )
    repo["registryId"].should.equal(ACCOUNT_ID)
    repo["repositoryUri"].should.equal(
        f"{ACCOUNT_ID}.dkr.ecr.{region_name}.amazonaws.com/{repo_name}"
    )
    repo["createdAt"].should.be.a(datetime)
    repo["imageTagMutability"].should.equal("IMMUTABLE")
    repo["imageScanningConfiguration"].should.equal({"scanOnPush": True})
    repo["encryptionConfiguration"].should.equal(
        {"encryptionType": "KMS", "kmsKey": kms_key}
    )


@mock_ecr
def test_create_repository_with_aws_managed_kms():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"

    # when
    repo = client.create_repository(
        repositoryName=repo_name, encryptionConfiguration={"encryptionType": "KMS"}
    )["repository"]

    # then
    repo["repositoryName"].should.equal(repo_name)
    repo["encryptionConfiguration"]["encryptionType"].should.equal("KMS")
    repo["encryptionConfiguration"]["kmsKey"].should.match(
        r"arn:aws:kms:eu-central-1:[0-9]{12}:key/[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[ab89][a-f0-9]{3}-[a-f0-9]{12}$"
    )


@mock_ecr
def test_create_repository_error_already_exists():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    with pytest.raises(ClientError) as e:
        client.create_repository(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryAlreadyExistsException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' already exists "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_describe_repositories():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories()
    len(response["repositories"]).should.equal(2)

    repository_arns = [
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository1",
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository0",
    ]
    sorted(
        [
            response["repositories"][0]["repositoryArn"],
            response["repositories"][1]["repositoryArn"],
        ]
    ).should.equal(sorted(repository_arns))

    repository_uris = [
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository1",
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository0",
    ]
    sorted(
        [
            response["repositories"][0]["repositoryUri"],
            response["repositories"][1]["repositoryUri"],
        ]
    ).should.equal(sorted(repository_uris))


@mock_ecr
def test_describe_repositories_1():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories(registryId=ACCOUNT_ID)
    len(response["repositories"]).should.equal(2)

    repository_arns = [
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository1",
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository0",
    ]
    sorted(
        [
            response["repositories"][0]["repositoryArn"],
            response["repositories"][1]["repositoryArn"],
        ]
    ).should.equal(sorted(repository_arns))

    repository_uris = [
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository1",
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository0",
    ]
    sorted(
        [
            response["repositories"][0]["repositoryUri"],
            response["repositories"][1]["repositoryUri"],
        ]
    ).should.equal(sorted(repository_uris))


@mock_ecr
def test_describe_repositories_2():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories(registryId="109876543210")
    len(response["repositories"]).should.equal(0)


@mock_ecr
def test_describe_repositories_3():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories(repositoryNames=["test_repository1"])
    len(response["repositories"]).should.equal(1)
    repository_arn = f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository1"
    response["repositories"][0]["repositoryArn"].should.equal(repository_arn)

    repository_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository1"
    response["repositories"][0]["repositoryUri"].should.equal(repository_uri)


@mock_ecr
def test_describe_repositories_with_image():
    # given
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    # when
    response = client.describe_repositories(repositoryNames=[repo_name])

    # then
    response["repositories"].should.have.length_of(1)

    repo = response["repositories"][0]
    repo["registryId"].should.equal(ACCOUNT_ID)
    repo["repositoryArn"].should.equal(
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{repo_name}"
    )
    repo["repositoryName"].should.equal(repo_name)
    repo["repositoryUri"].should.equal(
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}"
    )
    repo["createdAt"].should.be.a(datetime)
    repo["imageScanningConfiguration"].should.equal({"scanOnPush": False})
    repo["imageTagMutability"].should.equal("MUTABLE")
    repo["encryptionConfiguration"].should.equal({"encryptionType": "AES256"})


@mock_ecr
def test_delete_repository():
    # given
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    response = client.delete_repository(repositoryName=repo_name)

    # then
    repo = response["repository"]
    repo["repositoryName"].should.equal(repo_name)
    repo["repositoryArn"].should.equal(
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{repo_name}"
    )
    repo["registryId"].should.equal(ACCOUNT_ID)
    repo["repositoryUri"].should.equal(
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}"
    )
    repo["createdAt"].should.be.a(datetime)
    repo["imageTagMutability"].should.equal("MUTABLE")

    response = client.describe_repositories()
    response["repositories"].should.have.length_of(0)


@mock_ecr
def test_delete_repository_with_force():
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    # when
    # when
    response = client.delete_repository(repositoryName=repo_name, force=True)

    # then
    repo = response["repository"]
    repo["repositoryName"].should.equal(repo_name)
    repo["repositoryArn"].should.equal(
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{repo_name}"
    )
    repo["registryId"].should.equal(ACCOUNT_ID)
    repo["repositoryUri"].should.equal(
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}"
    )
    repo["createdAt"].should.be.a(datetime)
    repo["imageTagMutability"].should.equal("MUTABLE")

    response = client.describe_repositories()
    response["repositories"].should.have.length_of(0)


@mock_ecr
def test_put_image():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    response = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    response["image"]["imageId"]["imageTag"].should.equal("latest")
    response["image"]["imageId"]["imageDigest"].should.contain("sha")
    response["image"]["repositoryName"].should.equal("test_repository")
    response["image"]["registryId"].should.equal(ACCOUNT_ID)


@mock_ecr
def test_put_image_with_push_date():
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "true":
        raise SkipTest("Cant manipulate time in server mode")

    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    with freeze_time("2018-08-28 00:00:00"):
        image1_date = datetime.now()
        _ = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="latest",
        )

    with freeze_time("2019-05-31 00:00:00"):
        image2_date = datetime.now()
        _ = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="latest",
        )

    describe_response = client.describe_images(repositoryName="test_repository")

    type(describe_response["imageDetails"]).should.be(list)
    len(describe_response["imageDetails"]).should.be(2)

    set(
        [
            describe_response["imageDetails"][0]["imagePushedAt"],
            describe_response["imageDetails"][1]["imagePushedAt"],
        ]
    ).should.equal(set([image1_date, image2_date]))


@mock_ecr
def test_put_image_with_multiple_tags():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")
    manifest = _create_image_manifest()
    response = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest),
        imageTag="v1",
    )

    response["image"]["imageId"]["imageTag"].should.equal("v1")
    response["image"]["imageId"]["imageDigest"].should.contain("sha")
    response["image"]["repositoryName"].should.equal("test_repository")
    response["image"]["registryId"].should.equal(ACCOUNT_ID)

    response1 = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest),
        imageTag="latest",
    )

    response1["image"]["imageId"]["imageTag"].should.equal("latest")
    response1["image"]["imageId"]["imageDigest"].should.contain("sha")
    response1["image"]["repositoryName"].should.equal("test_repository")
    response1["image"]["registryId"].should.equal(ACCOUNT_ID)

    response2 = client.describe_images(repositoryName="test_repository")
    type(response2["imageDetails"]).should.be(list)
    len(response2["imageDetails"]).should.be(1)

    response2["imageDetails"][0]["imageDigest"].should.contain("sha")

    response2["imageDetails"][0]["registryId"].should.equal(ACCOUNT_ID)

    response2["imageDetails"][0]["repositoryName"].should.equal("test_repository")

    len(response2["imageDetails"][0]["imageTags"]).should.be(2)
    response2["imageDetails"][0]["imageTags"].should.be.equal(["v1", "latest"])


@mock_ecr
def test_list_images():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository_1")

    _ = client.create_repository(repositoryName="test_repository_2")

    _ = client.put_image(
        repositoryName="test_repository_1",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    _ = client.put_image(
        repositoryName="test_repository_1",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v1",
    )

    _ = client.put_image(
        repositoryName="test_repository_1",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v2",
    )

    _ = client.put_image(
        repositoryName="test_repository_2",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="oldest",
    )

    response = client.list_images(repositoryName="test_repository_1")
    type(response["imageIds"]).should.be(list)
    len(response["imageIds"]).should.be(3)

    for image in response["imageIds"]:
        image["imageDigest"].should.contain("sha")

    image_tags = ["latest", "v1", "v2"]
    set(
        [
            response["imageIds"][0]["imageTag"],
            response["imageIds"][1]["imageTag"],
            response["imageIds"][2]["imageTag"],
        ]
    ).should.equal(set(image_tags))

    response = client.list_images(repositoryName="test_repository_2")
    type(response["imageIds"]).should.be(list)
    len(response["imageIds"]).should.be(1)
    response["imageIds"][0]["imageTag"].should.equal("oldest")
    response["imageIds"][0]["imageDigest"].should.contain("sha")


@mock_ecr
def test_list_images_from_repository_that_doesnt_exist():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository_1")

    # non existing repo
    error_msg = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123'.*",
        re.MULTILINE,
    )
    client.list_images.when.called_with(
        repositoryName="repo-that-doesnt-exist", registryId="123"
    ).should.throw(Exception, error_msg)

    # repo does not exist in specified registry
    error_msg = re.compile(
        r".*The repository with name 'test_repository_1' does not exist in the registry with id '222'.*",
        re.MULTILINE,
    )
    client.list_images.when.called_with(
        repositoryName="test_repository_1", registryId="222"
    ).should.throw(Exception, error_msg)


@mock_ecr
def test_describe_images():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v1",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v2",
    )

    response = client.describe_images(repositoryName="test_repository")
    type(response["imageDetails"]).should.be(list)
    len(response["imageDetails"]).should.be(4)

    response["imageDetails"][0]["imageDigest"].should.contain("sha")
    response["imageDetails"][1]["imageDigest"].should.contain("sha")
    response["imageDetails"][2]["imageDigest"].should.contain("sha")
    response["imageDetails"][3]["imageDigest"].should.contain("sha")

    response["imageDetails"][0]["registryId"].should.equal(ACCOUNT_ID)
    response["imageDetails"][1]["registryId"].should.equal(ACCOUNT_ID)
    response["imageDetails"][2]["registryId"].should.equal(ACCOUNT_ID)
    response["imageDetails"][3]["registryId"].should.equal(ACCOUNT_ID)

    response["imageDetails"][0]["repositoryName"].should.equal("test_repository")
    response["imageDetails"][1]["repositoryName"].should.equal("test_repository")
    response["imageDetails"][2]["repositoryName"].should.equal("test_repository")
    response["imageDetails"][3]["repositoryName"].should.equal("test_repository")

    response["imageDetails"][0].should_not.have.key("imageTags")
    len(response["imageDetails"][1]["imageTags"]).should.be(1)
    len(response["imageDetails"][2]["imageTags"]).should.be(1)
    len(response["imageDetails"][3]["imageTags"]).should.be(1)

    image_tags = ["latest", "v1", "v2"]
    set(
        [
            response["imageDetails"][1]["imageTags"][0],
            response["imageDetails"][2]["imageTags"][0],
            response["imageDetails"][3]["imageTags"][0],
        ]
    ).should.equal(set(image_tags))

    response["imageDetails"][0]["imageSizeInBytes"].should.equal(52428800)
    response["imageDetails"][1]["imageSizeInBytes"].should.equal(52428800)
    response["imageDetails"][2]["imageSizeInBytes"].should.equal(52428800)
    response["imageDetails"][3]["imageSizeInBytes"].should.equal(52428800)


@mock_ecr
def test_describe_images_by_tag():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    tag_map = {}
    for tag in ["latest", "v1", "v2"]:
        put_response = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag=tag,
        )
        tag_map[tag] = put_response["image"]

    for tag, put_response in tag_map.items():
        response = client.describe_images(
            repositoryName="test_repository", imageIds=[{"imageTag": tag}]
        )
        len(response["imageDetails"]).should.be(1)
        image_detail = response["imageDetails"][0]
        image_detail["registryId"].should.equal(ACCOUNT_ID)
        image_detail["repositoryName"].should.equal("test_repository")
        image_detail["imageTags"].should.equal([put_response["imageId"]["imageTag"]])
        image_detail["imageDigest"].should.equal(put_response["imageId"]["imageDigest"])


@mock_ecr
def test_describe_images_tags_should_not_contain_empty_tag1():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()
    client.put_image(
        repositoryName="test_repository", imageManifest=json.dumps(manifest)
    )

    tags = ["v1", "v2", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    response = client.describe_images(
        repositoryName="test_repository", imageIds=[{"imageTag": tag}]
    )
    len(response["imageDetails"]).should.be(1)
    image_detail = response["imageDetails"][0]
    len(image_detail["imageTags"]).should.equal(3)
    image_detail["imageTags"].should.be.equal(tags)


@mock_ecr
def test_describe_images_tags_should_not_contain_empty_tag2():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()
    tags = ["v1", "v2"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    client.put_image(
        repositoryName="test_repository", imageManifest=json.dumps(manifest)
    )

    client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest),
        imageTag="latest",
    )

    response = client.describe_images(
        repositoryName="test_repository", imageIds=[{"imageTag": tag}]
    )
    len(response["imageDetails"]).should.be(1)
    image_detail = response["imageDetails"][0]
    len(image_detail["imageTags"]).should.equal(3)
    image_detail["imageTags"].should.be.equal(["v1", "v2", "latest"])


@mock_ecr
def test_describe_repository_that_doesnt_exist():
    client = boto3.client("ecr", region_name="us-east-1")

    error_msg = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123'.*",
        re.MULTILINE,
    )
    client.describe_repositories.when.called_with(
        repositoryNames=["repo-that-doesnt-exist"], registryId="123"
    ).should.throw(ClientError, error_msg)


@mock_ecr
def test_describe_image_that_doesnt_exist():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    error_msg1 = re.compile(
        r".*The image with imageId {imageDigest:'null', imageTag:'testtag'} does not exist within "
        r"the repository with name 'test_repository' in the registry with id '123456789012'.*",
        re.MULTILINE,
    )

    client.describe_images.when.called_with(
        repositoryName="test_repository",
        imageIds=[{"imageTag": "testtag"}],
        registryId=ACCOUNT_ID,
    ).should.throw(client.exceptions.ImageNotFoundException, error_msg1)

    error_msg2 = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123456789012'.*",
        re.MULTILINE,
    )
    client.describe_images.when.called_with(
        repositoryName="repo-that-doesnt-exist",
        imageIds=[{"imageTag": "testtag"}],
        registryId=ACCOUNT_ID,
    ).should.throw(ClientError, error_msg2)


@mock_ecr
def test_delete_repository_that_doesnt_exist():
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "repo-that-doesnt-exist"

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_repository_error_not_empty():
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotEmptyException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' "
        f"in registry with id '{ACCOUNT_ID}' "
        "cannot be deleted because it still contains images"
    )


@mock_ecr
def test_describe_images_by_digest():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    tags = ["latest", "v1", "v2"]
    digest_map = {}
    for tag in tags:
        put_response = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag=tag,
        )
        digest_map[put_response["image"]["imageId"]["imageDigest"]] = put_response[
            "image"
        ]

    for digest, put_response in digest_map.items():
        response = client.describe_images(
            repositoryName="test_repository", imageIds=[{"imageDigest": digest}]
        )
        len(response["imageDetails"]).should.be(1)
        image_detail = response["imageDetails"][0]
        image_detail["registryId"].should.equal(ACCOUNT_ID)
        image_detail["repositoryName"].should.equal("test_repository")
        image_detail["imageTags"].should.equal([put_response["imageId"]["imageTag"]])
        image_detail["imageDigest"].should.equal(digest)


@mock_ecr
def test_get_authorization_token_assume_region():
    client = boto3.client("ecr", region_name="us-east-1")
    auth_token_response = client.get_authorization_token()

    auth_token_response.should.contain("authorizationData")
    auth_token_response.should.contain("ResponseMetadata")
    auth_token_response["authorizationData"].should.equal(
        [
            {
                "authorizationToken": "QVdTOjEyMzQ1Njc4OTAxMi1hdXRoLXRva2Vu",
                "proxyEndpoint": f"https://{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com",
                "expiresAt": datetime(2015, 1, 1, tzinfo=tzlocal()),
            }
        ]
    )


@mock_ecr
def test_get_authorization_token_explicit_regions():
    client = boto3.client("ecr", region_name="us-east-1")
    auth_token_response = client.get_authorization_token(
        registryIds=["10987654321", "878787878787"]
    )

    auth_token_response.should.contain("authorizationData")
    auth_token_response.should.contain("ResponseMetadata")
    auth_token_response["authorizationData"].should.equal(
        [
            {
                "authorizationToken": "QVdTOjEwOTg3NjU0MzIxLWF1dGgtdG9rZW4=",
                "proxyEndpoint": "https://10987654321.dkr.ecr.us-east-1.amazonaws.com",
                "expiresAt": datetime(2015, 1, 1, tzinfo=tzlocal()),
            },
            {
                "authorizationToken": "QVdTOjg3ODc4Nzg3ODc4Ny1hdXRoLXRva2Vu",
                "proxyEndpoint": "https://878787878787.dkr.ecr.us-east-1.amazonaws.com",
                "expiresAt": datetime(2015, 1, 1, tzinfo=tzlocal()),
            },
        ]
    )


@mock_ecr
def test_batch_get_image():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v1",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v2",
    )

    response = client.batch_get_image(
        repositoryName="test_repository", imageIds=[{"imageTag": "v2"}]
    )

    type(response["images"]).should.be(list)
    len(response["images"]).should.be(1)

    response["images"][0]["imageManifest"].should.contain(
        "vnd.docker.distribution.manifest.v2+json"
    )
    response["images"][0]["registryId"].should.equal(ACCOUNT_ID)
    response["images"][0]["repositoryName"].should.equal("test_repository")

    response["images"][0]["imageId"]["imageTag"].should.equal("v2")
    response["images"][0]["imageId"]["imageDigest"].should.contain("sha")

    type(response["failures"]).should.be(list)
    len(response["failures"]).should.be(0)


@mock_ecr
def test_batch_get_image_that_doesnt_exist():
    client = boto3.client("ecr", region_name="us-east-1")
    _ = client.create_repository(repositoryName="test_repository")

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v1",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v2",
    )

    response = client.batch_get_image(
        repositoryName="test_repository", imageIds=[{"imageTag": "v5"}]
    )

    type(response["images"]).should.be(list)
    len(response["images"]).should.be(0)

    type(response["failures"]).should.be(list)
    len(response["failures"]).should.be(1)
    response["failures"][0]["failureReason"].should.equal("Requested image not found")
    response["failures"][0]["failureCode"].should.equal("ImageNotFound")
    response["failures"][0]["imageId"]["imageTag"].should.equal("v5")


@mock_ecr
def test_batch_delete_image_by_tag():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()

    tags = ["v1", "v1.0", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response1 = client.describe_images(repositoryName="test_repository")

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageTag": "latest"}],
    )

    describe_response2 = client.describe_images(repositoryName="test_repository")

    type(describe_response1["imageDetails"][0]["imageTags"]).should.be(list)
    len(describe_response1["imageDetails"][0]["imageTags"]).should.be(3)

    type(describe_response2["imageDetails"][0]["imageTags"]).should.be(list)
    len(describe_response2["imageDetails"][0]["imageTags"]).should.be(2)

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(1)

    batch_delete_response["imageIds"][0]["imageTag"].should.equal("latest")

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(0)


@mock_ecr
def test_batch_delete_image_delete_last_tag():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="v1",
    )

    describe_response1 = client.describe_images(repositoryName="test_repository")

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageTag": "v1"}],
    )

    describe_response2 = client.describe_images(repositoryName="test_repository")

    type(describe_response1["imageDetails"][0]["imageTags"]).should.be(list)
    len(describe_response1["imageDetails"][0]["imageTags"]).should.be(1)

    type(describe_response2["imageDetails"]).should.be(list)
    len(describe_response2["imageDetails"]).should.be(0)

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(1)

    batch_delete_response["imageIds"][0]["imageTag"].should.equal("v1")

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(0)


@mock_ecr
def test_batch_delete_image_with_nonexistent_tag():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()

    tags = ["v1", "v1.0", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response = client.describe_images(repositoryName="test_repository")

    missing_tag = "missing-tag"
    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageTag": missing_tag}],
    )

    type(describe_response["imageDetails"][0]["imageTags"]).should.be(list)
    len(describe_response["imageDetails"][0]["imageTags"]).should.be(3)

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(0)

    batch_delete_response["failures"][0]["imageId"]["imageTag"].should.equal(
        missing_tag
    )
    batch_delete_response["failures"][0]["failureCode"].should.equal("ImageNotFound")
    batch_delete_response["failures"][0]["failureReason"].should.equal(
        "Requested image not found"
    )

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(1)


@mock_ecr
def test_batch_delete_image_by_digest():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()

    tags = ["v1", "v2", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response = client.describe_images(repositoryName="test_repository")
    image_digest = describe_response["imageDetails"][0]["imageDigest"]

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageDigest": image_digest}],
    )

    describe_response = client.describe_images(repositoryName="test_repository")

    type(describe_response["imageDetails"]).should.be(list)
    len(describe_response["imageDetails"]).should.be(0)

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(3)

    batch_delete_response["imageIds"][0]["imageDigest"].should.equal(image_digest)
    batch_delete_response["imageIds"][1]["imageDigest"].should.equal(image_digest)
    batch_delete_response["imageIds"][2]["imageDigest"].should.equal(image_digest)

    set(
        [
            batch_delete_response["imageIds"][0]["imageTag"],
            batch_delete_response["imageIds"][1]["imageTag"],
            batch_delete_response["imageIds"][2]["imageTag"],
        ]
    ).should.equal(set(tags))

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(0)


@mock_ecr
def test_batch_delete_image_with_invalid_digest():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()

    tags = ["v1", "v2", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    invalid_image_digest = "sha256:invalid-digest"

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageDigest": invalid_image_digest}],
    )

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(0)

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(1)

    batch_delete_response["failures"][0]["imageId"]["imageDigest"].should.equal(
        invalid_image_digest
    )
    batch_delete_response["failures"][0]["failureCode"].should.equal(
        "InvalidImageDigest"
    )
    batch_delete_response["failures"][0]["failureReason"].should.equal(
        "Invalid request parameters: image digest should satisfy the regex '[a-zA-Z0-9-_+.]+:[a-fA-F0-9]+'"
    )


@mock_ecr
def test_batch_delete_image_with_missing_parameters():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910", repositoryName="test_repository", imageIds=[{}]
    )

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(0)

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(1)

    batch_delete_response["failures"][0]["failureCode"].should.equal(
        "MissingDigestAndTag"
    )
    batch_delete_response["failures"][0]["failureReason"].should.equal(
        "Invalid request parameters: both tag and digest cannot be null"
    )


@mock_ecr
def test_batch_delete_image_with_matching_digest_and_tag():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()

    tags = ["v1", "v1.0", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response = client.describe_images(repositoryName="test_repository")
    image_digest = describe_response["imageDetails"][0]["imageDigest"]

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageDigest": image_digest, "imageTag": "v1"}],
    )

    describe_response = client.describe_images(repositoryName="test_repository")

    type(describe_response["imageDetails"]).should.be(list)
    len(describe_response["imageDetails"]).should.be(0)

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(3)

    batch_delete_response["imageIds"][0]["imageDigest"].should.equal(image_digest)
    batch_delete_response["imageIds"][1]["imageDigest"].should.equal(image_digest)
    batch_delete_response["imageIds"][2]["imageDigest"].should.equal(image_digest)

    set(
        [
            batch_delete_response["imageIds"][0]["imageTag"],
            batch_delete_response["imageIds"][1]["imageTag"],
            batch_delete_response["imageIds"][2]["imageTag"],
        ]
    ).should.equal(set(tags))

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(0)


@mock_ecr
def test_batch_delete_image_with_mismatched_digest_and_tag():
    client = boto3.client("ecr", region_name="us-east-1")
    client.create_repository(repositoryName="test_repository")

    manifest = _create_image_manifest()

    tags = ["v1", "latest"]
    for tag in tags:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response = client.describe_images(repositoryName="test_repository")
    image_digest = describe_response["imageDetails"][0]["imageDigest"]

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910",
        repositoryName="test_repository",
        imageIds=[{"imageDigest": image_digest, "imageTag": "v2"}],
    )

    type(batch_delete_response["imageIds"]).should.be(list)
    len(batch_delete_response["imageIds"]).should.be(0)

    type(batch_delete_response["failures"]).should.be(list)
    len(batch_delete_response["failures"]).should.be(1)

    batch_delete_response["failures"][0]["imageId"]["imageDigest"].should.equal(
        image_digest
    )
    batch_delete_response["failures"][0]["imageId"]["imageTag"].should.equal("v2")
    batch_delete_response["failures"][0]["failureCode"].should.equal("ImageNotFound")
    batch_delete_response["failures"][0]["failureReason"].should.equal(
        "Requested image not found"
    )


@mock_ecr
def test_list_tags_for_resource():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    arn = client.create_repository(
        repositoryName=repo_name, tags=[{"Key": "key-1", "Value": "value-1"}],
    )["repository"]["repositoryArn"]

    # when
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]

    # then
    tags.should.equal([{"Key": "key-1", "Value": "value-1"}])


@mock_ecr
def test_list_tags_for_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(
            resourceArn=f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{repo_name}"
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("ListTagsForResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_list_tags_for_resource_error_invalid_param():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(resourceArn="invalid",)

    # then
    ex = e.value
    ex.operation_name.should.equal("ListTagsForResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Invalid parameter at 'resourceArn' failed to satisfy constraint: "
        "'Invalid ARN'"
    )


@mock_ecr
def test_tag_resource():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    arn = client.create_repository(
        repositoryName=repo_name, tags=[{"Key": "key-1", "Value": "value-1"}],
    )["repository"]["repositoryArn"]

    # when
    client.tag_resource(resourceArn=arn, tags=[{"Key": "key-2", "Value": "value-2"}])

    # then
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    sorted(tags, key=lambda i: i["Key"]).should.equal(
        sorted(
            [
                {"Key": "key-1", "Value": "value-1"},
                {"Key": "key-2", "Value": "value-2"},
            ],
            key=lambda i: i["Key"],
        )
    )


@mock_ecr
def test_tag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            resourceArn=f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{repo_name}",
            tags=[{"Key": "key-1", "Value": "value-2"}],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("TagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_untag_resource():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    arn = client.create_repository(
        repositoryName=repo_name,
        tags=[
            {"Key": "key-1", "Value": "value-1"},
            {"Key": "key-2", "Value": "value-2"},
        ],
    )["repository"]["repositoryArn"]

    # when
    client.untag_resource(resourceArn=arn, tagKeys=["key-1"])

    # then
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    tags.should.equal([{"Key": "key-2", "Value": "value-2"}])


@mock_ecr
def test_untag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.untag_resource(
            resourceArn=f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{repo_name}",
            tagKeys=["key-1"],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("UntagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_image_tag_mutability():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    response = client.describe_repositories(repositoryNames=[repo_name])
    response["repositories"][0]["imageTagMutability"].should.equal("MUTABLE")

    # when
    response = client.put_image_tag_mutability(
        repositoryName=repo_name, imageTagMutability="IMMUTABLE",
    )

    # then
    response["imageTagMutability"].should.equal("IMMUTABLE")
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)

    response = client.describe_repositories(repositoryNames=[repo_name])
    response["repositories"][0]["imageTagMutability"].should.equal("IMMUTABLE")


@mock_ecr
def test_put_image_tag_mutability_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.put_image_tag_mutability(
            repositoryName=repo_name, imageTagMutability="IMMUTABLE",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutImageTagMutability")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_image_tag_mutability_error_invalid_param():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    with pytest.raises(ClientError) as e:
        client.put_image_tag_mutability(
            repositoryName=repo_name, imageTagMutability="invalid",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutImageTagMutability")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Invalid parameter at 'imageTagMutability' failed to satisfy constraint: "
        "'Member must satisfy enum value set: [IMMUTABLE, MUTABLE]'"
    )


@mock_ecr
def test_put_image_scanning_configuration():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    response = client.describe_repositories(repositoryNames=[repo_name])
    response["repositories"][0]["imageScanningConfiguration"].should.equal(
        {"scanOnPush": False}
    )

    # when
    response = client.put_image_scanning_configuration(
        repositoryName=repo_name, imageScanningConfiguration={"scanOnPush": True}
    )

    # then
    response["imageScanningConfiguration"].should.equal({"scanOnPush": True})
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)

    response = client.describe_repositories(repositoryNames=[repo_name])
    response["repositories"][0]["imageScanningConfiguration"].should.equal(
        {"scanOnPush": True}
    )


@mock_ecr
def test_put_image_scanning_configuration_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.put_image_scanning_configuration(
            repositoryName=repo_name, imageScanningConfiguration={"scanOnPush": True},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutImageScanningConfiguration")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_set_repository_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "root",
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                "Action": ["ecr:DescribeImages"],
            }
        ],
    }

    # when
    response = client.set_repository_policy(
        repositoryName=repo_name, policyText=json.dumps(policy),
    )

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    json.loads(response["policyText"]).should.equal(policy)


@mock_ecr
def test_set_repository_policy_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "root",
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                "Action": ["ecr:DescribeImages"],
            }
        ],
    }

    # when
    with pytest.raises(ClientError) as e:
        client.set_repository_policy(
            repositoryName=repo_name, policyText=json.dumps(policy),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("SetRepositoryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_set_repository_policy_error_invalid_param():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow"}],
    }

    # when
    with pytest.raises(ClientError) as e:
        client.set_repository_policy(
            repositoryName=repo_name, policyText=json.dumps(policy),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("SetRepositoryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Invalid parameter at 'PolicyText' failed to satisfy constraint: "
        "'Invalid repository policy provided'"
    )


@mock_ecr
def test_get_repository_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "root",
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                "Action": ["ecr:DescribeImages"],
            }
        ],
    }
    client.set_repository_policy(
        repositoryName=repo_name, policyText=json.dumps(policy),
    )

    # when
    response = client.get_repository_policy(repositoryName=repo_name)

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    json.loads(response["policyText"]).should.equal(policy)


@mock_ecr
def test_get_repository_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.get_repository_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("GetRepositoryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_get_repository_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    with pytest.raises(ClientError) as e:
        client.get_repository_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("GetRepositoryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryPolicyNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Repository policy does not exist "
        f"for the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_repository_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "root",
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                "Action": ["ecr:DescribeImages"],
            }
        ],
    }
    client.set_repository_policy(
        repositoryName=repo_name, policyText=json.dumps(policy),
    )

    # when
    response = client.delete_repository_policy(repositoryName=repo_name)

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    json.loads(response["policyText"]).should.equal(policy)

    with pytest.raises(ClientError) as e:
        client.get_repository_policy(repositoryName=repo_name)

    e.value.response["Error"]["Code"].should.contain(
        "RepositoryPolicyNotFoundException"
    )


@mock_ecr
def test_delete_repository_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteRepositoryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_repository_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteRepositoryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryPolicyNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Repository policy does not exist "
        f"for the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_lifecycle_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "rules": [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            }
        ]
    }

    # when
    response = client.put_lifecycle_policy(
        repositoryName=repo_name, lifecyclePolicyText=json.dumps(policy),
    )

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    json.loads(response["lifecyclePolicyText"]).should.equal(policy)


@mock_ecr
def test_put_lifecycle_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"
    policy = {
        "rules": [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            }
        ]
    }

    # when
    with pytest.raises(ClientError) as e:
        client.put_lifecycle_policy(
            repositoryName=repo_name, lifecyclePolicyText=json.dumps(policy)
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutLifecyclePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_get_lifecycle_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "rules": [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            }
        ]
    }
    client.put_lifecycle_policy(
        repositoryName=repo_name, lifecyclePolicyText=json.dumps(policy),
    )

    # when
    response = client.get_lifecycle_policy(repositoryName=repo_name)

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    json.loads(response["lifecyclePolicyText"]).should.equal(policy)
    response["lastEvaluatedAt"].should.be.a(datetime)


@mock_ecr
def test_get_lifecycle_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.get_lifecycle_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("GetLifecyclePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_get_lifecycle_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    with pytest.raises(ClientError) as e:
        client.get_lifecycle_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("GetLifecyclePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("LifecyclePolicyNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Lifecycle policy does not exist "
        f"for the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_lifecycle_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    policy = {
        "rules": [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            }
        ]
    }
    client.put_lifecycle_policy(
        repositoryName=repo_name, lifecyclePolicyText=json.dumps(policy),
    )

    # when
    response = client.delete_lifecycle_policy(repositoryName=repo_name)

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    json.loads(response["lifecyclePolicyText"]).should.equal(policy)
    response["lastEvaluatedAt"].should.be.a(datetime)

    with pytest.raises(ClientError) as e:
        client.get_lifecycle_policy(repositoryName=repo_name)

    e.value.response["Error"]["Code"].should.contain("LifecyclePolicyNotFoundException")


@mock_ecr
def test_delete_lifecycle_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.delete_lifecycle_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteLifecyclePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_lifecycle_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_lifecycle_policy(repositoryName=repo_name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteLifecyclePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("LifecyclePolicyNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Lifecycle policy does not exist "
        f"for the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_registry_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": ["arn:aws:iam::111111111111:root", "222222222222"]
                },
                "Action": ["ecr:CreateRepository", "ecr:ReplicateImage"],
                "Resource": "*",
            }
        ],
    }

    # when
    response = client.put_registry_policy(policyText=json.dumps(policy))

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    json.loads(response["policyText"]).should.equal(policy)


@mock_ecr
def test_put_registry_policy_error_invalid_action():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
                "Action": [
                    "ecr:CreateRepository",
                    "ecr:ReplicateImage",
                    "ecr:DescribeRepositories",
                ],
                "Resource": "*",
            }
        ],
    }

    # when
    with pytest.raises(ClientError) as e:
        client.put_registry_policy(policyText=json.dumps(policy))

    # then
    ex = e.value
    ex.operation_name.should.equal("PutRegistryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Invalid parameter at 'PolicyText' failed to satisfy constraint: "
        "'Invalid registry policy provided'"
    )


@mock_ecr
def test_get_registry_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": ["arn:aws:iam::111111111111:root", "222222222222"]
                },
                "Action": ["ecr:CreateRepository", "ecr:ReplicateImage"],
                "Resource": "*",
            }
        ],
    }
    client.put_registry_policy(policyText=json.dumps(policy))

    # when
    response = client.get_registry_policy()

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    json.loads(response["policyText"]).should.equal(policy)


@mock_ecr
def test_get_registry_policy_error_policy_not_exists():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.get_registry_policy()

    # then
    ex = e.value
    ex.operation_name.should.equal("GetRegistryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RegistryPolicyNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"Registry policy does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_registry_policy():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": ["arn:aws:iam::111111111111:root", "222222222222"]
                },
                "Action": ["ecr:CreateRepository", "ecr:ReplicateImage"],
                "Resource": "*",
            }
        ],
    }
    client.put_registry_policy(policyText=json.dumps(policy))

    # when
    response = client.delete_registry_policy()

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    json.loads(response["policyText"]).should.equal(policy)

    with pytest.raises(ClientError) as e:
        client.get_registry_policy()

    e.value.response["Error"]["Code"].should.contain("RegistryPolicyNotFoundException")


@mock_ecr
def test_delete_registry_policy_error_policy_not_exists():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.delete_registry_policy()

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteRegistryPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RegistryPolicyNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"Registry policy does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_tag = "latest"
    image_digest = client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]

    # when
    response = client.start_image_scan(
        repositoryName=repo_name, imageId={"imageTag": image_tag}
    )

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    response["imageId"].should.equal(
        {"imageDigest": image_digest, "imageTag": image_tag}
    )
    response["imageScanStatus"].should.equal({"status": "IN_PROGRESS"})


@mock_ecr
def test_start_image_scan_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=repo_name, imageId={"imageTag": "latest"}
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartImageScan")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan_error_image_not_exists():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_tag = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=repo_name, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartImageScan")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ImageNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The image with imageId {{imageDigest:'null', imageTag:'{image_tag}'}} does not exist "
        f"within the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan_error_image_tag_digest_mismatch():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_digest = client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]
    image_tag = "not-latest"

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=repo_name,
            imageId={"imageTag": image_tag, "imageDigest": image_digest},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartImageScan")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ImageNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The image with imageId {{imageDigest:'{image_digest}', imageTag:'{image_tag}'}} does not exist "
        f"within the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan_error_daily_limit():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_tag = "latest"
    image_digest = client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]
    client.start_image_scan(repositoryName=repo_name, imageId={"imageTag": image_tag})

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=repo_name, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartImageScan")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("LimitExceededException")
    ex.response["Error"]["Message"].should.equal(
        "The scan quota per image has been exceeded. Wait and try again."
    )


@mock_ecr
def test_describe_image_scan_findings():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_tag = "latest"
    image_digest = client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]
    client.start_image_scan(repositoryName=repo_name, imageId={"imageTag": image_tag})

    # when
    response = client.describe_image_scan_findings(
        repositoryName=repo_name, imageId={"imageTag": image_tag}
    )

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["repositoryName"].should.equal(repo_name)
    response["imageId"].should.equal(
        {"imageDigest": image_digest, "imageTag": image_tag}
    )
    response["imageScanStatus"].should.equal(
        {"status": "COMPLETE", "description": "The scan was completed successfully."}
    )
    scan_findings = response["imageScanFindings"]
    scan_findings["imageScanCompletedAt"].should.be.a(datetime)
    scan_findings["vulnerabilitySourceUpdatedAt"].should.be.a(datetime)
    scan_findings["findings"].should.equal(
        [
            {
                "name": "CVE-9999-9999",
                "uri": "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-9999-9999",
                "severity": "HIGH",
                "attributes": [
                    {"key": "package_version", "value": "9.9.9"},
                    {"key": "package_name", "value": "moto_fake"},
                    {"key": "CVSS2_VECTOR", "value": "AV:N/AC:L/Au:N/C:P/I:P/A:P",},
                    {"key": "CVSS2_SCORE", "value": "7.5"},
                ],
            }
        ]
    )
    scan_findings["findingSeverityCounts"].should.equal({"HIGH": 1})


@mock_ecr
def test_describe_image_scan_findings_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    repo_name = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_image_scan_findings(
            repositoryName=repo_name, imageId={"imageTag": "latest"}
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeImageScanFindings")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The repository with name '{repo_name}' does not exist "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_describe_image_scan_findings_error_image_not_exists():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_tag = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_image_scan_findings(
            repositoryName=repo_name, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeImageScanFindings")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ImageNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"The image with imageId {{imageDigest:'null', imageTag:'{image_tag}'}} does not exist "
        f"within the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_describe_image_scan_findings_error_scan_not_exists():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    repo_name = "test-repo"
    client.create_repository(repositoryName=repo_name)
    image_tag = "latest"
    client.put_image(
        repositoryName=repo_name,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag=image_tag,
    )

    # when
    with pytest.raises(ClientError) as e:
        client.describe_image_scan_findings(
            repositoryName=repo_name, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeImageScanFindings")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ScanNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"Image scan does not exist for the image with '{{imageDigest:'null', imageTag:'{image_tag}'}}' "
        f"in the repository with name '{repo_name}' "
        f"in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_replication_configuration():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    config = {
        "rules": [
            {"destinations": [{"region": "eu-west-1", "registryId": ACCOUNT_ID},]},
        ]
    }

    # when
    response = client.put_replication_configuration(replicationConfiguration=config)

    # then
    response["replicationConfiguration"].should.equal(config)


@mock_ecr
def test_put_replication_configuration_error_feature_disabled():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    config = {
        "rules": [
            {
                "destinations": [
                    {"region": "eu-central-1", "registryId": "111111111111"},
                ]
            },
            {
                "destinations": [
                    {"region": "eu-central-1", "registryId": "222222222222"},
                ]
            },
        ]
    }

    # when
    with pytest.raises(ClientError) as e:
        client.put_replication_configuration(replicationConfiguration=config)

    # then
    ex = e.value
    ex.operation_name.should.equal("PutReplicationConfiguration")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal("This feature is disabled")


@mock_ecr
def test_put_replication_configuration_error_same_source():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    config = {
        "rules": [
            {"destinations": [{"region": region_name, "registryId": ACCOUNT_ID}]},
        ]
    }

    # when
    with pytest.raises(ClientError) as e:
        client.put_replication_configuration(replicationConfiguration=config)

    # then
    ex = e.value
    ex.operation_name.should.equal("PutReplicationConfiguration")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidParameterException")
    ex.response["Error"]["Message"].should.equal(
        "Invalid parameter at 'replicationConfiguration' failed to satisfy constraint: "
        "'Replication destination cannot be the same as the source registry'"
    )


@mock_ecr
def test_describe_registry():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")

    # when
    response = client.describe_registry()

    # then
    response["registryId"].should.equal(ACCOUNT_ID)
    response["replicationConfiguration"].should.equal({"rules": []})


@mock_ecr
def test_describe_registry_after_update():
    # given
    client = boto3.client("ecr", region_name="eu-central-1")
    config = {
        "rules": [
            {"destinations": [{"region": "eu-west-1", "registryId": ACCOUNT_ID}]},
        ]
    }
    client.put_replication_configuration(replicationConfiguration=config)

    # when
    response = client.describe_registry()

    # then
    response["replicationConfiguration"].should.equal(config)
