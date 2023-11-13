import boto3
import json
import pytest

from botocore.exceptions import ClientError
from datetime import datetime
from dateutil.tz import tzlocal
from freezegun import freeze_time
from moto import mock_ecr, settings
from unittest import SkipTest

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .test_ecr_helpers import _create_image_manifest, _create_image_manifest_list

ECR_REGION = "us-east-1"
ECR_REPO = "test-repo"
ECR_REPO_NOT_EXIST = "does-not-exist"


@mock_ecr
def test_create_repository():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)

    # when
    response = client.create_repository(repositoryName=ECR_REPO)

    # then
    repo = response["repository"]
    assert repo["repositoryName"] == ECR_REPO
    assert (
        repo["repositoryArn"]
        == f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{ECR_REPO}"
    )
    assert repo["registryId"] == ACCOUNT_ID
    assert (
        repo["repositoryUri"]
        == f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{ECR_REPO}"
    )
    assert isinstance(repo["createdAt"], datetime)
    assert repo["imageTagMutability"] == "MUTABLE"
    assert repo["imageScanningConfiguration"] == {"scanOnPush": False}
    assert repo["encryptionConfiguration"] == {"encryptionType": "AES256"}


@mock_ecr
def test_create_repository_with_non_default_config():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    kms_key = f"arn:aws:kms:{region_name}:{ACCOUNT_ID}:key/51d81fab-b138-4bd2-8a09-07fd6d37224d"

    # when
    response = client.create_repository(
        repositoryName=ECR_REPO,
        imageTagMutability="IMMUTABLE",
        imageScanningConfiguration={"scanOnPush": True},
        encryptionConfiguration={"encryptionType": "KMS", "kmsKey": kms_key},
        tags=[{"Key": "key-1", "Value": "value-1"}],
    )

    # then
    repo = response["repository"]
    assert repo["repositoryName"] == ECR_REPO
    assert (
        repo["repositoryArn"]
        == f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{ECR_REPO}"
    )
    assert repo["registryId"] == ACCOUNT_ID
    assert (
        repo["repositoryUri"]
        == f"{ACCOUNT_ID}.dkr.ecr.{region_name}.amazonaws.com/{ECR_REPO}"
    )
    assert isinstance(repo["createdAt"], datetime)
    assert repo["imageTagMutability"] == "IMMUTABLE"
    assert repo["imageScanningConfiguration"] == {"scanOnPush": True}
    assert repo["encryptionConfiguration"] == {
        "encryptionType": "KMS",
        "kmsKey": kms_key,
    }


@mock_ecr
def test_create_repository_in_different_account():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)

    # when passing in a custom registry ID
    response = client.create_repository(
        registryId="222222222222", repositoryName=ECR_REPO
    )

    # then we should persist this ID
    repo = response["repository"]
    assert repo["registryId"] == "222222222222"
    assert (
        repo["repositoryArn"]
        == "arn:aws:ecr:us-east-1:222222222222:repository/test-repo"
    )

    # then this repo should be returned with the correct ID
    repo = client.describe_repositories()["repositories"][0]
    assert repo["registryId"] == "222222222222"

    # then we can search for repos with this ID
    response = client.describe_repositories(registryId="222222222222")
    assert len(response["repositories"]) == 1

    # then this repo is not found when searching for a different ID
    response = client.describe_repositories(registryId=ACCOUNT_ID)
    assert len(response["repositories"]) == 0


@mock_ecr
def test_create_repository_with_aws_managed_kms():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    repo = client.create_repository(
        repositoryName=ECR_REPO, encryptionConfiguration={"encryptionType": "KMS"}
    )["repository"]

    # then
    assert repo["repositoryName"] == ECR_REPO
    assert repo["encryptionConfiguration"]["encryptionType"] == "KMS"
    assert repo["encryptionConfiguration"]["kmsKey"].startswith(
        f"arn:aws:kms:eu-central-1:{ACCOUNT_ID}:key/"
    )


@mock_ecr
def test_create_repository_error_already_exists():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    with pytest.raises(ClientError) as e:
        client.create_repository(repositoryName=ECR_REPO)

    # then
    ex = e.value
    assert ex.operation_name == "CreateRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryAlreadyExistsException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO}' already exists in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_create_repository_error_name_validation():
    client = boto3.client("ecr", region_name=ECR_REGION)
    repo_name = "tesT"

    with pytest.raises(ClientError) as e:
        client.create_repository(repositoryName=repo_name)

    ex = e.value
    assert ex.operation_name == "CreateRepository"
    assert ex.response["Error"]["Code"] == "InvalidParameterException"


@mock_ecr
def test_describe_repositories():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories()
    assert len(response["repositories"]) == 2

    repository_arns = {
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository1",
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository0",
    }
    assert {
        response["repositories"][0]["repositoryArn"],
        response["repositories"][1]["repositoryArn"],
    } == repository_arns

    repository_uris = {
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository1",
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository0",
    }
    assert {
        response["repositories"][0]["repositoryUri"],
        response["repositories"][1]["repositoryUri"],
    } == repository_uris


@mock_ecr
def test_describe_repositories_1():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories(registryId=ACCOUNT_ID)
    assert len(response["repositories"]) == 2

    repository_arns = {
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository1",
        f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository0",
    }
    assert {
        response["repositories"][0]["repositoryArn"],
        response["repositories"][1]["repositoryArn"],
    } == repository_arns

    repository_uris = {
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository1",
        f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository0",
    }
    assert {
        response["repositories"][0]["repositoryUri"],
        response["repositories"][1]["repositoryUri"],
    } == repository_uris


@mock_ecr
def test_describe_repositories_2():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories(registryId="109876543210")
    assert len(response["repositories"]) == 0


@mock_ecr
def test_describe_repositories_3():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository1")
    _ = client.create_repository(repositoryName="test_repository0")
    response = client.describe_repositories(repositoryNames=["test_repository1"])
    assert len(response["repositories"]) == 1
    repository_arn = f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/test_repository1"
    assert response["repositories"][0]["repositoryArn"] == repository_arn

    repository_uri = f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/test_repository1"
    assert response["repositories"][0]["repositoryUri"] == repository_uri


