from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import apigateway_backends


class APIGatewayResponse(BaseResponse):

    def _get_param(self, key):
        return json.loads(self.body.decode("ascii")).get(key)

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
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == 'GET':
            rest_api = self.backend.get_rest_api(function_id)
            return 200, headers, json.dumps(rest_api.to_dict())
        elif self.method == 'DELETE':
            rest_api = self.backend.delete_rest_api(function_id)
            return 200, headers, json.dumps(rest_api.to_dict())

    def resources(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == 'GET':
            resources = self.backend.list_resources(function_id)
            return 200, headers, json.dumps({"item": [
                resource.to_dict() for resource in resources
            ]})

    def resource_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]
        resource_id = self.path.split("/")[-1]

        if self.method == 'GET':
            resource = self.backend.get_resource(function_id, resource_id)
        elif self.method == 'POST':
            path_part = self._get_param("pathPart")
            resource = self.backend.create_resource(function_id, resource_id, path_part)
        elif self.method == 'DELETE':
            resource = self.backend.delete_resource(function_id, resource_id)
        return 200, headers, json.dumps(resource.to_dict())

    def resource_methods(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]

        if self.method == 'GET':
            method = self.backend.get_method(function_id, resource_id, method_type)
            return 200, headers, json.dumps(method)
        elif self.method == 'PUT':
            authorization_type = self._get_param("authorizationType")
            method = self.backend.create_method(function_id, resource_id, method_type, authorization_type)
            return 200, headers, json.dumps(method)

    def resource_method_responses(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]
        response_code = url_path_parts[8]

        if self.method == 'GET':
            method_response = self.backend.get_method_response(function_id, resource_id, method_type, response_code)
        elif self.method == 'PUT':
            method_response = self.backend.create_method_response(function_id, resource_id, method_type, response_code)
        elif self.method == 'DELETE':
            method_response = self.backend.delete_method_response(function_id, resource_id, method_type, response_code)
        return 200, headers, json.dumps(method_response)

    def stages(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        stage_name = url_path_parts[4]

        if self.method == 'GET':
            stage_response = self.backend.get_stage(function_id, stage_name)
        elif self.method == 'PATCH':
            path_operations = self._get_param('patchOperations')
            stage_response = self.backend.update_stage(function_id, stage_name, path_operations)
        return 200, headers, json.dumps(stage_response)

    def integrations(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]

        if self.method == 'GET':
            integration_response = self.backend.get_integration(function_id, resource_id, method_type)
        elif self.method == 'PUT':
            integration_type = self._get_param('type')
            uri = self._get_param('uri')
            request_templates = self._get_param('requestTemplates')
            integration_response = self.backend.create_integration(function_id, resource_id, method_type, integration_type, uri, request_templates=request_templates)
        elif self.method == 'DELETE':
            integration_response = self.backend.delete_integration(function_id, resource_id, method_type)
        return 200, headers, json.dumps(integration_response)

    def integration_responses(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]
        status_code = url_path_parts[9]

        if self.method == 'GET':
            integration_response = self.backend.get_integration_response(
                function_id, resource_id, method_type, status_code
            )
        elif self.method == 'PUT':
            selection_pattern = self._get_param("selectionPattern")
            integration_response = self.backend.create_integration_response(
                function_id, resource_id, method_type, status_code, selection_pattern
            )
        elif self.method == 'DELETE':
            integration_response = self.backend.delete_integration_response(
                function_id, resource_id, method_type, status_code
            )
        return 200, headers, json.dumps(integration_response)

    def deployments(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == 'GET':
            deployments = self.backend.get_deployments(function_id)
            return 200, headers, json.dumps({"item": deployments})
        elif self.method == 'POST':
            name = self._get_param("stageName")
            deployment = self.backend.create_deployment(function_id, name)
            return 200, headers, json.dumps(deployment)

    def individual_deployment(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        deployment_id = url_path_parts[4]

        if self.method == 'GET':
            deployment = self.backend.get_deployment(function_id, deployment_id)
        elif self.method == 'DELETE':
            deployment = self.backend.delete_deployment(function_id, deployment_id)
        return 200, headers, json.dumps(deployment)
