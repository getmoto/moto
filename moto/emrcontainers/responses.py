"""Handles incoming emrcontainers requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import emrcontainers_backends


class EMRContainersResponse(BaseResponse):
    """Handler for EMRContainers requests and responses."""

    SERVICE_NAME = "emr-containers"


    @property
    def emrcontainers_backend(self):
        """Return backend instance specific for this region."""
        return emrcontainers_backends[self.region]

    def create_virtual_cluster(self):
        name = self._get_param("name")
        container_provider = self._get_param("containerProvider")
        client_token = self._get_param("clientToken")
        tags = self._get_param("tags")

        virtual_cluster = self.emrcontainers_backend.create_virtual_cluster(
            name = name,
            container_provider = container_provider,
            client_token = client_token,
            tags = tags
        )

        return 200, {}, json.dumps(virtual_cluster)

# add templates from here