@mock_ecr
def test_describe_repositories_with_image():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    # when
    response = client.describe_repositories(repositoryNames=[ECR_REPO])

    # then
    assert len(response["repositories"]) == 1

    repo = response["repositories"][0]
    assert repo["registryId"] == ACCOUNT_ID
    assert (
        repo["repositoryArn"]
        == f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{ECR_REPO}"
    )
    assert repo["repositoryName"] == ECR_REPO
    assert (
        repo["repositoryUri"]
        == f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{ECR_REPO}"
    )
    assert isinstance(repo["createdAt"], datetime)
    assert repo["imageScanningConfiguration"] == {"scanOnPush": False}
    assert repo["imageTagMutability"] == "MUTABLE"
    assert repo["encryptionConfiguration"] == {"encryptionType": "AES256"}


@mock_ecr
def test_delete_repository():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    response = client.delete_repository(repositoryName=ECR_REPO)

    # then
    repo = response["repository"]
    assert repo["repositoryName"] == ECR_REPO
    assert (
        repo["repositoryArn"]
        == f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{ECR_REPO}"
    )
    assert repo["registryId"] == ACCOUNT_ID
    assert (
        repo["repositoryUri"]
        == f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{ECR_REPO}"
    )
    assert isinstance(repo["createdAt"], datetime)
    assert repo["imageTagMutability"] == "MUTABLE"

    response = client.describe_repositories()
    assert len(response["repositories"]) == 0


@mock_ecr
def test_delete_repository_with_force():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    # when
    # when
    response = client.delete_repository(repositoryName=ECR_REPO, force=True)

    # then
    repo = response["repository"]
    assert repo["repositoryName"] == ECR_REPO
    assert (
        repo["repositoryArn"]
        == f"arn:aws:ecr:us-east-1:{ACCOUNT_ID}:repository/{ECR_REPO}"
    )
    assert repo["registryId"] == ACCOUNT_ID
    assert (
        repo["repositoryUri"]
        == f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/{ECR_REPO}"
    )
    assert isinstance(repo["createdAt"], datetime)
    assert repo["imageTagMutability"] == "MUTABLE"

    response = client.describe_repositories()
    assert len(response["repositories"]) == 0


@mock_ecr
def test_put_image():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")

    response = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    assert response["image"]["imageId"]["imageTag"] == "latest"
    assert "sha" in response["image"]["imageId"]["imageDigest"]
    assert response["image"]["repositoryName"] == "test_repository"
    assert response["image"]["registryId"] == ACCOUNT_ID


@mock_ecr
def test_put_image_without_mediatype():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")

    image_manifest = _create_image_manifest()
    _ = image_manifest.pop("mediaType")

    with pytest.raises(ClientError) as exc:
        client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(image_manifest),
            imageTag="latest",
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "image manifest mediatype not provided in manifest or parameter"
    )


@mock_ecr
def test_put_image_with_imagemanifestmediatype():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")

    image_manifest = _create_image_manifest()
    media_type = image_manifest.pop("mediaType")

    response = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(image_manifest),
        imageManifestMediaType=media_type,
        imageTag="latest",
    )

    assert response["image"]["imageId"]["imageTag"] == "latest"
    assert "sha" in response["image"]["imageId"]["imageDigest"]
    assert response["image"]["repositoryName"] == "test_repository"
    assert response["image"]["imageManifestMediaType"] == media_type
    assert response["image"]["registryId"] == ACCOUNT_ID


@mock_ecr()
def test_put_manifest_list():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")

    manifest_list = _create_image_manifest_list()
    for image_manifest in manifest_list["image_manifests"]:
        _ = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(image_manifest),
        )

    response = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest_list["manifest_list"]),
        imageTag="multiArch",
    )

    assert response["image"]["imageId"]["imageTag"] == "multiArch"
    assert "sha" in response["image"]["imageId"]["imageDigest"]
    assert response["image"]["repositoryName"] == "test_repository"
    assert response["image"]["registryId"] == ACCOUNT_ID
    assert "imageManifest" in response["image"]
    image_manifest = json.loads(response["image"]["imageManifest"])
    assert "mediaType" in image_manifest
    assert "manifests" in image_manifest


@mock_ecr
def test_put_image_with_push_date():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")

    with freeze_time("2018-08-28 00:00:00"):
        image1_date = datetime.now(tzlocal())
        _ = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="first",
        )

    with freeze_time("2019-05-31 00:00:00"):
        image2_date = datetime.now(tzlocal())
        _ = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag="second",
        )

    describe_response = client.describe_images(repositoryName="test_repository")

    assert isinstance(describe_response["imageDetails"], list)
    assert len(describe_response["imageDetails"]) == 2

    assert {
        describe_response["imageDetails"][0]["imagePushedAt"],
        describe_response["imageDetails"][1]["imagePushedAt"],
    } == {image1_date, image2_date}


@mock_ecr
def test_put_image_with_multiple_tags():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")
    manifest = _create_image_manifest()
    response = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest),
        imageTag="v1",
    )

    assert response["image"]["imageId"]["imageTag"] == "v1"
    assert "sha" in response["image"]["imageId"]["imageDigest"]
    assert response["image"]["repositoryName"] == "test_repository"
    assert response["image"]["registryId"] == ACCOUNT_ID

    response1 = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest),
        imageTag="latest",
    )

    assert response1["image"]["imageId"]["imageTag"] == "latest"
    assert "sha" in response1["image"]["imageId"]["imageDigest"]
    assert response1["image"]["repositoryName"] == "test_repository"
    assert response1["image"]["registryId"] == ACCOUNT_ID

    response2 = client.describe_images(repositoryName="test_repository")
    assert isinstance(response2["imageDetails"], list)
    assert len(response2["imageDetails"]) == 1

    assert "sha" in response2["imageDetails"][0]["imageDigest"]

    assert response2["imageDetails"][0]["registryId"] == ACCOUNT_ID
    assert response2["imageDetails"][0]["repositoryName"] == "test_repository"

    assert len(response2["imageDetails"][0]["imageTags"]) == 2
    assert response2["imageDetails"][0]["imageTags"] == ["v1", "latest"]


