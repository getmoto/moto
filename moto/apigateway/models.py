from __future__ import absolute_import
from __future__ import unicode_literals

import random
import string
import requests
import time

from boto3.session import Session
import responses
from moto.core import BaseBackend, BaseModel
from .utils import create_id
from .exceptions import StageNotFoundException, ApiKeyNotFoundException

STAGE_URL = "https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}"


class Deployment(BaseModel, dict):

    def __init__(self, deployment_id, name, description=""):
        super(Deployment, self).__init__()
        self['id'] = deployment_id
        self['stageName'] = name
        self['description'] = description
        self['createdDate'] = int(time.time())


class IntegrationResponse(BaseModel, dict):

    def __init__(self, status_code, selection_pattern=None):
        self['responseTemplates'] = {"application/json": None}
        self['statusCode'] = status_code
        if selection_pattern:
            self['selectionPattern'] = selection_pattern


class Integration(BaseModel, dict):

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
        integration_response = IntegrationResponse(
            status_code, selection_pattern)
        self["integrationResponses"][status_code] = integration_response
        return integration_response

    def get_integration_response(self, status_code):
        return self["integrationResponses"][status_code]

    def delete_integration_response(self, status_code):
        return self["integrationResponses"].pop(status_code)


class MethodResponse(BaseModel, dict):

    def __init__(self, status_code):
        super(MethodResponse, self).__init__()
        self['statusCode'] = status_code


class Method(BaseModel, dict):

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


class Resource(BaseModel):

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
            requests_func = getattr(requests, integration[
                                    'httpMethod'].lower())
            response = requests_func(uri)
        else:
            raise NotImplementedError(
                "The {0} type has not been implemented".format(integration_type))
        return response.status_code, response.text

    def add_method(self, method_type, authorization_type):
        method = Method(method_type=method_type,
                        authorization_type=authorization_type)
        self.resource_methods[method_type] = method
        return method

    def get_method(self, method_type):
        return self.resource_methods[method_type]

    def add_integration(self, method_type, integration_type, uri, request_templates=None):
        integration = Integration(
            integration_type, uri, method_type, request_templates=request_templates)
        self.resource_methods[method_type]['methodIntegration'] = integration
        return integration

    def get_integration(self, method_type):
        return self.resource_methods[method_type]['methodIntegration']

    def delete_integration(self, method_type):
        return self.resource_methods[method_type].pop('methodIntegration')


class Stage(BaseModel, dict):

    def __init__(self, name=None, deployment_id=None, variables=None,
                 description='', cacheClusterEnabled=False, cacheClusterSize=None):
        super(Stage, self).__init__()
        if variables is None:
            variables = {}
        self['stageName'] = name
        self['deploymentId'] = deployment_id
        self['methodSettings'] = {}
        self['variables'] = variables
        self['description'] = description
        self['cacheClusterEnabled'] = cacheClusterEnabled
        if self['cacheClusterEnabled']:
            self['cacheClusterSize'] = str(0.5)

        if cacheClusterSize is not None:
            self['cacheClusterSize'] = str(cacheClusterSize)

    def apply_operations(self, patch_operations):
        for op in patch_operations:
            if 'variables/' in op['path']:
                self._apply_operation_to_variables(op)
            elif '/cacheClusterEnabled' in op['path']:
                self['cacheClusterEnabled'] = self._str2bool(op['value'])
                if 'cacheClusterSize' not in self and self['cacheClusterEnabled']:
                    self['cacheClusterSize'] = str(0.5)
            elif '/cacheClusterSize' in op['path']:
                self['cacheClusterSize'] = str(float(op['value']))
            elif '/description' in op['path']:
                self['description'] = op['value']
            elif '/deploymentId' in op['path']:
                self['deploymentId'] = op['value']
            elif op['op'] == 'replace':
                # Method Settings drop into here
                # (e.g., path could be '/*/*/logging/loglevel')
                split_path = op['path'].split('/', 3)
                if len(split_path) != 4:
                    continue
                self._patch_method_setting(
                    '/'.join(split_path[1:3]), split_path[3], op['value'])
            else:
                raise Exception(
                    'Patch operation "%s" not implemented' % op['op'])
        return self

    def _patch_method_setting(self, resource_path_and_method, key, value):
        updated_key = self._method_settings_translations(key)
        if updated_key is not None:
            if resource_path_and_method not in self['methodSettings']:
                self['methodSettings'][
                    resource_path_and_method] = self._get_default_method_settings()
            self['methodSettings'][resource_path_and_method][
                updated_key] = self._convert_to_type(updated_key, value)

    def _get_default_method_settings(self):
        return {
            "throttlingRateLimit": 1000.0,
            "dataTraceEnabled": False,
            "metricsEnabled": False,
            "unauthorizedCacheControlHeaderStrategy": "SUCCEED_WITH_RESPONSE_HEADER",
            "cacheTtlInSeconds": 300,
            "cacheDataEncrypted": True,
            "cachingEnabled": False,
            "throttlingBurstLimit": 2000,
            "requireAuthorizationForCacheControl": True
        }

    def _method_settings_translations(self, key):
        mappings = {
            'metrics/enabled': 'metricsEnabled',
            'logging/loglevel': 'loggingLevel',
            'logging/dataTrace': 'dataTraceEnabled',
            'throttling/burstLimit': 'throttlingBurstLimit',
            'throttling/rateLimit': 'throttlingRateLimit',
            'caching/enabled': 'cachingEnabled',
            'caching/ttlInSeconds': 'cacheTtlInSeconds',
            'caching/dataEncrypted': 'cacheDataEncrypted',
            'caching/requireAuthorizationForCacheControl': 'requireAuthorizationForCacheControl',
            'caching/unauthorizedCacheControlHeaderStrategy': 'unauthorizedCacheControlHeaderStrategy'
        }

        if key in mappings:
            return mappings[key]
        else:
            None

    def _str2bool(self, v):
        return v.lower() == "true"

    def _convert_to_type(self, key, val):
        type_mappings = {
            'metricsEnabled': 'bool',
            'loggingLevel': 'str',
            'dataTraceEnabled': 'bool',
            'throttlingBurstLimit': 'int',
            'throttlingRateLimit': 'float',
            'cachingEnabled': 'bool',
            'cacheTtlInSeconds': 'int',
            'cacheDataEncrypted': 'bool',
            'requireAuthorizationForCacheControl': 'bool',
            'unauthorizedCacheControlHeaderStrategy': 'str'
        }

        if key in type_mappings:
            type_value = type_mappings[key]

            if type_value == 'bool':
                return self._str2bool(val)
            elif type_value == 'int':
                return int(val)
            elif type_value == 'float':
                return float(val)
            else:
                return str(val)
        else:
            return str(val)

    def _apply_operation_to_variables(self, op):
        key = op['path'][op['path'].rindex("variables/") + 10:]
        if op['op'] == 'remove':
            self['variables'].pop(key, None)
        elif op['op'] == 'replace':
            self['variables'][key] = op['value']
        else:
            raise Exception('Patch operation "%s" not implemented' % op['op'])


