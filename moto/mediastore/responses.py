from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import mediastore_backends
import json


class MediaStoreResponse(BaseResponse):
    SERVICE_NAME = 'mediastore'
    @property
    def mediastore_backend(self):
        return mediastore_backends[self.region]

    def create_container(self):
        name = self._get_param("ContainerName")
        tags = self._get_param("Tags")
        container = self.mediastore_backend.create_container(name=name, tags=tags)
        return json.dumps(dict(Container=container.to_dict()))

    def describe_container(self):
        name = self._get_param("ContainerName")
        container = self.mediastore_backend.describe_container(name=name)
        return json.dumps(dict(Container=container.to_dict()))
    
    def put_lifecycle_policy(self):
        container_name = self._get_param("ContainerName")
        lifecycle_policy = self._get_param("LifecyclePolicy")
        policy = self.mediastore_backend.put_lifecycle_policy(
            container_name=container_name,
            lifecycle_policy=lifecycle_policy,
        )
        return json.dumps(policy)