@mock_ecr
def test_put_multiple_images_with_same_tag():
    image_tag = "my-tag"
    manifest = json.dumps(_create_image_manifest())

    client = boto3.client("ecr", "us-east-1")
    client.create_repository(repositoryName=ECR_REPO)

    image_1 = client.put_image(
        repositoryName=ECR_REPO,
        imageTag=image_tag,
        imageManifest=manifest,
    )["image"]["imageId"]["imageDigest"]

    # We should overwrite the first image because the first image
    # only has one tag

    image_2 = client.put_image(
        repositoryName=ECR_REPO,
        imageTag=image_tag,
        imageManifest=json.dumps(_create_image_manifest()),
    )["image"]["imageId"]["imageDigest"]

    assert image_1 != image_2

    images = client.describe_images(repositoryName=ECR_REPO)["imageDetails"]

    assert len(images) == 1
    assert images[0]["imageDigest"] == image_2

    # Same image with different tags is allowed
    image_3 = client.put_image(
        repositoryName=ECR_REPO,
        imageTag="different-tag",
        imageManifest=manifest,
    )["image"]["imageId"]["imageDigest"]

    images = client.describe_images(repositoryName=ECR_REPO)["imageDetails"]
    assert len(images) == 2
    assert set([img["imageDigest"] for img in images]) == {image_2, image_3}


@mock_ecr
def test_put_same_image_with_same_tag():
    image_tag = "my-tag"
    manifest = json.dumps(_create_image_manifest())

    client = boto3.client("ecr", "us-east-1")
    client.create_repository(repositoryName=ECR_REPO)

    image_1 = client.put_image(
        repositoryName=ECR_REPO,
        imageTag=image_tag,
        imageManifest=manifest,
    )["image"]["imageId"]["imageDigest"]

    with pytest.raises(ClientError) as e:
        client.put_image(
            repositoryName=ECR_REPO,
            imageTag=image_tag,
            imageManifest=manifest,
        )["image"]["imageId"]["imageDigest"]

    ex = e.value
    assert ex.operation_name == "PutImage"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ImageAlreadyExistsException" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"]
        == f"Image with digest '{image_1}' and tag '{image_tag}' already exists in the repository with name '{ECR_REPO}' in registry with id '{ACCOUNT_ID}'"
    )

    images = client.describe_images(repositoryName=ECR_REPO)["imageDetails"]

    assert len(images) == 1


@mock_ecr
def test_multiple_tags__ensure_tags_exist_only_on_one_image():
    tag_to_move = "mock-tag"
    image_manifests = {
        "image_001": json.dumps(_create_image_manifest()),
        "image_002": json.dumps(_create_image_manifest()),
    }

    client = boto3.client("ecr", "us-east-1")
    client.create_repository(repositoryName=ECR_REPO)

    # Create image with unique tag
    for name, manifest in image_manifests.items():
        client.put_image(
            repositoryName=ECR_REPO,
            imageTag=name,
            imageManifest=manifest,
        )

    # Tag first image with shared tag
    client.put_image(
        repositoryName=ECR_REPO,
        imageTag=tag_to_move,
        imageManifest=image_manifests["image_001"],
    )["image"]["imageId"]["imageDigest"]

    # Image can be found
    initial_image, *_ = client.batch_get_image(
        repositoryName=ECR_REPO,
        imageIds=[{"imageTag": tag_to_move}],
    )["images"]
    assert initial_image["imageManifest"] == image_manifests["image_001"]

    # Tag second image with shared tag
    client.put_image(
        repositoryName=ECR_REPO,
        imageTag=tag_to_move,
        imageManifest=image_manifests["image_002"],
    )["image"]["imageId"]["imageDigest"]

    # We should find the second image now - the shared tag should be removed from the first image
    new_image, *_ = client.batch_get_image(
        repositoryName=ECR_REPO,
        imageIds=[{"imageTag": tag_to_move}],
    )["images"]
    assert new_image["imageManifest"] == image_manifests["image_002"]


@mock_ecr
def test_list_images():
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert isinstance(response["imageIds"], list)
    assert len(response["imageIds"]) == 3

    for image in response["imageIds"]:
        assert "sha" in image["imageDigest"]

    image_tags = ["latest", "v1", "v2"]
    assert {
        response["imageIds"][0]["imageTag"],
        response["imageIds"][1]["imageTag"],
        response["imageIds"][2]["imageTag"],
    } == set(image_tags)

    response = client.list_images(repositoryName="test_repository_2")
    assert isinstance(response["imageIds"], list)
    assert len(response["imageIds"]) == 1
    assert response["imageIds"][0]["imageTag"] == "oldest"
    assert "sha" in response["imageIds"][0]["imageDigest"]


@mock_ecr
def test_list_images_from_repository_that_doesnt_exist():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository_1")

    # non existing repo
    with pytest.raises(ClientError) as exc:
        client.list_images(repositoryName="repo-that-doesnt-exist", registryId="123")
    err = exc.value.response["Error"]
    assert err["Code"] == "RepositoryNotFoundException"

    # repo does not exist in specified registry
    with pytest.raises(ClientError) as exc:
        client.list_images(repositoryName="test_repository_1", registryId="222")
    err = exc.value.response["Error"]
    assert err["Code"] == "RepositoryNotFoundException"


