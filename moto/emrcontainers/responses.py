"""Handles incoming emrcontainers requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import emrcontainers_backends

DEFAULT_MAX_RESULTS = 100
DEFAULT_NEXT_TOKEN = ""
DEFAULT_CONTAINER_PROVIDER_TYPE = "EKS"


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
            name=name,
            container_provider=container_provider,
            client_token=client_token,
            tags=tags,
        )
        return 200, {}, json.dumps(dict(virtual_cluster))

    def delete_virtual_cluster(self):
        id = self._get_param("virtualClusterId")

        virtual_cluster = self.emrcontainers_backend.delete_virtual_cluster(id=id)
        return 200, {}, json.dumps(dict(virtual_cluster))

    def describe_virtual_cluster(self):
        id = self._get_param("virtualClusterId")

        virtual_cluster = self.emrcontainers_backend.describe_virtual_cluster(id=id)
        response = {"virtualCluster": virtual_cluster}
        return 200, {}, json.dumps(response)

    def list_virtual_clusters(self):
        container_provider_id = self._get_param("containerProviderId")
        container_provider_type = self._get_param(
            "containerProviderType", DEFAULT_CONTAINER_PROVIDER_TYPE
        )
        created_after = self._get_param("createdAfter")
        created_before = self._get_param("createdBefore")
        states = self.querystring.get("states", [])
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)

        virtual_clusters, next_token = self.emrcontainers_backend.list_virtual_clusters(
            container_provider_id=container_provider_id,
            container_provider_type=container_provider_type,
            created_after=created_after,
            created_before=created_before,
            states=states,
            max_results=max_results,
            next_token=next_token,
        )

        response = {"virtualClusters": virtual_clusters, "nextToken": next_token}
        return 200, {}, json.dumps(response)
