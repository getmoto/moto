from __future__ import unicode_literals

import hashlib
import re
import uuid
from collections import namedtuple
from datetime import datetime
from random import random

from botocore.exceptions import ParamValidationError

from moto.core import BaseBackend, BaseModel, CloudFormationModel, ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.ec2 import ec2_backends
from moto.ecr.exceptions import (
    ImageNotFoundException,
    RepositoryNotFoundException,
    RepositoryAlreadyExistsException,
    RepositoryNotEmptyException,
    InvalidParameterException,
    RepositoryPolicyNotFoundException,
)
from moto.iam.exceptions import MalformedPolicyDocument
from moto.iam.policy_validation import IAMPolicyDocumentValidator
from moto.utilities.tagging_service import TaggingService

DEFAULT_REGISTRY_ID = ACCOUNT_ID
ECR_REPOSITORY_ARN_PATTERN = "^arn:(?P<partition>[^:]+):ecr:(?P<region>[^:]+):(?P<account_id>[^:]+):repository/(?P<repo_name>.*)$"

EcrRepositoryArn = namedtuple(
    "EcrRepositoryArn", ["partition", "region", "account_id", "repo_name"]
)


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
    def __init__(
        self,
        region_name,
        repository_name,
        encryption_config,
        image_scan_config,
        image_tag_mutablility,
    ):
        self.region_name = region_name
        self.registry_id = DEFAULT_REGISTRY_ID
        self.arn = (
            f"arn:aws:ecr:{region_name}:{self.registry_id}:repository/{repository_name}"
        )
        self.name = repository_name
        self.created_at = datetime.utcnow()
        self.uri = (
            f"{self.registry_id}.dkr.ecr.{region_name}.amazonaws.com/{repository_name}"
        )
        self.image_tag_mutability = image_tag_mutablility or "MUTABLE"
        self.image_scanning_configuration = image_scan_config or {"scanOnPush": False}
        self.encryption_configuration = self._determine_encryption_config(
            encryption_config
        )
        self.policy = None
        self.images = []

    def _determine_encryption_config(self, encryption_config):
        if not encryption_config:
            return {"encryptionType": "AES256"}
        if encryption_config == {"encryptionType": "KMS"}:
            encryption_config[
                "kmsKey"
            ] = f"arn:aws:kms:{self.region_name}:{ACCOUNT_ID}:key/{uuid.uuid4()}"
        return encryption_config

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
        response_object["createdAt"] = iso_8601_datetime_without_milliseconds(
            self.created_at
        )
        del response_object["arn"], response_object["name"], response_object["images"]
        return response_object

    def update(self, image_scan_config=None, image_tag_mutability=None):
        if image_scan_config:
            self.image_scanning_configuration = image_scan_config
        if image_tag_mutability:
            self.image_tag_mutability = image_tag_mutability

    def delete(self, region_name):
        ecr_backend = ecr_backends[region_name]
        ecr_backend.delete_repository(self.name)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        elif attribute_name == "RepositoryUri":
            return self.uri

        raise UnformattedGetAttTemplateException()

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
        ecr_backend = ecr_backends[region_name]
        properties = cloudformation_json["Properties"]

        encryption_config = properties.get("EncryptionConfiguration")
        image_scan_config = properties.get("ImageScanningConfiguration")
        image_tag_mutablility = properties.get("ImageTagMutability")
        tags = properties.get("Tags", [])

        return ecr_backend.create_repository(
            # RepositoryName is optional in CloudFormation, thus create a random
            # name if necessary
            repository_name=resource_name,
            encryption_config=encryption_config,
            image_scan_config=image_scan_config,
            image_tag_mutablility=image_tag_mutablility,
            tags=tags,
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        ecr_backend = ecr_backends[region_name]
        properties = cloudformation_json["Properties"]
        encryption_configuration = properties.get(
            "EncryptionConfiguration", {"encryptionType": "AES256"}
        )

        if (
            new_resource_name == original_resource.name
            and encryption_configuration == original_resource.encryption_configuration
        ):
            original_resource.update(
                properties.get("ImageScanningConfiguration"),
                properties.get("ImageTagMutability"),
            )

            ecr_backend.tagger.tag_resource(
                original_resource.arn, properties.get("Tags", [])
            )

            return original_resource
        else:
            original_resource.delete(region_name)
            return cls.create_from_cloudformation_json(
                new_resource_name, cloudformation_json, region_name
            )


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
        response_object["imageDigest"] = self.get_image_digest()
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
    def __init__(self, region_name):
        self.region_name = region_name
        self.repositories = {}
        self.tagger = TaggingService(tagName="tags")

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def _get_repository(self, name, registry_id=None):
        repo = self.repositories.get(name)
        reg_id = registry_id or DEFAULT_REGISTRY_ID

        if not repo or repo.registry_id != reg_id:
            raise RepositoryNotFoundException(name, reg_id)
        return repo

    @staticmethod
    def _parse_resource_arn(resource_arn) -> EcrRepositoryArn:
        match = re.match(ECR_REPOSITORY_ARN_PATTERN, resource_arn)
        if not match:
            raise InvalidParameterException(
                "Invalid parameter at 'resourceArn' failed to satisfy constraint: "
                "'Invalid ARN'"
            )
        return EcrRepositoryArn(**match.groupdict())

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

    def create_repository(
        self,
        repository_name,
        encryption_config,
        image_scan_config,
        image_tag_mutablility,
        tags,
    ):
        if self.repositories.get(repository_name):
            raise RepositoryAlreadyExistsException(repository_name, DEFAULT_REGISTRY_ID)

        repository = Repository(
            region_name=self.region_name,
            repository_name=repository_name,
            encryption_config=encryption_config,
            image_scan_config=image_scan_config,
            image_tag_mutablility=image_tag_mutablility,
        )
        self.repositories[repository_name] = repository
        self.tagger.tag_resource(repository.arn, tags)

        return repository

    def delete_repository(self, repository_name, registry_id=None):
        repo = self._get_repository(repository_name, registry_id)

        if repo.images:
            raise RepositoryNotEmptyException(
                repository_name, registry_id or DEFAULT_REGISTRY_ID
            )

        self.tagger.delete_all_tags_for_resource(repo.arn)
        return self.repositories.pop(repository_name)

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

    def list_tags_for_resource(self, arn):
        resource = self._parse_resource_arn(arn)
        repo = self._get_repository(resource.repo_name, resource.account_id)

        return self.tagger.list_tags_for_resource(repo.arn)

    def tag_resource(self, arn, tags):
        resource = self._parse_resource_arn(arn)
        repo = self._get_repository(resource.repo_name, resource.account_id)
        self.tagger.tag_resource(repo.arn, tags)

        return {}

    def untag_resource(self, arn, tag_keys):
        resource = self._parse_resource_arn(arn)
        repo = self._get_repository(resource.repo_name, resource.account_id)
        self.tagger.untag_resource_using_names(repo.arn, tag_keys)

        return {}

    def put_image_tag_mutability(
        self, registry_id, repository_name, image_tag_mutability
    ):
        if image_tag_mutability not in ["IMMUTABLE", "MUTABLE"]:
            raise InvalidParameterException(
                "Invalid parameter at 'imageTagMutability' failed to satisfy constraint: "
                "'Member must satisfy enum value set: [IMMUTABLE, MUTABLE]'"
            )

        repo = self._get_repository(repository_name, registry_id)
        repo.update(image_tag_mutability=image_tag_mutability)

        return {
            "registryId": repo.registry_id,
            "repositoryName": repository_name,
            "imageTagMutability": repo.image_tag_mutability,
        }

    def put_image_scanning_configuration(
        self, registry_id, repository_name, image_scan_config
    ):
        repo = self._get_repository(repository_name, registry_id)
        repo.update(image_scan_config=image_scan_config)

        return {
            "registryId": repo.registry_id,
            "repositoryName": repository_name,
            "imageScanningConfiguration": repo.image_scanning_configuration,
        }

    def set_repository_policy(self, registry_id, repository_name, policy_text):
        repo = self._get_repository(repository_name, registry_id)

        try:
            iam_policy_document_validator = IAMPolicyDocumentValidator(policy_text)
            # the repository policy can be defined without a resource field
            iam_policy_document_validator._validate_resource_exist = lambda: None
            # the repository policy can have the old version 2008-10-17
            iam_policy_document_validator._validate_version = lambda: None
            iam_policy_document_validator.validate()
        except MalformedPolicyDocument:
            raise InvalidParameterException(
                "Invalid parameter at 'PolicyText' failed to satisfy constraint: "
                "'Invalid repository policy provided'"
            )

        repo.policy = policy_text

        return {
            "registryId": repo.registry_id,
            "repositoryName": repository_name,
            "policyText": repo.policy,
        }

    def get_repository_policy(self, registry_id, repository_name):
        repo = self._get_repository(repository_name, registry_id)

        if not repo.policy:
            raise RepositoryPolicyNotFoundException(repository_name, repo.registry_id)

        return {
            "registryId": repo.registry_id,
            "repositoryName": repository_name,
            "policyText": repo.policy,
        }

    def delete_repository_policy(self, registry_id, repository_name):
        repo = self._get_repository(repository_name, registry_id)
        policy = repo.policy

        if not policy:
            raise RepositoryPolicyNotFoundException(repository_name, repo.registry_id)

        repo.policy = None

        return {
            "registryId": repo.registry_id,
            "repositoryName": repository_name,
            "policyText": policy,
        }


ecr_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecr_backends[region] = ECRBackend(region)