@mock_ecr
def test_describe_images():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    manifest_list = _create_image_manifest_list()
    for image_manifest in manifest_list["image_manifests"]:
        _ = client.put_image(
            repositoryName="test_repository",
            imageManifest=json.dumps(image_manifest),
        )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=json.dumps(manifest_list["manifest_list"]),
        imageTag="multiArch",
    )

    response = client.describe_images(repositoryName="test_repository")
    assert isinstance(response["imageDetails"], list)
    assert len(response["imageDetails"]) == 7

    for detail in response["imageDetails"][0:5]:
        assert "distribution.manifest.v2+json" in detail["imageManifestMediaType"]
        assert "sha" in detail["imageDigest"]
        assert detail["registryId"] == ACCOUNT_ID
        assert detail["repositoryName"] == "test_repository"

    assert "imageTags" not in response["imageDetails"][0]
    assert "imageTags" not in response["imageDetails"][4]
    assert "imageTags" not in response["imageDetails"][5]

    assert len(response["imageDetails"][1]["imageTags"]) == 1
    assert len(response["imageDetails"][2]["imageTags"]) == 1
    assert len(response["imageDetails"][3]["imageTags"]) == 1
    assert len(response["imageDetails"][6]["imageTags"]) == 1

    image_tags = ["latest", "v1", "v2"]
    assert {
        response["imageDetails"][1]["imageTags"][0],
        response["imageDetails"][2]["imageTags"][0],
        response["imageDetails"][3]["imageTags"][0],
    } == set(image_tags)

    assert "imageSizeInBytes" not in response["imageDetails"][6]

    assert response["imageDetails"][0]["imageSizeInBytes"] > 0
    assert response["imageDetails"][1]["imageSizeInBytes"] > 0
    assert response["imageDetails"][2]["imageSizeInBytes"] > 0
    assert response["imageDetails"][3]["imageSizeInBytes"] > 0
    assert response["imageDetails"][4]["imageSizeInBytes"] > 0
    assert response["imageDetails"][5]["imageSizeInBytes"] > 0


@mock_ecr
def test_describe_images_by_tag():
    client = boto3.client("ecr", region_name=ECR_REGION)
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
        assert len(response["imageDetails"]) == 1
        image_detail = response["imageDetails"][0]
        assert image_detail["registryId"] == ACCOUNT_ID
        assert image_detail["repositoryName"] == "test_repository"
        assert image_detail["imageTags"] == [put_response["imageId"]["imageTag"]]
        assert image_detail["imageDigest"] == put_response["imageId"]["imageDigest"]


@mock_ecr
def test_describe_images_tags_should_not_contain_empty_tag1():
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert len(response["imageDetails"]) == 1
    image_detail = response["imageDetails"][0]
    assert len(image_detail["imageTags"]) == 3
    assert image_detail["imageTags"] == tags


@mock_ecr
def test_describe_images_tags_should_not_contain_empty_tag2():
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert len(response["imageDetails"]) == 1
    image_detail = response["imageDetails"][0]
    assert len(image_detail["imageTags"]) == 3
    assert image_detail["imageTags"] == ["v1", "v2", "latest"]