class ApiKey(BaseModel, dict):

    def __init__(self, name=None, description=None, enabled=True,
                 generateDistinctId=False, value=None, stageKeys=None, customerId=None):
        super(ApiKey, self).__init__()
        self['id'] = create_id()
        self['value'] = value if value else ''.join(random.sample(string.ascii_letters + string.digits, 40))
        self['name'] = name
        self['customerId'] = customerId
        self['description'] = description
        self['enabled'] = enabled
        self['createdDate'] = self['lastUpdatedDate'] = int(time.time())
        self['stageKeys'] = stageKeys


class UsagePlan(BaseModel, dict):

    def __init__(self, name=None, description=None, apiStages=[],
                 throttle=None, quota=None):
        super(UsagePlan, self).__init__()
        self['id'] = create_id()
        self['name'] = name
        self['description'] = description
        self['apiStages'] = apiStages
        self['throttle'] = throttle
        self['quota'] = quota


class UsagePlanKey(BaseModel, dict):

    def __init__(self, id, type, name, value):
        super(UsagePlanKey, self).__init__()
        self['id'] = id
        self['name'] = name
        self['type'] = type
        self['value'] = value


class RestAPI(BaseModel):

    def __init__(self, id, region_name, name, description):
        self.id = id
        self.region_name = region_name
        self.name = name
        self.description = description
        self.create_date = int(time.time())

        self.deployments = {}
        self.stages = {}

        self.resources = {}
        self.add_child('/')  # Add default child

    def __repr__(self):
        return str(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "createdDate": int(time.time()),
        }

    def add_child(self, path, parent_id=None):
        child_id = create_id()
        child = Resource(id=child_id, region_name=self.region_name,
                         api_id=self.id, path_part=path, parent_id=parent_id)
        self.resources[child_id] = child
        return child

    def get_resource_for_path(self, path_after_stage_name):
        for resource in self.resources.values():
            if resource.get_path() == path_after_stage_name:
                return resource
        # TODO deal with no matching resource

    def resource_callback(self, request):
        path_after_stage_name = '/'.join(request.path_url.split("/")[2:])
        if not path_after_stage_name:
            path_after_stage_name = '/'

        resource = self.get_resource_for_path(path_after_stage_name)
        status_code, response = resource.get_response(request)
        return status_code, {}, response

    def update_integration_mocks(self, stage_name):
        stage_url_lower = STAGE_URL.format(api_id=self.id.lower(),
            region_name=self.region_name, stage_name=stage_name)
        stage_url_upper = STAGE_URL.format(api_id=self.id.upper(),
            region_name=self.region_name, stage_name=stage_name)

        responses.add_callback(responses.GET, stage_url_lower,
                               callback=self.resource_callback)
        responses.add_callback(responses.GET, stage_url_upper,
                               callback=self.resource_callback)

    def create_stage(self, name, deployment_id, variables=None, description='', cacheClusterEnabled=None, cacheClusterSize=None):
        if variables is None:
            variables = {}
        stage = Stage(name=name, deployment_id=deployment_id, variables=variables,
                      description=description, cacheClusterSize=cacheClusterSize, cacheClusterEnabled=cacheClusterEnabled)
        self.stages[name] = stage
        self.update_integration_mocks(name)
        return stage

    def create_deployment(self, name, description="", stage_variables=None):
        if stage_variables is None:
            stage_variables = {}
        deployment_id = create_id()
        deployment = Deployment(deployment_id, name, description)
        self.deployments[deployment_id] = deployment
        self.stages[name] = Stage(
            name=name, deployment_id=deployment_id, variables=stage_variables)
        self.update_integration_mocks(name)

        return deployment

    def get_deployment(self, deployment_id):
        return self.deployments[deployment_id]

    def get_stages(self):
        return list(self.stages.values())

    def get_deployments(self):
        return list(self.deployments.values())

    def delete_deployment(self, deployment_id):
        return self.deployments.pop(deployment_id)


