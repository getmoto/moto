from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import apigateway_backends


class APIGatewayResponse(BaseResponse):

    def _get_param(self, key):
        return json.loads(self.body).get(key)

    @property
    def backend(self):
        return apigateway_backends[self.region]

    def restapis(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == 'GET':
            apis = self.backend.list_apis()
            return 200, headers, json.dumps({"item": [
                api.to_dict() for api in apis
            ]})
        elif self.method == 'POST':
            name = self._get_param('name')
            description = self._get_param('description')
            rest_api = self.backend.create_rest_api(name, description)
            return 200, headers, json.dumps(rest_api.to_dict())

    def restapis_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.split("/")[-1]
        if self.method == 'GET':
            rest_api = self.backend.get_rest_api(function_id)
            return 200, headers, json.dumps(rest_api.to_dict())
        elif self.method == 'DELETE':
            rest_api = self.backend.delete_rest_api(function_id)
            return 200, headers, json.dumps(rest_api.to_dict())