@mock_ecr
def test_describe_repository_that_doesnt_exist():
    client = boto3.client("ecr", region_name=ECR_REGION)

    with pytest.raises(ClientError) as exc:
        client.describe_repositories(
            repositoryNames=["repo-that-doesnt-exist"], registryId="123"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "RepositoryNotFoundException"


@mock_ecr
def test_describe_image_that_doesnt_exist():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName="test_repository")

    with pytest.raises(ClientError) as exc:
        client.describe_images(
            repositoryName="test_repository",
            imageIds=[{"imageTag": "testtag"}],
            registryId=ACCOUNT_ID,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ImageNotFoundException"

    with pytest.raises(ClientError) as exc:
        client.describe_images(
            repositoryName="repo-that-doesnt-exist",
            imageIds=[{"imageTag": "testtag"}],
            registryId=ACCOUNT_ID,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "RepositoryNotFoundException"


@mock_ecr
def test_delete_repository_that_doesnt_exist():
    client = boto3.client("ecr", region_name=ECR_REGION)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository(repositoryName=ECR_REPO_NOT_EXIST)

    # then
    ex = e.value
    assert ex.operation_name == "DeleteRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_repository_error_not_empty():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository(repositoryName=ECR_REPO)

    # then
    ex = e.value
    assert ex.operation_name == "DeleteRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotEmptyException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO}' in registry with id '{ACCOUNT_ID}' cannot be deleted because it still contains images"
    )


@mock_ecr
def test_describe_images_by_digest():
    client = boto3.client("ecr", region_name=ECR_REGION)
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
        assert len(response["imageDetails"]) == 1
        image_detail = response["imageDetails"][0]
        assert image_detail["registryId"] == ACCOUNT_ID
        assert image_detail["repositoryName"] == "test_repository"
        assert image_detail["imageTags"] == [put_response["imageId"]["imageTag"]]
        assert image_detail["imageDigest"] == digest


@mock_ecr
def test_get_authorization_token_assume_region():
    client = boto3.client("ecr", region_name=ECR_REGION)
    auth_token_response = client.get_authorization_token()

    assert "authorizationData" in auth_token_response
    assert "ResponseMetadata" in auth_token_response
    assert auth_token_response["authorizationData"] == [
        {
            "authorizationToken": "QVdTOjEyMzQ1Njc4OTAxMi1hdXRoLXRva2Vu",
            "proxyEndpoint": f"https://{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com",
            "expiresAt": datetime(2015, 1, 1, tzinfo=tzlocal()),
        }
    ]


@mock_ecr
def test_get_authorization_token_explicit_regions():
    client = boto3.client("ecr", region_name=ECR_REGION)
    auth_token_response = client.get_authorization_token(
        registryIds=["10987654321", "878787878787"]
    )

    assert "authorizationData" in auth_token_response
    assert "ResponseMetadata" in auth_token_response
    assert auth_token_response["authorizationData"] == [
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


@mock_ecr
def test_batch_get_image():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(response["images"], list)
    assert len(response["images"]) == 1

    assert (
        "vnd.docker.distribution.manifest.v2+json"
        in response["images"][0]["imageManifest"]
    )
    assert response["images"][0]["registryId"] == ACCOUNT_ID
    assert response["images"][0]["repositoryName"] == "test_repository"

    assert response["images"][0]["imageId"]["imageTag"] == "v2"
    assert "sha" in response["images"][0]["imageId"]["imageDigest"]

    assert isinstance(response["failures"], list)
    assert len(response["failures"]) == 0


@mock_ecr
def test_batch_get_image_that_doesnt_exist():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(response["images"], list)
    assert len(response["images"]) == 0

    assert isinstance(response["failures"], list)
    assert len(response["failures"]) == 1
    assert response["failures"][0]["failureReason"] == "Requested image not found"
    assert response["failures"][0]["failureCode"] == "ImageNotFound"
    assert response["failures"][0]["imageId"]["imageTag"] == "v5"


@mock_ecr
def test_batch_get_image_with_multiple_tags():
    client = boto3.client("ecr", region_name=ECR_REGION)
    _ = client.create_repository(repositoryName="test_repository")

    manifest = json.dumps(_create_image_manifest())
    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=manifest,
        imageTag="latest",
    )

    _ = client.put_image(
        repositoryName="test_repository",
        imageManifest=manifest,
        imageTag="v1",
    )

    latest_response = client.batch_get_image(
        repositoryName="test_repository", imageIds=[{"imageTag": "latest"}]
    )

    v1_response = client.batch_get_image(
        repositoryName="test_repository", imageIds=[{"imageTag": "v1"}]
    )

    assert (
        latest_response["images"][0]["imageManifest"]
        == v1_response["images"][0]["imageManifest"]
    )


@mock_ecr
def test_batch_delete_image_by_tag():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(describe_response1["imageDetails"][0]["imageTags"], list)
    assert len(describe_response1["imageDetails"][0]["imageTags"]) == 3

    assert isinstance(describe_response2["imageDetails"][0]["imageTags"], list)
    assert len(describe_response2["imageDetails"][0]["imageTags"]) == 2

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 1

    assert batch_delete_response["imageIds"][0]["imageTag"] == "latest"

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 0


@mock_ecr
def test_batch_delete_image_delete_last_tag():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(describe_response1["imageDetails"][0]["imageTags"], list)
    assert len(describe_response1["imageDetails"][0]["imageTags"]) == 1

    assert isinstance(describe_response2["imageDetails"], list)
    assert len(describe_response2["imageDetails"]) == 0

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 1

    assert batch_delete_response["imageIds"][0]["imageTag"] == "v1"

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 0


@mock_ecr
def test_batch_delete_image_with_nonexistent_tag():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(describe_response["imageDetails"][0]["imageTags"], list)
    assert len(describe_response["imageDetails"][0]["imageTags"]) == 3

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 0

    assert batch_delete_response["failures"][0]["imageId"]["imageTag"] == missing_tag
    assert batch_delete_response["failures"][0]["failureCode"] == "ImageNotFound"
    assert (
        batch_delete_response["failures"][0]["failureReason"]
        == "Requested image not found"
    )

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 1


@mock_ecr
def test_batch_delete_image_by_digest():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(describe_response["imageDetails"], list)
    assert len(describe_response["imageDetails"]) == 0

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 3

    assert batch_delete_response["imageIds"][0]["imageDigest"] == image_digest
    assert batch_delete_response["imageIds"][1]["imageDigest"] == image_digest
    assert batch_delete_response["imageIds"][2]["imageDigest"] == image_digest

    assert {
        batch_delete_response["imageIds"][0]["imageTag"],
        batch_delete_response["imageIds"][1]["imageTag"],
        batch_delete_response["imageIds"][2]["imageTag"],
    } == set(tags)

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 0


@mock_ecr
def test_batch_delete_image_with_invalid_digest():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 0

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 1

    assert (
        batch_delete_response["failures"][0]["imageId"]["imageDigest"]
        == invalid_image_digest
    )
    assert batch_delete_response["failures"][0]["failureCode"] == "InvalidImageDigest"
    assert (
        batch_delete_response["failures"][0]["failureReason"]
        == "Invalid request parameters: image digest should satisfy the regex '[a-zA-Z0-9-_+.]+:[a-fA-F0-9]+'"
    )


@mock_ecr
def test_batch_delete_image_with_missing_parameters():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName="test_repository")

    batch_delete_response = client.batch_delete_image(
        registryId="012345678910", repositoryName="test_repository", imageIds=[{}]
    )

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 0

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 1

    assert batch_delete_response["failures"][0]["failureCode"] == "MissingDigestAndTag"
    assert (
        batch_delete_response["failures"][0]["failureReason"]
        == "Invalid request parameters: both tag and digest cannot be null"
    )


@mock_ecr
def test_batch_delete_image_with_matching_digest_and_tag():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(describe_response["imageDetails"], list)
    assert len(describe_response["imageDetails"]) == 0

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 3

    assert batch_delete_response["imageIds"][0]["imageDigest"] == image_digest
    assert batch_delete_response["imageIds"][1]["imageDigest"] == image_digest
    assert batch_delete_response["imageIds"][2]["imageDigest"] == image_digest

    assert {
        batch_delete_response["imageIds"][0]["imageTag"],
        batch_delete_response["imageIds"][1]["imageTag"],
        batch_delete_response["imageIds"][2]["imageTag"],
    } == set(tags)

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 0


@mock_ecr
def test_batch_delete_image_with_mismatched_digest_and_tag():
    client = boto3.client("ecr", region_name=ECR_REGION)
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

    assert isinstance(batch_delete_response["imageIds"], list)
    assert len(batch_delete_response["imageIds"]) == 0

    assert isinstance(batch_delete_response["failures"], list)
    assert len(batch_delete_response["failures"]) == 1

    assert (
        batch_delete_response["failures"][0]["imageId"]["imageDigest"] == image_digest
    )
    assert batch_delete_response["failures"][0]["imageId"]["imageTag"] == "v2"
    assert batch_delete_response["failures"][0]["failureCode"] == "ImageNotFound"
    assert (
        batch_delete_response["failures"][0]["failureReason"]
        == "Requested image not found"
    )


@mock_ecr
def test_delete_batch_image_with_multiple_images():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    # Populate mock repo with images
    for i in range(10):
        client.put_image(
            repositoryName=ECR_REPO,
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag=f"tag{i}",
        )

    # Pull down image digests for each image in the mock repo
    repo_images = client.describe_images(repositoryName=ECR_REPO)["imageDetails"]
    image_digests = [{"imageDigest": image["imageDigest"]} for image in repo_images]

    # Pick a couple of images to delete
    images_to_delete = image_digests[5:7]

    # Delete the images
    response = client.batch_delete_image(
        repositoryName=ECR_REPO, imageIds=images_to_delete
    )
    assert len(response["imageIds"]) == 2
    assert response["failures"] == []

    # Verify other images still exist
    repo_images = client.describe_images(repositoryName=ECR_REPO)["imageDetails"]
    image_tags = [img["imageTags"][0] for img in repo_images]
    assert image_tags == [
        "tag0",
        "tag1",
        "tag2",
        "tag3",
        "tag4",
        "tag7",
        "tag8",
        "tag9",
    ]