class APIGatewayBackend(BaseBackend):

    def __init__(self, region_name):
        super(APIGatewayBackend, self).__init__()
        self.apis = {}
        self.keys = {}
        self.usage_plans = {}
        self.usage_plan_keys = {}
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
        stage = api.stages.get(stage_name)
        if stage is None:
            raise StageNotFoundException()
        else:
            return stage

    def get_stages(self, function_id):
        api = self.get_rest_api(function_id)
        return api.get_stages()

    def create_stage(self, function_id, stage_name, deploymentId,
                     variables=None, description='', cacheClusterEnabled=None, cacheClusterSize=None):
        if variables is None:
            variables = {}
        api = self.get_rest_api(function_id)
        api.create_stage(stage_name, deploymentId, variables=variables,
                         description=description, cacheClusterEnabled=cacheClusterEnabled, cacheClusterSize=cacheClusterSize)
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
        integration = self.get_integration(
            function_id, resource_id, method_type)
        integration_response = integration.create_integration_response(
            status_code, selection_pattern)
        return integration_response

    def get_integration_response(self, function_id, resource_id, method_type, status_code):
        integration = self.get_integration(
            function_id, resource_id, method_type)
        integration_response = integration.get_integration_response(
            status_code)
        return integration_response

    def delete_integration_response(self, function_id, resource_id, method_type, status_code):
        integration = self.get_integration(
            function_id, resource_id, method_type)
        integration_response = integration.delete_integration_response(
            status_code)
        return integration_response

    def create_deployment(self, function_id, name, description="", stage_variables=None):
        if stage_variables is None:
            stage_variables = {}
        api = self.get_rest_api(function_id)
        deployment = api.create_deployment(name, description, stage_variables)
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

    def create_apikey(self, payload):
        key = ApiKey(**payload)
        self.keys[key['id']] = key
        return key

    def get_apikeys(self):
        return list(self.keys.values())

    def get_apikey(self, api_key_id):
        return self.keys[api_key_id]

    def delete_apikey(self, api_key_id):
        self.keys.pop(api_key_id)
        return {}

    def create_usage_plan(self, payload):
        plan = UsagePlan(**payload)
        self.usage_plans[plan['id']] = plan
        return plan

    def get_usage_plans(self):
        return list(self.usage_plans.values())

    def get_usage_plan(self, usage_plan_id):
        return self.usage_plans[usage_plan_id]

    def delete_usage_plan(self, usage_plan_id):
        self.usage_plans.pop(usage_plan_id)
        return {}

    def create_usage_plan_key(self, usage_plan_id, payload):
        if usage_plan_id not in self.usage_plan_keys:
            self.usage_plan_keys[usage_plan_id] = {}

        key_id = payload["keyId"]
        if key_id not in self.keys:
            raise ApiKeyNotFoundException()

        api_key = self.keys[key_id]

        usage_plan_key = UsagePlanKey(id=key_id, type=payload["keyType"], name=api_key["name"], value=api_key["value"])
        self.usage_plan_keys[usage_plan_id][usage_plan_key['id']] = usage_plan_key
        return usage_plan_key

    def get_usage_plan_keys(self, usage_plan_id):
        if usage_plan_id not in self.usage_plan_keys:
            return []

        return list(self.usage_plan_keys[usage_plan_id].values())

    def get_usage_plan_key(self, usage_plan_id, key_id):
        return self.usage_plan_keys[usage_plan_id][key_id]

    def delete_usage_plan_key(self, usage_plan_id, key_id):
        self.usage_plan_keys[usage_plan_id].pop(key_id)
        return {}


apigateway_backends = {}
for region_name in Session().get_available_regions('apigateway'):
    apigateway_backends[region_name] = APIGatewayBackend(region_name)
