from __future__ import unicode_literals

import datetime
import httpretty
import requests

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_with_milliseconds
from .utils import create_id

STAGE_URL = "https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}"


class Deployment(dict):
    def __init__(self, deployment_id, name):
        super(Deployment, self).__init__()
        self['id'] = deployment_id
        self['stageName'] = name


class IntegrationResponse(dict):
    def __init__(self, status_code, selection_pattern=None):
        self['responseTemplates'] = {"application/json": None}
        self['statusCode'] = status_code
        if selection_pattern:
            self['selectionPattern'] = selection_pattern


class Integration(dict):
    def __init__(self, integration_type, uri, http_method, request_templates=None):
        super(Integration, self).__init__()
        self['type'] = integration_type
        self['uri'] = uri
        self['httpMethod'] = http_method
        self['requestTemplates'] = request_templates
        self["integrationResponses"] = {
            "200": IntegrationResponse(200)
        }

    def create_integration_response(self, status_code, selection_pattern):
        integration_response = IntegrationResponse(status_code, selection_pattern)
        self["integrationResponses"][status_code] = integration_response
        return integration_response

    def get_integration_response(self, status_code):
        return self["integrationResponses"][status_code]

    def delete_integration_response(self, status_code):
        return self["integrationResponses"].pop(status_code)


class MethodResponse(dict):
    def __init__(self, status_code):
        super(MethodResponse, self).__init__()
        self['statusCode'] = status_code


class Method(dict):
    def __init__(self, method_type, authorization_type):
        super(Method, self).__init__()
        self.update(dict(
            httpMethod=method_type,
            authorizationType=authorization_type,
            authorizerId=None,
            apiKeyRequired=None,
            requestParameters=None,
            requestModels=None,
            methodIntegration=None,
        ))
        self.method_responses = {}

    def create_response(self, response_code):
        method_response = MethodResponse(response_code)
        self.method_responses[response_code] = method_response
        return method_response

    def get_response(self, response_code):
        return self.method_responses[response_code]

    def delete_response(self, response_code):
        return self.method_responses.pop(response_code)


class Resource(object):
    def __init__(self, id, region_name, api_id, path_part, parent_id):
        self.id = id
        self.region_name = region_name
        self.api_id = api_id
        self.path_part = path_part
        self.parent_id = parent_id
        self.resource_methods = {
            'GET': {}
        }

    def to_dict(self):
        response = {
            "path": self.get_path(),
            "id": self.id,
            "resourceMethods": self.resource_methods,
        }
        if self.parent_id:
            response['parentId'] = self.parent_id
            response['pathPart'] = self.path_part
        return response

    def get_path(self):
        return self.get_parent_path() + self.path_part

    def get_parent_path(self):
        if self.parent_id:
            backend = apigateway_backends[self.region_name]
            parent = backend.get_resource(self.api_id, self.parent_id)
            parent_path = parent.get_path()
            if parent_path != '/':  # Root parent
                parent_path += '/'
            return parent_path
        else:
            return ''

    def get_response(self, request):
        integration = self.get_integration(request.method)
        integration_type = integration['type']

        if integration_type == 'HTTP':
            uri = integration['uri']
            requests_func = getattr(requests, integration['httpMethod'].lower())
            response = requests_func(uri)
        else:
            raise NotImplementedError("The {0} type has not been implemented".format(integration_type))
        return response.status_code, response.text

    def add_method(self, method_type, authorization_type):
        method = Method(method_type=method_type, authorization_type=authorization_type)
        self.resource_methods[method_type] = method
        return method

    def get_method(self, method_type):
        return self.resource_methods[method_type]

    def add_integration(self, method_type, integration_type, uri, request_templates=None):
        integration = Integration(integration_type, uri, method_type, request_templates=request_templates)
        self.resource_methods[method_type]['methodIntegration'] = integration
        return integration

    def get_integration(self, method_type):
        return self.resource_methods[method_type]['methodIntegration']

    def delete_integration(self, method_type):
        return self.resource_methods[method_type].pop('methodIntegration')


class Stage(dict):
    def __init__(self, name=None, deployment_id=None):
        super(Stage, self).__init__()
        self['stageName'] = name
        self['deploymentId'] = deployment_id
        self['methodSettings'] = {}
        self['variables'] = {}
        self['description'] = ''

    def apply_operations(self, patch_operations):
        for op in patch_operations:
            if op['op'] == 'replace':
                # TODO: match the path against the values hash
                # (e.g., path could be '/*/*/logging/loglevel')
                self[op['path']] = op['value']
            else:
                raise Exception('Patch operation "%s" not implemented' % op['op'])
        return self