@mock_ecr
def test_list_tags_for_resource():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    arn = client.create_repository(
        repositoryName=ECR_REPO, tags=[{"Key": "key-1", "Value": "value-1"}]
    )["repository"]["repositoryArn"]

    # when
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]

    # then
    assert tags == [{"Key": "key-1", "Value": "value-1"}]


@mock_ecr
def test_list_tags_for_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(
            resourceArn=f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{ECR_REPO}"
        )

    # then
    ex = e.value
    assert ex.operation_name == "ListTagsForResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_list_tags_for_resource_error_invalid_param():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(resourceArn="invalid")

    # then
    ex = e.value
    assert ex.operation_name == "ListTagsForResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Invalid parameter at 'resourceArn' failed to satisfy constraint: 'Invalid ARN'"
    )


@mock_ecr
def test_tag_resource():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    arn = client.create_repository(
        repositoryName=ECR_REPO, tags=[{"Key": "key-1", "Value": "value-1"}]
    )["repository"]["repositoryArn"]

    # when
    client.tag_resource(resourceArn=arn, tags=[{"Key": "key-2", "Value": "value-2"}])

    # then
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert sorted(tags, key=lambda i: i["Key"]) == [
        {"Key": "key-1", "Value": "value-1"},
        {"Key": "key-2", "Value": "value-2"},
    ]


@mock_ecr
def test_tag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            resourceArn=f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{ECR_REPO}",
            tags=[{"Key": "key-1", "Value": "value-2"}],
        )

    # then
    ex = e.value
    assert ex.operation_name == "TagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_untag_resource():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    arn = client.create_repository(
        repositoryName=ECR_REPO,
        tags=[
            {"Key": "key-1", "Value": "value-1"},
            {"Key": "key-2", "Value": "value-2"},
        ],
    )["repository"]["repositoryArn"]

    # when
    client.untag_resource(resourceArn=arn, tagKeys=["key-1"])

    # then
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags == [{"Key": "key-2", "Value": "value-2"}]


@mock_ecr
def test_untag_resource_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.untag_resource(
            resourceArn=f"arn:aws:ecr:{region_name}:{ACCOUNT_ID}:repository/{ECR_REPO}",
            tagKeys=["key-1"],
        )

    # then
    ex = e.value
    assert ex.operation_name == "UntagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_image_tag_mutability():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    response = client.describe_repositories(repositoryNames=[ECR_REPO])
    assert response["repositories"][0]["imageTagMutability"] == "MUTABLE"

    # when
    response = client.put_image_tag_mutability(
        repositoryName=ECR_REPO, imageTagMutability="IMMUTABLE"
    )

    # then
    assert response["imageTagMutability"] == "IMMUTABLE"
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO

    response = client.describe_repositories(repositoryNames=[ECR_REPO])
    assert response["repositories"][0]["imageTagMutability"] == "IMMUTABLE"


@mock_ecr
def test_put_image_tag_mutability_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.put_image_tag_mutability(
            repositoryName=ECR_REPO_NOT_EXIST, imageTagMutability="IMMUTABLE"
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutImageTagMutability"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_image_tag_mutability_error_invalid_param():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    with pytest.raises(ClientError) as e:
        client.put_image_tag_mutability(
            repositoryName=ECR_REPO, imageTagMutability="invalid"
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutImageTagMutability"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Invalid parameter at 'imageTagMutability' failed to satisfy constraint: 'Member must satisfy enum value set: [IMMUTABLE, MUTABLE]'"
    )


@mock_ecr
def test_put_image_scanning_configuration():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    response = client.describe_repositories(repositoryNames=[ECR_REPO])
    assert response["repositories"][0]["imageScanningConfiguration"] == {
        "scanOnPush": False
    }

    # when
    response = client.put_image_scanning_configuration(
        repositoryName=ECR_REPO, imageScanningConfiguration={"scanOnPush": True}
    )

    # then
    assert response["imageScanningConfiguration"] == {"scanOnPush": True}
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO

    response = client.describe_repositories(repositoryNames=[ECR_REPO])
    assert response["repositories"][0]["imageScanningConfiguration"] == {
        "scanOnPush": True
    }


@mock_ecr
def test_put_image_scanning_configuration_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.put_image_scanning_configuration(
            repositoryName=ECR_REPO_NOT_EXIST,
            imageScanningConfiguration={"scanOnPush": True},
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutImageScanningConfiguration"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_set_repository_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
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
        repositoryName=ECR_REPO, policyText=json.dumps(policy)
    )

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert json.loads(response["policyText"]) == policy


@mock_ecr
def test_set_repository_policy_error_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
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
            repositoryName=ECR_REPO_NOT_EXIST, policyText=json.dumps(policy)
        )

    # then
    ex = e.value
    assert ex.operation_name == "SetRepositoryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_set_repository_policy_error_invalid_param():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    client.create_repository(repositoryName=ECR_REPO)
    policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow"}],
    }

    # when
    with pytest.raises(ClientError) as e:
        client.set_repository_policy(
            repositoryName=ECR_REPO, policyText=json.dumps(policy)
        )

    # then
    ex = e.value
    assert ex.operation_name == "SetRepositoryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Invalid parameter at 'PolicyText' failed to satisfy constraint: 'Invalid repository policy provided'"
    )


@mock_ecr
def test_get_repository_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
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
    client.set_repository_policy(repositoryName=ECR_REPO, policyText=json.dumps(policy))

    # when
    response = client.get_repository_policy(repositoryName=ECR_REPO)

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert json.loads(response["policyText"]) == policy


