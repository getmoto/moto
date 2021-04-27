from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import eks_backends
import json

DEFAULT_MAX_RESULTS = 100
DEFAULT_NEXT_TOKEN = ''


class EKSResponse(BaseResponse):
    SERVICE_NAME = 'eks'

    @property
    def eks_backend(self):
        return eks_backends[self.region]

    def list_clusters(self):
        max_results = self._get_int_param("maxResults") or DEFAULT_MAX_RESULTS
        next_token = self._get_param("nextToken") or DEFAULT_NEXT_TOKEN
        clusters, next_token = self.eks_backend.list_clusters(
            max_results=max_results,
            next_token=next_token,
        )

        return json.dumps(dict(clusters=clusters, nextToken=next_token))