class RestAPI(object):
    def __init__(self, id, region_name, name, description):
        self.id = id
        self.region_name = region_name
        self.name = name
        self.description = description
        self.create_date = datetime.datetime.utcnow()

        self.deployments = {}
        self.stages = {}

        self.resources = {}
        self.add_child('/')  # Add default child

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "createdDate": iso_8601_datetime_with_milliseconds(self.create_date),
        }

    def add_child(self, path, parent_id=None):
        child_id = create_id()
        child = Resource(id=child_id, region_name=self.region_name, api_id=self.id, path_part=path, parent_id=parent_id)
        self.resources[child_id] = child
        return child

    def get_resource_for_path(self, path_after_stage_name):
        for resource in self.resources.values():
            if resource.get_path() == path_after_stage_name:
                return resource
        # TODO deal with no matching resource

    def resource_callback(self, request, full_url, headers):
        path_after_stage_name = '/'.join(request.path.split("/")[2:])
        if not path_after_stage_name:
            path_after_stage_name = '/'

        resource = self.get_resource_for_path(path_after_stage_name)
        status_code, response = resource.get_response(request)
        return status_code, headers, response

    def update_integration_mocks(self, stage_name):
        httpretty.enable()

        stage_url = STAGE_URL.format(api_id=self.id, region_name=self.region_name, stage_name=stage_name)
        for method in httpretty.httpretty.METHODS:
            httpretty.register_uri(method, stage_url, body=self.resource_callback)

    def create_deployment(self, name):
        deployment_id = create_id()
        deployment = Deployment(deployment_id, name)
        self.deployments[deployment_id] = deployment
        self.stages[name] = Stage(name=name, deployment_id=deployment_id)

        self.update_integration_mocks(name)

        return deployment

    def get_deployment(self, deployment_id):
        return self.deployments[deployment_id]

    def get_deployments(self):
        return list(self.deployments.values())

    def delete_deployment(self, deployment_id):
        return self.deployments.pop(deployment_id)


class APIGatewayBackend(BaseBackend):
    def __init__(self, region_name):
        super(APIGatewayBackend, self).__init__()
        self.apis = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_rest_api(self, name, description):
        api_id = create_id()
        rest_api = RestAPI(api_id, self.region_name, name, description)
        self.apis[api_id] = rest_api
        return rest_api

    def get_rest_api(self, function_id):
        rest_api = self.apis[function_id]
        return rest_api

    def list_apis(self):
        return self.apis.values()

    def delete_rest_api(self, function_id):
        rest_api = self.apis.pop(function_id)
        return rest_api

    def list_resources(self, function_id):
        api = self.get_rest_api(function_id)
        return api.resources.values()

    def get_resource(self, function_id, resource_id):
        api = self.get_rest_api(function_id)
        resource = api.resources[resource_id]
        return resource

    def create_resource(self, function_id, parent_resource_id, path_part):
        api = self.get_rest_api(function_id)
        child = api.add_child(
            path=path_part,
            parent_id=parent_resource_id,
        )
        return child

    def delete_resource(self, function_id, resource_id):
        api = self.get_rest_api(function_id)
        resource = api.resources.pop(resource_id)
        return resource

    def get_method(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.get_method(method_type)

    def create_method(self, function_id, resource_id, method_type, authorization_type):
        resource = self.get_resource(function_id, resource_id)
        method = resource.add_method(method_type, authorization_type)
        return method

    def get_stage(self, function_id, stage_name):
        api = self.get_rest_api(function_id)
        return api.stages.get(stage_name)

    def update_stage(self, function_id, stage_name, patch_operations):
        stage = self.get_stage(function_id, stage_name)
        if not stage:
            api = self.get_rest_api(function_id)
            stage = api.stages[stage_name] = Stage()
        return stage.apply_operations(patch_operations)

    def get_method_response(self, function_id, resource_id, method_type, response_code):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.get_response(response_code)
        return method_response

    def create_method_response(self, function_id, resource_id, method_type, response_code):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.create_response(response_code)
        return method_response

    def delete_method_response(self, function_id, resource_id, method_type, response_code):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.delete_response(response_code)
        return method_response

    def create_integration(self, function_id, resource_id, method_type, integration_type, uri,
            request_templates=None):
        resource = self.get_resource(function_id, resource_id)
        integration = resource.add_integration(method_type, integration_type, uri,
            request_templates=request_templates)
        return integration

    def get_integration(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.get_integration(method_type)

    def delete_integration(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.delete_integration(method_type)

    def create_integration_response(self, function_id, resource_id, method_type, status_code, selection_pattern):
        integration = self.get_integration(function_id, resource_id, method_type)
        integration_response = integration.create_integration_response(status_code, selection_pattern)
        return integration_response

    def get_integration_response(self, function_id, resource_id, method_type, status_code):
        integration = self.get_integration(function_id, resource_id, method_type)
        integration_response = integration.get_integration_response(status_code)
        return integration_response

    def delete_integration_response(self, function_id, resource_id, method_type, status_code):
        integration = self.get_integration(function_id, resource_id, method_type)
        integration_response = integration.delete_integration_response(status_code)
        return integration_response

    def create_deployment(self, function_id, name):
        api = self.get_rest_api(function_id)
        deployment = api.create_deployment(name)
        return deployment

    def get_deployment(self, function_id, deployment_id):
        api = self.get_rest_api(function_id)
        return api.get_deployment(deployment_id)

    def get_deployments(self, function_id):
        api = self.get_rest_api(function_id)
        return api.get_deployments()

    def delete_deployment(self, function_id, deployment_id):
        api = self.get_rest_api(function_id)
        return api.delete_deployment(deployment_id)

apigateway_backends = {}
for region_name in ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1']:  # Not available in boto yet
    apigateway_backends[region_name] = APIGatewayBackend(region_name)