@mock_ecr
def test_get_repository_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.get_repository_policy(repositoryName=ECR_REPO_NOT_EXIST)

    # then
    ex = e.value
    assert ex.operation_name == "GetRepositoryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_get_repository_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    with pytest.raises(ClientError) as e:
        client.get_repository_policy(repositoryName=ECR_REPO)

    # then
    ex = e.value
    assert ex.operation_name == "GetRepositoryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryPolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Repository policy does not exist for the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_repository_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
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
    client.set_repository_policy(repositoryName=ECR_REPO, policyText=json.dumps(policy))

    # when
    response = client.delete_repository_policy(repositoryName=ECR_REPO)

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert json.loads(response["policyText"]) == policy

    with pytest.raises(ClientError) as e:
        client.get_repository_policy(repositoryName=ECR_REPO)

    assert e.value.response["Error"]["Code"] == "RepositoryPolicyNotFoundException"


@mock_ecr
def test_delete_repository_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository_policy(repositoryName=ECR_REPO_NOT_EXIST)

    # then
    ex = e.value
    assert ex.operation_name == "DeleteRepositoryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_repository_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_repository_policy(repositoryName=ECR_REPO)

    # then
    ex = e.value
    assert ex.operation_name == "DeleteRepositoryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryPolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Repository policy does not exist for the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_lifecycle_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
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
        repositoryName=ECR_REPO, lifecyclePolicyText=json.dumps(policy)
    )

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert json.loads(response["lifecyclePolicyText"]) == policy


@mock_ecr
def test_put_lifecycle_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
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
            repositoryName=ECR_REPO_NOT_EXIST, lifecyclePolicyText=json.dumps(policy)
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutLifecyclePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_get_lifecycle_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
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
        repositoryName=ECR_REPO, lifecyclePolicyText=json.dumps(policy)
    )

    # when
    response = client.get_lifecycle_policy(repositoryName=ECR_REPO)

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert json.loads(response["lifecyclePolicyText"]) == policy
    assert isinstance(response["lastEvaluatedAt"], datetime)


@mock_ecr
def test_get_lifecycle_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.get_lifecycle_policy(repositoryName=ECR_REPO_NOT_EXIST)

    # then
    ex = e.value
    assert ex.operation_name == "GetLifecyclePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_get_lifecycle_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    with pytest.raises(ClientError) as e:
        client.get_lifecycle_policy(repositoryName=ECR_REPO)

    # then
    ex = e.value
    assert ex.operation_name == "GetLifecyclePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "LifecyclePolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Lifecycle policy does not exist for the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_lifecycle_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
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
        repositoryName=ECR_REPO, lifecyclePolicyText=json.dumps(policy)
    )

    # when
    response = client.delete_lifecycle_policy(repositoryName=ECR_REPO)

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert json.loads(response["lifecyclePolicyText"]) == policy
    assert isinstance(response["lastEvaluatedAt"], datetime)

    with pytest.raises(ClientError) as e:
        client.get_lifecycle_policy(repositoryName=ECR_REPO)

    assert e.value.response["Error"]["Code"] == "LifecyclePolicyNotFoundException"


@mock_ecr
def test_delete_lifecycle_policy_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_lifecycle_policy(repositoryName=ECR_REPO_NOT_EXIST)

    # then
    ex = e.value
    assert ex.operation_name == "DeleteLifecyclePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_lifecycle_policy_error_policy_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)
    client.create_repository(repositoryName=ECR_REPO)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_lifecycle_policy(repositoryName=ECR_REPO)

    # then
    ex = e.value
    assert ex.operation_name == "DeleteLifecyclePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "LifecyclePolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Lifecycle policy does not exist for the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
@pytest.mark.parametrize(
    "actions",
    ["ecr:CreateRepository", ["ecr:CreateRepository", "ecr:ReplicateImage"]],
    ids=["single-action", "multiple-actions"],
)
def test_put_registry_policy(actions):
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": ["arn:aws:iam::111111111111:root", "222222222222"]
                },
                "Action": actions,
                "Resource": "*",
            }
        ],
    }

    # when
    response = client.put_registry_policy(policyText=json.dumps(policy))

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert json.loads(response["policyText"]) == policy


@mock_ecr
def test_put_registry_policy_error_invalid_action():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert ex.operation_name == "PutRegistryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Invalid parameter at 'PolicyText' failed to satisfy constraint: 'Invalid registry policy provided'"
    )


@mock_ecr
def test_get_registry_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert response["registryId"] == ACCOUNT_ID
    assert json.loads(response["policyText"]) == policy


@mock_ecr
def test_get_registry_policy_error_policy_not_exists():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)

    # when
    with pytest.raises(ClientError) as e:
        client.get_registry_policy()

    # then
    ex = e.value
    assert ex.operation_name == "GetRegistryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RegistryPolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Registry policy does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_delete_registry_policy():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert response["registryId"] == ACCOUNT_ID
    assert json.loads(response["policyText"]) == policy

    with pytest.raises(ClientError) as e:
        client.get_registry_policy()

    assert e.value.response["Error"]["Code"] == "RegistryPolicyNotFoundException"


@mock_ecr
def test_delete_registry_policy_error_policy_not_exists():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)

    # when
    with pytest.raises(ClientError) as e:
        client.delete_registry_policy()

    # then
    ex = e.value
    assert ex.operation_name == "DeleteRegistryPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RegistryPolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Registry policy does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_tag = "latest"
    image_digest = client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]

    # when
    response = client.start_image_scan(
        repositoryName=ECR_REPO, imageId={"imageTag": image_tag}
    )

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert response["imageId"] == {"imageDigest": image_digest, "imageTag": image_tag}
    assert response["imageScanStatus"] == {"status": "IN_PROGRESS"}


