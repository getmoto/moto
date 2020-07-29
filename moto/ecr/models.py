from __future__ import unicode_literals

import hashlib
import re
from datetime import datetime
from random import random

from botocore.exceptions import ParamValidationError

from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.ec2 import ec2_backends
from moto.ecr.exceptions import ImageNotFoundException, RepositoryNotFoundException

DEFAULT_REGISTRY_ID = "012345678910"


class BaseObject(BaseModel):
    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split("_")):
            if i > 0:
                words.append(word.title())
            else:
                words.append(word)
        return "".join(words)

    def gen_response_object(self):
        response_object = dict()
        for key, value in self.__dict__.items():
            if "_" in key:
                response_object[self.camelCase(key)] = value
            else:
                response_object[key] = value
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class Repository(BaseObject, CloudFormationModel):
    def __init__(self, repository_name):
        self.registry_id = DEFAULT_REGISTRY_ID
        self.arn = "arn:aws:ecr:us-east-1:{0}:repository/{1}".format(
            self.registry_id, repository_name
        )
        self.name = repository_name
        # self.created = datetime.utcnow()
        self.uri = "{0}.dkr.ecr.us-east-1.amazonaws.com/{1}".format(
            self.registry_id, repository_name
        )
        self.images = []

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def response_object(self):
        response_object = self.gen_response_object()

        response_object["registryId"] = self.registry_id
        response_object["repositoryArn"] = self.arn
        response_object["repositoryName"] = self.name
        response_object["repositoryUri"] = self.uri
        # response_object['createdAt'] = self.created
        del response_object["arn"], response_object["name"], response_object["images"]
        return response_object

    @staticmethod
    def cloudformation_name_type():
        return "RepositoryName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecr-repository.html
        return "AWS::ECR::Repository"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        ecr_backend = ecr_backends[region_name]
        return ecr_backend.create_repository(
            # RepositoryName is optional in CloudFormation, thus create a random
            # name if necessary
            repository_name=properties.get(
                "RepositoryName", "ecrrepository{0}".format(int(random() * 10 ** 6))
            )
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        if original_resource.name != properties["RepositoryName"]:
            ecr_backend = ecr_backends[region_name]
            ecr_backend.delete_cluster(original_resource.arn)
            return ecr_backend.create_repository(
                # RepositoryName is optional in CloudFormation, thus create a
                # random name if necessary
                repository_name=properties.get(
                    "RepositoryName",
                    "RepositoryName{0}".format(int(random() * 10 ** 6)),
                )
            )
        else:
            # no-op when nothing changed between old and new resources
            return original_resource


class Image(BaseObject):
    def __init__(
        self, tag, manifest, repository, digest=None, registry_id=DEFAULT_REGISTRY_ID
    ):
        self.image_tag = tag
        self.image_tags = [tag] if tag is not None else []
        self.image_manifest = manifest
        self.image_size_in_bytes = 50 * 1024 * 1024
        self.repository = repository
        self.registry_id = registry_id
        self.image_digest = digest
        self.image_pushed_at = str(datetime.utcnow().isoformat())

    def _create_digest(self):
        image_contents = "docker_image{0}".format(int(random() * 10 ** 6))
        self.image_digest = (
            "sha256:%s" % hashlib.sha256(image_contents.encode("utf-8")).hexdigest()
        )

    def get_image_digest(self):
        if not self.image_digest:
            self._create_digest()
        return self.image_digest

    def get_image_manifest(self):
        return self.image_manifest

    def remove_tag(self, tag):
        if tag is not None and tag in self.image_tags:
            self.image_tags.remove(tag)
            if self.image_tags:
                self.image_tag = self.image_tags[-1]

    def update_tag(self, tag):
        self.image_tag = tag
        if tag not in self.image_tags and tag is not None:
            self.image_tags.append(tag)

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["imageId"] = {}
        response_object["imageId"]["imageTag"] = self.image_tag
        response_object["imageId"]["imageDigest"] = self.get_image_digest()
        response_object["imageManifest"] = self.image_manifest
        response_object["repositoryName"] = self.repository
        response_object["registryId"] = self.registry_id
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_list_object(self):
        response_object = self.gen_response_object()
        response_object["imageTag"] = self.image_tag
        response_object["imageDigest"] = "i don't know"
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_describe_object(self):
        response_object = self.gen_response_object()
        response_object["imageTags"] = self.image_tags
        response_object["imageDigest"] = self.get_image_digest()
        response_object["imageManifest"] = self.image_manifest
        response_object["repositoryName"] = self.repository
        response_object["registryId"] = self.registry_id
        response_object["imageSizeInBytes"] = self.image_size_in_bytes
        response_object["imagePushedAt"] = self.image_pushed_at
        return {k: v for k, v in response_object.items() if v is not None and v != []}

    @property
    def response_batch_get_image(self):
        response_object = {}
        response_object["imageId"] = {}
        response_object["imageId"]["imageTag"] = self.image_tag
        response_object["imageId"]["imageDigest"] = self.get_image_digest()
        response_object["imageManifest"] = self.image_manifest
        response_object["repositoryName"] = self.repository
        response_object["registryId"] = self.registry_id
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_batch_delete_image(self):
        response_object = {}
        response_object["imageDigest"] = self.get_image_digest()
        response_object["imageTag"] = self.image_tag
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }


class ECRBackend(BaseBackend):
    def __init__(self):
        self.repositories = {}

    def describe_repositories(self, registry_id=None, repository_names=None):
        """
        maxResults and nextToken not implemented
        """
        if repository_names:
            for repository_name in repository_names:
                if repository_name not in self.repositories:
                    raise RepositoryNotFoundException(
                        repository_name, registry_id or DEFAULT_REGISTRY_ID
                    )

        repositories = []
        for repository in self.repositories.values():
            # If a registry_id was supplied, ensure this repository matches
            if registry_id:
                if repository.registry_id != registry_id:
                    continue
            # If a list of repository names was supplied, esure this repository
            # is in that list
            if repository_names:
                if repository.name not in repository_names:
                    continue
            repositories.append(repository.response_object)
        return repositories

    def create_repository(self, repository_name):
        repository = Repository(repository_name)
        self.repositories[repository_name] = repository
        return repository

    def delete_repository(self, repository_name, registry_id=None):
        if repository_name in self.repositories:
            return self.repositories.pop(repository_name)
        else:
            raise RepositoryNotFoundException(
                repository_name, registry_id or DEFAULT_REGISTRY_ID
            )

    def list_images(self, repository_name, registry_id=None):
        """
        maxResults and filtering not implemented
        """
        repository = None
        found = False
        if repository_name in self.repositories:
            repository = self.repositories[repository_name]
            if registry_id:
                if repository.registry_id == registry_id:
                    found = True
            else:
                found = True

        if not found:
            raise RepositoryNotFoundException(
                repository_name, registry_id or DEFAULT_REGISTRY_ID
            )

        images = []
        for image in repository.images:
            images.append(image)
        return images

    def describe_images(self, repository_name, registry_id=None, image_ids=None):

        if repository_name in self.repositories:
            repository = self.repositories[repository_name]
        else:
            raise RepositoryNotFoundException(
                repository_name, registry_id or DEFAULT_REGISTRY_ID
            )

        if image_ids:
            response = set()
            for image_id in image_ids:
                found = False
                for image in repository.images:
                    if (
                        "imageDigest" in image_id
                        and image.get_image_digest() == image_id["imageDigest"]
                    ) or (
                        "imageTag" in image_id
                        and image_id["imageTag"] in image.image_tags
                    ):
                        found = True
                        response.add(image)
                if not found:
                    image_id_representation = "{imageDigest:'%s', imageTag:'%s'}" % (
                        image_id.get("imageDigest", "null"),
                        image_id.get("imageTag", "null"),
                    )
                    raise ImageNotFoundException(
                        image_id=image_id_representation,
                        repository_name=repository_name,
                        registry_id=registry_id or DEFAULT_REGISTRY_ID,
                    )

        else:
            response = []
            for image in repository.images:
                response.append(image)

        return response

    def put_image(self, repository_name, image_manifest, image_tag):
        if repository_name in self.repositories:
            repository = self.repositories[repository_name]
        else:
            raise Exception("{0} is not a repository".format(repository_name))

        existing_images = list(
            filter(
                lambda x: x.response_object["imageManifest"] == image_manifest,
                repository.images,
            )
        )
        if not existing_images:
            # this image is not in ECR yet
            image = Image(image_tag, image_manifest, repository_name)
            repository.images.append(image)
            return image
        else:
            # update existing image
            existing_images[0].update_tag(image_tag)
            return existing_images[0]

    def batch_get_image(
        self,
        repository_name,
        registry_id=None,
        image_ids=None,
        accepted_media_types=None,
    ):
        if repository_name in self.repositories:
            repository = self.repositories[repository_name]
        else:
            raise RepositoryNotFoundException(
                repository_name, registry_id or DEFAULT_REGISTRY_ID
            )

        if not image_ids:
            raise ParamValidationError(
                msg='Missing required parameter in input: "imageIds"'
            )

        response = {"images": [], "failures": []}

        for image_id in image_ids:
            found = False
            for image in repository.images:
                if (
                    "imageDigest" in image_id
                    and image.get_image_digest() == image_id["imageDigest"]
                ) or (
                    "imageTag" in image_id and image.image_tag == image_id["imageTag"]
                ):
                    found = True
                    response["images"].append(image.response_batch_get_image)

        if not found:
            response["failures"].append(
                {
                    "imageId": {"imageTag": image_id.get("imageTag", "null")},
                    "failureCode": "ImageNotFound",
                    "failureReason": "Requested image not found",
                }
            )

        return response

    def batch_delete_image(self, repository_name, registry_id=None, image_ids=None):
        if repository_name in self.repositories:
            repository = self.repositories[repository_name]
        else:
            raise RepositoryNotFoundException(
                repository_name, registry_id or DEFAULT_REGISTRY_ID
            )

        if not image_ids:
            raise ParamValidationError(
                msg='Missing required parameter in input: "imageIds"'
            )

        response = {"imageIds": [], "failures": []}

        for image_id in image_ids:
            image_found = False

            # Is request missing both digest and tag?
            if "imageDigest" not in image_id and "imageTag" not in image_id:
                response["failures"].append(
                    {
                        "imageId": {},
                        "failureCode": "MissingDigestAndTag",
                        "failureReason": "Invalid request parameters: both tag and digest cannot be null",
                    }
                )
                continue

            # If we have a digest, is it valid?
            if "imageDigest" in image_id:
                pattern = re.compile(r"^[0-9a-zA-Z_+\.-]+:[0-9a-fA-F]{64}")
                if not pattern.match(image_id.get("imageDigest")):
                    response["failures"].append(
                        {
                            "imageId": {
                                "imageDigest": image_id.get("imageDigest", "null")
                            },
                            "failureCode": "InvalidImageDigest",
                            "failureReason": "Invalid request parameters: image digest should satisfy the regex '[a-zA-Z0-9-_+.]+:[a-fA-F0-9]+'",
                        }
                    )
                    continue

            for num, image in enumerate(repository.images):

                # Search by matching both digest and tag
                if "imageDigest" in image_id and "imageTag" in image_id:
                    if (
                        image_id["imageDigest"] == image.get_image_digest()
                        and image_id["imageTag"] in image.image_tags
                    ):
                        image_found = True
                        for image_tag in reversed(image.image_tags):
                            repository.images[num].image_tag = image_tag
                            response["imageIds"].append(
                                image.response_batch_delete_image
                            )
                            repository.images[num].remove_tag(image_tag)
                        del repository.images[num]

                # Search by matching digest
                elif (
                    "imageDigest" in image_id
                    and image.get_image_digest() == image_id["imageDigest"]
                ):
                    image_found = True
                    for image_tag in reversed(image.image_tags):
                        repository.images[num].image_tag = image_tag
                        response["imageIds"].append(image.response_batch_delete_image)
                        repository.images[num].remove_tag(image_tag)
                    del repository.images[num]

                # Search by matching tag
                elif (
                    "imageTag" in image_id and image_id["imageTag"] in image.image_tags
                ):
                    image_found = True
                    repository.images[num].image_tag = image_id["imageTag"]
                    response["imageIds"].append(image.response_batch_delete_image)
                    if len(image.image_tags) > 1:
                        repository.images[num].remove_tag(image_id["imageTag"])
                    else:
                        repository.images.remove(image)

                if not image_found:
                    failure_response = {
                        "imageId": {},
                        "failureCode": "ImageNotFound",
                        "failureReason": "Requested image not found",
                    }

                    if "imageDigest" in image_id:
                        failure_response["imageId"]["imageDigest"] = image_id.get(
                            "imageDigest", "null"
                        )

                    if "imageTag" in image_id:
                        failure_response["imageId"]["imageTag"] = image_id.get(
                            "imageTag", "null"
                        )

                    response["failures"].append(failure_response)

        return response


ecr_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecr_backends[region] = ECRBackend()
