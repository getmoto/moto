from __future__ import unicode_literals
# from datetime import datetime
from random import random

from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends
from copy import copy
import hashlib


class BaseObject(BaseModel):

    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split('_')):
            if i > 0:
                words.append(word.title())
            else:
                words.append(word)
        return ''.join(words)

    def gen_response_object(self):
        response_object = copy(self.__dict__)
        for key, value in response_object.items():
            if '_' in key:
                response_object[self.camelCase(key)] = value
                del response_object[key]
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class Repository(BaseObject):

    def __init__(self, repository_name):
        self.arn = 'arn:aws:ecr:us-east-1:012345678910:repository/{0}'.format(
            repository_name)
        self.name = repository_name
        # self.created = datetime.utcnow()
        self.uri = '012345678910.dkr.ecr.us-east-1.amazonaws.com/{0}'.format(
            repository_name
        )
        self.registry_id = '012345678910'
        self.images = []

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def response_object(self):
        response_object = self.gen_response_object()

        response_object['registryId'] = self.registry_id
        response_object['repositoryArn'] = self.arn
        response_object['repositoryName'] = self.name
        response_object['repositoryUri'] = self.uri
        # response_object['createdAt'] = self.created
        del response_object['arn'], response_object['name'], response_object['images']
        return response_object

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ecr_backend = ecr_backends[region_name]
        return ecr_backend.create_repository(
            # RepositoryName is optional in CloudFormation, thus create a random
            # name if necessary
            repository_name=properties.get(
                'RepositoryName', 'ecrrepository{0}'.format(int(random() * 10 ** 6))),
        )

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        if original_resource.name != properties['RepositoryName']:
            ecr_backend = ecr_backends[region_name]
            ecr_backend.delete_cluster(original_resource.arn)
            return ecr_backend.create_repository(
                # RepositoryName is optional in CloudFormation, thus create a
                # random name if necessary
                repository_name=properties.get(
                    'RepositoryName', 'RepositoryName{0}'.format(int(random() * 10 ** 6))),
            )
        else:
            # no-op when nothing changed between old and new resources
            return original_resource


class Image(BaseObject):

    def __init__(self, tag, manifest, repository, registry_id="012345678910"):
        self.image_tag = tag
        self.image_manifest = manifest
        self.image_size_in_bytes = 50 * 1024 * 1024
        self.repository = repository
        self.registry_id = registry_id
        self.image_digest = None
        self.image_pushed_at = None

    def _create_digest(self):
        image_contents = 'docker_image{0}'.format(int(random() * 10 ** 6))
        self.image_digest = "sha256:%s" % hashlib.sha256(image_contents.encode('utf-8')).hexdigest()

    def get_image_digest(self):
        if not self.image_digest:
            self._create_digest()
        return self.image_digest

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['imageId'] = {}
        response_object['imageId']['imageTag'] = self.image_tag
        response_object['imageId']['imageDigest'] = self.get_image_digest()
        response_object['imageManifest'] = self.image_manifest
        response_object['repositoryName'] = self.repository
        response_object['registryId'] = self.registry_id
        return response_object

    @property
    def response_list_object(self):
        response_object = self.gen_response_object()
        response_object['imageTag'] = self.image_tag
        response_object['imageDigest'] = "i don't know"
        return response_object

    @property
    def response_describe_object(self):
        response_object = self.gen_response_object()
        response_object['imageTags'] = [self.image_tag]
        response_object['imageDigest'] = self.get_image_digest()
        response_object['imageManifest'] = self.image_manifest
        response_object['repositoryName'] = self.repository
        response_object['registryId'] = self.registry_id
        response_object['imageSizeInBytes'] = self.image_size_in_bytes
        response_object['imagePushedAt'] = '2017-05-09'
        return response_object


class ECRBackend(BaseBackend):

    def __init__(self):
        self.repositories = {}

    def describe_repositories(self, registry_id=None, repository_names=None):
        """
        maxResults and nextToken not implemented
        """
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

    def delete_repository(self, respository_name, registry_id=None):
        if respository_name in self.repositories:
            return self.repositories.pop(respository_name)
        else:
            raise Exception("{0} is not a repository".format(respository_name))

    def list_images(self, repository_name, registry_id=None):
        """
        maxResults and filtering not implemented
        """
        images = []
        for repository in self.repositories.values():
            if repository_name:
                if repository.name != repository_name:
                    continue
            if registry_id:
                if repository.registry_id != registry_id:
                    continue

            for image in repository.images:
                images.append(image)
        return images

    def describe_images(self, repository_name, registry_id=None, image_ids=None):

        if repository_name in self.repositories:
            repository = self.repositories[repository_name]
        else:
            raise Exception("{0} is not a repository".format(repository_name))

        if image_ids:
            response = set()
            for image_id in image_ids:
                if 'imageDigest' in image_id:
                    desired_digest = image_id['imageDigest']
                    response.update([i for i in repository.images if i.get_image_digest() == desired_digest])
                if 'imageTag' in image_id:
                    desired_tag = image_id['imageTag']
                    response.update([i for i in repository.images if i.image_tag == desired_tag])
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

        image = Image(image_tag, image_manifest, repository_name)
        repository.images.append(image)
        return image


ecr_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecr_backends[region] = ECRBackend()
