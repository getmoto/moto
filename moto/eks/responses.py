from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import eks_backends
import json

DEFAULT_MAX_RESULTS = 100
DEFAULT_NEXT_TOKEN = ""


class EKSResponse(BaseResponse):
    SERVICE_NAME = "eks"

    @property
    def eks_backend(self):
        return eks_backends[self.region]

    def create_cluster(self):
        name = self._get_param("name")
        version = self._get_param("version")
        role_arn = self._get_param("roleArn")
        resources_vpc_config = self._get_param("resourcesVpcConfig")
        kubernetes_network_config = self._get_param("kubernetesNetworkConfig")
        logging = self._get_param("logging")
        client_request_token = self._get_param("clientRequestToken")
        tags = self._get_param("tags")
        encryption_config = self._get_list_prefix("encryptionConfig.member")
        cluster = self.eks_backend.create_cluster(
            name=name,
            version=version,
            role_arn=role_arn,
            resources_vpc_config=resources_vpc_config,
            kubernetes_network_config=kubernetes_network_config,
            logging=logging,
            client_request_token=client_request_token,
            tags=tags,
            encryption_config=encryption_config,
        )

        return 200, {}, json.dumps({"cluster": {**dict(cluster)}})

    def list_clusters(self):
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)
        clusters, next_token = self.eks_backend.list_clusters(
            max_results=max_results, next_token=next_token,
        )

        return 200, {}, json.dumps(dict(clusters=clusters, nextToken=next_token))