@mock_ecr
def test_start_image_scan_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=ECR_REPO_NOT_EXIST, imageId={"imageTag": "latest"}
        )

    # then
    ex = e.value
    assert ex.operation_name == "StartImageScan"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan_error_image_not_exists():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_tag = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=ECR_REPO, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    assert ex.operation_name == "StartImageScan"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ImageNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The image with imageId {{imageDigest:'null', imageTag:'{image_tag}'}} does not exist within the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan_error_image_tag_digest_mismatch():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_digest = client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]
    image_tag = "not-latest"

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=ECR_REPO,
            imageId={"imageTag": image_tag, "imageDigest": image_digest},
        )

    # then
    ex = e.value
    assert ex.operation_name == "StartImageScan"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ImageNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The image with imageId {{imageDigest:'{image_digest}', imageTag:'{image_tag}'}} does not exist within the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_start_image_scan_error_daily_limit():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_tag = "latest"
    client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )
    client.start_image_scan(repositoryName=ECR_REPO, imageId={"imageTag": image_tag})

    # when
    with pytest.raises(ClientError) as e:
        client.start_image_scan(
            repositoryName=ECR_REPO, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    assert ex.operation_name == "StartImageScan"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "LimitExceededException"
    assert (
        ex.response["Error"]["Message"]
        == "The scan quota per image has been exceeded. Wait and try again."
    )


@mock_ecr
def test_describe_image_scan_findings():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_tag = "latest"
    image_digest = client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )["image"]["imageId"]["imageDigest"]
    client.start_image_scan(repositoryName=ECR_REPO, imageId={"imageTag": image_tag})

    # when
    response = client.describe_image_scan_findings(
        repositoryName=ECR_REPO, imageId={"imageTag": image_tag}
    )

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["repositoryName"] == ECR_REPO
    assert response["imageId"] == {"imageDigest": image_digest, "imageTag": image_tag}
    assert response["imageScanStatus"] == {
        "status": "COMPLETE",
        "description": "The scan was completed successfully.",
    }
    scan_findings = response["imageScanFindings"]
    assert isinstance(scan_findings["imageScanCompletedAt"], datetime)
    assert isinstance(scan_findings["vulnerabilitySourceUpdatedAt"], datetime)
    assert scan_findings["findings"] == [
        {
            "name": "CVE-9999-9999",
            "uri": "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-9999-9999",
            "severity": "HIGH",
            "attributes": [
                {"key": "package_version", "value": "9.9.9"},
                {"key": "package_name", "value": "moto_fake"},
                {"key": "CVSS2_VECTOR", "value": "AV:N/AC:L/Au:N/C:P/I:P/A:P"},
                {"key": "CVSS2_SCORE", "value": "7.5"},
            ],
        }
    ]
    assert scan_findings["findingSeverityCounts"] == {"HIGH": 1}


@mock_ecr
def test_describe_image_scan_findings_error_repo_not_exists():
    # given
    region_name = "eu-central-1"
    client = boto3.client("ecr", region_name=region_name)

    # when
    with pytest.raises(ClientError) as e:
        client.describe_image_scan_findings(
            repositoryName=ECR_REPO_NOT_EXIST, imageId={"imageTag": "latest"}
        )

    # then
    ex = e.value
    assert ex.operation_name == "DescribeImageScanFindings"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The repository with name '{ECR_REPO_NOT_EXIST}' does not exist in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_describe_image_scan_findings_error_image_not_exists():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_tag = "not-exists"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_image_scan_findings(
            repositoryName=ECR_REPO, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    assert ex.operation_name == "DescribeImageScanFindings"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ImageNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"The image with imageId {{imageDigest:'null', imageTag:'{image_tag}'}} does not exist within the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_describe_image_scan_findings_error_scan_not_exists():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)
    image_tag = "latest"
    client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag=image_tag,
    )

    # when
    with pytest.raises(ClientError) as e:
        client.describe_image_scan_findings(
            repositoryName=ECR_REPO, imageId={"imageTag": image_tag}
        )

    # then
    ex = e.value
    assert ex.operation_name == "DescribeImageScanFindings"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ScanNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == f"Image scan does not exist for the image with '{{imageDigest:'null', imageTag:'{image_tag}'}}' in the repository with name '{ECR_REPO}' in the registry with id '{ACCOUNT_ID}'"
    )


@mock_ecr
def test_put_replication_configuration():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    config = {
        "rules": [{"destinations": [{"region": "eu-west-1", "registryId": ACCOUNT_ID}]}]
    }

    # when
    response = client.put_replication_configuration(replicationConfiguration=config)

    # then
    assert response["replicationConfiguration"] == config


@mock_ecr
def test_put_replication_configuration_error_feature_disabled():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
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
    assert ex.operation_name == "PutReplicationConfiguration"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ValidationException"
    assert ex.response["Error"]["Message"] == "This feature is disabled"


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
    assert ex.operation_name == "PutReplicationConfiguration"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Invalid parameter at 'replicationConfiguration' failed to satisfy constraint: 'Replication destination cannot be the same as the source registry'"
    )


@mock_ecr
def test_describe_registry():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)

    # when
    response = client.describe_registry()

    # then
    assert response["registryId"] == ACCOUNT_ID
    assert response["replicationConfiguration"] == {"rules": []}


@mock_ecr
def test_describe_registry_after_update():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    config = {
        "rules": [
            {"destinations": [{"region": "eu-west-1", "registryId": ACCOUNT_ID}]},
        ]
    }
    client.put_replication_configuration(replicationConfiguration=config)

    # when
    response = client.describe_registry()

    # then
    assert response["replicationConfiguration"] == config


@mock_ecr
def test_ecr_image_digest():
    # given
    client = boto3.client("ecr", region_name=ECR_REGION)
    digest = "sha256:826b6832e45ba17d625debc95ae8554e148550b00c05b47fa8f7be1c555bc83c"
    client.create_repository(repositoryName=ECR_REPO)
    image_manifest = {
        "config": {
            "digest": "sha256:6442bc26a7c562f5afe6467dab36365c709909f6a81afcecfc0c25cff0f1bab0",
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 5205,
        },
        "layers": [
            {
                "digest": "sha256:b35e87b5838011a3637be660e4238af9a55e4edc74404c990f7a558e7f416658",
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 26690191,
            }
        ],
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "schemaVersion": 2,
    }

    # when
    put_response = client.put_image(
        repositoryName=ECR_REPO,
        imageManifest=json.dumps(image_manifest),
        imageManifestMediaType="application/vnd.oci.image.manifest.v1+json",
        imageTag="test1",
        imageDigest=digest,
    )
    describe_response = client.describe_images(repositoryName=ECR_REPO)

    # then
    assert put_response["image"]["imageId"]["imageDigest"] == digest
    assert describe_response["imageDetails"][0]["imageDigest"] == digest
