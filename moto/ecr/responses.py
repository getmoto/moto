from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import ecr_backends


class ECRResponse(BaseResponse):

    @property
    def ecr_backend(self):
        return ecr_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param):
        return self.request_params.get(param, None)

    def create_repository(self):
        repository_name = self._get_param('repositoryName')
        if repository_name is None:
            repository_name = 'default'
        repository = self.ecr_backend.create_repository(repository_name)
        return json.dumps({
            'repository': repository.response_object
        })

    def describe_repositories(self):
        describe_repositories_name = self._get_param('repositoryNames')
        registry_id = self._get_param('registryId')

        repositories = self.ecr_backend.describe_repositories(
            repository_names=describe_repositories_name, registry_id=registry_id)
        return json.dumps({
            'repositories': repositories,
            'failures': []
        })

    def delete_repository(self):
        repository_str = self._get_param('repositoryName')
        repository = self.ecr_backend.delete_repository(repository_str)
        return json.dumps({
            'repository': repository.response_object
        })

    def put_image(self):
        repository_str = self._get_param('repositoryName')
        image_manifest = self._get_param('imageManifest')
        image_tag = self._get_param('imageTag')
        image = self.ecr_backend.put_image(repository_str, image_manifest, image_tag)

        return json.dumps({
            'image': image.response_object
        })

    def list_images(self):
        repository_str = self._get_param('repositoryName')
        registry_id = self._get_param('registryId')
        images = self.ecr_backend.list_images(repository_str, registry_id)
        return json.dumps({
            'imageIds': [image.response_list_object for image in images],
        })

    def describe_images(self):
        repository_str = self._get_param('repositoryName')
        registry_id = self._get_param('registryId')
        images = self.ecr_backend.describe_images(repository_str, registry_id)
        return json.dumps({
            'imageDetails': [image.response_describe_object for image in images],
        })
