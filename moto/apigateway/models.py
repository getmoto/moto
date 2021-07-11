from __future__ import absolute_import
from __future__ import unicode_literals

import random
import string
import re
from copy import copy

import requests
import time

from boto3.session import Session

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import responses
from moto.core import ACCOUNT_ID, BaseBackend, BaseModel, CloudFormationModel
from .utils import create_id
from moto.core.utils import path_url
from .exceptions import (
    ApiKeyNotFoundException,
    UsagePlanNotFoundException,
    AwsProxyNotAllowed,
    CrossAccountNotAllowed,
    IntegrationMethodNotDefined,
    InvalidArn,
    InvalidIntegrationArn,
    InvalidHttpEndpoint,
    InvalidResourcePathException,
    AuthorizerNotFoundException,
    StageNotFoundException,
    RoleNotSpecified,
    NoIntegrationDefined,
    NoIntegrationResponseDefined,
    NoMethodDefined,
    ApiKeyAlreadyExists,
    DomainNameNotFound,
    InvalidDomainName,
    InvalidRestApiId,
    InvalidModelName,
    RestAPINotFound,
    ModelNotFound,
    ApiKeyValueMinLength,
)
from ..core.models import responses_mock
from moto.apigateway.exceptions import MethodNotFoundException

STAGE_URL = "https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}"


class Deployment(CloudFormationModel, dict):
    def __init__(self, deployment_id, name, description=""):
        super(Deployment, self).__init__()
        self["id"] = deployment_id
        self["stageName"] = name
        self["description"] = description
        self["createdDate"] = int(time.time())

    @staticmethod
    def cloudformation_name_type():
        return "Deployment"

    @staticmethod
    def cloudformation_type():
        return "AWS::ApiGateway::Deployment"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        rest_api_id = properties["RestApiId"]
        name = properties["StageName"]
        desc = properties.get("Description", "")
        backend = apigateway_backends[region_name]
        return backend.create_deployment(
            function_id=rest_api_id, name=name, description=desc
        )


class IntegrationResponse(BaseModel, dict):
    def __init__(
        self,
        status_code,
        selection_pattern=None,
        response_templates=None,
        content_handling=None,
    ):
        if response_templates is None:
            # response_templates = {"application/json": None}  # Note: removed for compatibility with TF
            response_templates = {}
        for key in response_templates.keys():
            response_templates[key] = (
                response_templates[key] or None
            )  # required for compatibility with TF
        self["responseTemplates"] = response_templates
        self["statusCode"] = status_code
        if selection_pattern:
            self["selectionPattern"] = selection_pattern
        if content_handling:
            self["contentHandling"] = content_handling


class Integration(BaseModel, dict):
    def __init__(
        self,
        integration_type,
        uri,
        http_method,
        request_templates=None,
        tls_config=None,
        cache_namespace=None,
    ):
        super(Integration, self).__init__()
        self["type"] = integration_type
        self["uri"] = uri
        self["httpMethod"] = http_method
        self["requestTemplates"] = request_templates
        # self["integrationResponses"] = {"200": IntegrationResponse(200)}  # commented out (tf-compat)
        self["integrationResponses"] = {}
        self["tlsConfig"] = tls_config
        self["cacheNamespace"] = cache_namespace

    def create_integration_response(
        self, status_code, selection_pattern, response_templates, content_handling
    ):
        if response_templates == {}:
            response_templates = None
        integration_response = IntegrationResponse(
            status_code, selection_pattern, response_templates, content_handling
        )
        self["integrationResponses"][status_code] = integration_response
        return integration_response

    def get_integration_response(self, status_code):
        result = self["integrationResponses"].get(status_code)
        if not result:
            raise NoIntegrationResponseDefined(status_code)
        return result

    def delete_integration_response(self, status_code):
        return self["integrationResponses"].pop(status_code, None)


class MethodResponse(BaseModel, dict):
    def __init__(self, status_code, response_models=None, response_parameters=None):
        super(MethodResponse, self).__init__()
        self["statusCode"] = status_code
        self["responseModels"] = response_models
        self["responseParameters"] = response_parameters


class Method(CloudFormationModel, dict):
    def __init__(self, method_type, authorization_type, **kwargs):
        super(Method, self).__init__()
        self.update(
            dict(
                httpMethod=method_type,
                authorizationType=authorization_type,
                authorizerId=kwargs.get("authorizer_id"),
                authorizationScopes=kwargs.get("authorization_scopes"),
                apiKeyRequired=kwargs.get("api_key_required") or False,
                requestParameters=None,
                requestModels=kwargs.get("request_models"),
                methodIntegration=None,
                operationName=kwargs.get("operation_name"),
                requestValidatorId=kwargs.get("request_validator_id"),
            )
        )
        self.method_responses = {}

    @staticmethod
    def cloudformation_name_type():
        return "Method"

    @staticmethod
    def cloudformation_type():
        return "AWS::ApiGateway::Method"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        rest_api_id = properties["RestApiId"]
        resource_id = properties["ResourceId"]
        method_type = properties["HttpMethod"]
        auth_type = properties["AuthorizationType"]
        key_req = properties["ApiKeyRequired"]
        backend = apigateway_backends[region_name]
        m = backend.create_method(
            function_id=rest_api_id,
            resource_id=resource_id,
            method_type=method_type,
            authorization_type=auth_type,
            api_key_required=key_req,
        )
        int_method = properties["Integration"]["IntegrationHttpMethod"]
        int_type = properties["Integration"]["Type"]
        int_uri = properties["Integration"]["Uri"]
        backend.create_integration(
            function_id=rest_api_id,
            resource_id=resource_id,
            method_type=method_type,
            integration_type=int_type,
            uri=int_uri,
            integration_method=int_method,
        )
        return m

    def create_response(self, response_code, response_models, response_parameters):
        method_response = MethodResponse(
            response_code, response_models, response_parameters
        )
        self.method_responses[response_code] = method_response
        return method_response

    def get_response(self, response_code):
        return self.method_responses.get(response_code)

    def delete_response(self, response_code):
        return self.method_responses.pop(response_code, None)


class Resource(CloudFormationModel):
    def __init__(self, id, region_name, api_id, path_part, parent_id):
        super(Resource, self).__init__()
        self.id = id
        self.region_name = region_name
        self.api_id = api_id
        self.path_part = path_part
        self.parent_id = parent_id
        self.resource_methods = {}

    def to_dict(self):
        response = {
            "path": self.get_path(),
            "id": self.id,
        }
        if self.resource_methods:
            response["resourceMethods"] = self.resource_methods
        if self.parent_id:
            response["parentId"] = self.parent_id
            response["pathPart"] = self.path_part
        return response

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return "Resource"

    @staticmethod
    def cloudformation_type():
        return "AWS::ApiGateway::Resource"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        api_id = properties["RestApiId"]
        parent = properties["ParentId"]
        path = properties["PathPart"]

        backend = apigateway_backends[region_name]
        if parent == api_id:
            # A Root path (/) is automatically created. Any new paths should use this as their parent
            resources = backend.list_resources(function_id=api_id)
            root_id = [resource for resource in resources if resource.path_part == "/"][
                0
            ].id
            parent = root_id
        return backend.create_resource(
            function_id=api_id, parent_resource_id=parent, path_part=path
        )

    def get_path(self):
        return self.get_parent_path() + self.path_part

    def get_parent_path(self):
        if self.parent_id:
            backend = apigateway_backends[self.region_name]
            parent = backend.get_resource(self.api_id, self.parent_id)
            parent_path = parent.get_path()
            if parent_path != "/":  # Root parent
                parent_path += "/"
            return parent_path
        else:
            return ""

    def get_response(self, request):
        integration = self.get_integration(request.method)
        integration_type = integration["type"]

        if integration_type == "HTTP":
            uri = integration["uri"]
            requests_func = getattr(requests, integration["httpMethod"].lower())
            response = requests_func(uri)
        else:
            raise NotImplementedError(
                "The {0} type has not been implemented".format(integration_type)
            )
        return response.status_code, response.text

    def add_method(
        self,
        method_type,
        authorization_type,
        api_key_required,
        request_models=None,
        operation_name=None,
        authorizer_id=None,
        authorization_scopes=None,
        request_validator_id=None,
    ):
        if authorization_scopes and not isinstance(authorization_scopes, list):
            authorization_scopes = [authorization_scopes]
        method = Method(
            method_type=method_type,
            authorization_type=authorization_type,
            api_key_required=api_key_required,
            request_models=request_models,
            operation_name=operation_name,
            authorizer_id=authorizer_id,
            authorization_scopes=authorization_scopes,
            request_validator_id=request_validator_id,
        )
        self.resource_methods[method_type] = method
        return method

    def get_method(self, method_type):
        method = self.resource_methods.get(method_type)
        if not method:
            raise MethodNotFoundException()
        return method

    def add_integration(
        self,
        method_type,
        integration_type,
        uri,
        request_templates=None,
        integration_method=None,
        tls_config=None,
        cache_namespace=None,
    ):
        integration_method = integration_method or method_type
        integration = Integration(
            integration_type,
            uri,
            integration_method,
            request_templates=request_templates,
            tls_config=tls_config,
            cache_namespace=cache_namespace,
        )
        self.resource_methods[method_type]["methodIntegration"] = integration
        return integration

    def get_integration(self, method_type):
        return self.resource_methods.get(method_type, {}).get("methodIntegration", {})

    def delete_integration(self, method_type):
        return self.resource_methods[method_type].pop("methodIntegration")


class Authorizer(BaseModel, dict):
    def __init__(self, id, name, authorizer_type, **kwargs):
        super(Authorizer, self).__init__()
        self["id"] = id
        self["name"] = name
        self["type"] = authorizer_type
        if kwargs.get("provider_arns"):
            self["providerARNs"] = kwargs.get("provider_arns")
        if kwargs.get("auth_type"):
            self["authType"] = kwargs.get("auth_type")
        if kwargs.get("authorizer_uri"):
            self["authorizerUri"] = kwargs.get("authorizer_uri")
        if kwargs.get("authorizer_credentials"):
            self["authorizerCredentials"] = kwargs.get("authorizer_credentials")
        if kwargs.get("identity_source"):
            self["identitySource"] = kwargs.get("identity_source")
        if kwargs.get("identity_validation_expression"):
            self["identityValidationExpression"] = kwargs.get(
                "identity_validation_expression"
            )
        self["authorizerResultTtlInSeconds"] = kwargs.get("authorizer_result_ttl")

    def apply_operations(self, patch_operations):
        for op in patch_operations:
            if "/authorizerUri" in op["path"]:
                self["authorizerUri"] = op["value"]
            elif "/authorizerCredentials" in op["path"]:
                self["authorizerCredentials"] = op["value"]
            elif "/authorizerResultTtlInSeconds" in op["path"]:
                self["authorizerResultTtlInSeconds"] = int(op["value"])
            elif "/authType" in op["path"]:
                self["authType"] = op["value"]
            elif "/identitySource" in op["path"]:
                self["identitySource"] = op["value"]
            elif "/identityValidationExpression" in op["path"]:
                self["identityValidationExpression"] = op["value"]
            elif "/name" in op["path"]:
                self["name"] = op["value"]
            elif "/providerARNs" in op["path"]:
                # TODO: add and remove
                raise Exception('Patch operation for "%s" not implemented' % op["path"])
            elif "/type" in op["path"]:
                self["type"] = op["value"]
            else:
                raise Exception('Patch operation "%s" not implemented' % op["op"])
        return self


class Stage(BaseModel, dict):
    def __init__(
        self,
        name=None,
        deployment_id=None,
        variables=None,
        description="",
        cacheClusterEnabled=False,
        cacheClusterSize=None,
        tags=None,
        tracing_enabled=None,
    ):
        super(Stage, self).__init__()
        if variables is None:
            variables = {}
        self["stageName"] = name
        self["deploymentId"] = deployment_id
        self["methodSettings"] = {}
        self["variables"] = variables
        self["description"] = description
        self["cacheClusterEnabled"] = cacheClusterEnabled
        if self["cacheClusterEnabled"]:
            self["cacheClusterSize"] = str(0.5)
        if cacheClusterSize is not None:
            self["cacheClusterSize"] = str(cacheClusterSize)
        if tags is not None:
            self["tags"] = tags
        if tracing_enabled is not None:
            self["tracingEnabled"] = tracing_enabled

    def apply_operations(self, patch_operations):
        for op in patch_operations:
            if "variables/" in op["path"]:
                self._apply_operation_to_variables(op)
            elif "/cacheClusterEnabled" in op["path"]:
                self["cacheClusterEnabled"] = self._str2bool(op["value"])
                if "cacheClusterSize" not in self and self["cacheClusterEnabled"]:
                    self["cacheClusterSize"] = str(0.5)
            elif "/cacheClusterSize" in op["path"]:
                self["cacheClusterSize"] = str(float(op["value"]))
            elif "/description" in op["path"]:
                self["description"] = op["value"]
            elif "/deploymentId" in op["path"]:
                self["deploymentId"] = op["value"]
            elif op["op"] == "replace":
                # Method Settings drop into here
                # (e.g., path could be '/*/*/logging/loglevel')
                split_path = op["path"].split("/", 3)
                if len(split_path) != 4:
                    continue
                self._patch_method_setting(
                    "/".join(split_path[1:3]), split_path[3], op["value"]
                )
            else:
                raise Exception('Patch operation "%s" not implemented' % op["op"])
        return self

    def _patch_method_setting(self, resource_path_and_method, key, value):
        updated_key = self._method_settings_translations(key)
        if updated_key is not None:
            if resource_path_and_method not in self["methodSettings"]:
                self["methodSettings"][
                    resource_path_and_method
                ] = self._get_default_method_settings()
            self["methodSettings"][resource_path_and_method][
                updated_key
            ] = self._convert_to_type(updated_key, value)

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
            "requireAuthorizationForCacheControl": True,
        }

    def _method_settings_translations(self, key):
        mappings = {
            "metrics/enabled": "metricsEnabled",
            "logging/loglevel": "loggingLevel",
            "logging/dataTrace": "dataTraceEnabled",
            "throttling/burstLimit": "throttlingBurstLimit",
            "throttling/rateLimit": "throttlingRateLimit",
            "caching/enabled": "cachingEnabled",
            "caching/ttlInSeconds": "cacheTtlInSeconds",
            "caching/dataEncrypted": "cacheDataEncrypted",
            "caching/requireAuthorizationForCacheControl": "requireAuthorizationForCacheControl",
            "caching/unauthorizedCacheControlHeaderStrategy": "unauthorizedCacheControlHeaderStrategy",
        }

        if key in mappings:
            return mappings[key]
        else:
            None

    def _str2bool(self, v):
        return v.lower() == "true"

    def _convert_to_type(self, key, val):
        type_mappings = {
            "metricsEnabled": "bool",
            "loggingLevel": "str",
            "dataTraceEnabled": "bool",
            "throttlingBurstLimit": "int",
            "throttlingRateLimit": "float",
            "cachingEnabled": "bool",
            "cacheTtlInSeconds": "int",
            "cacheDataEncrypted": "bool",
            "requireAuthorizationForCacheControl": "bool",
            "unauthorizedCacheControlHeaderStrategy": "str",
        }

        if key in type_mappings:
            type_value = type_mappings[key]

            if type_value == "bool":
                return self._str2bool(val)
            elif type_value == "int":
                return int(val)
            elif type_value == "float":
                return float(val)
            else:
                return str(val)
        else:
            return str(val)

    def _apply_operation_to_variables(self, op):
        key = op["path"][op["path"].rindex("variables/") + 10 :]
        if op["op"] == "remove":
            self["variables"].pop(key, None)
        elif op["op"] == "replace":
            self["variables"][key] = op["value"]
        else:
            raise Exception('Patch operation "%s" not implemented' % op["op"])


class ApiKey(BaseModel, dict):
    def __init__(
        self,
        name=None,
        description=None,
        enabled=False,
        generateDistinctId=False,
        value=None,
        stageKeys=[],
        tags=None,
        customerId=None,
    ):
        super(ApiKey, self).__init__()
        self["id"] = create_id()
        self["value"] = (
            value
            if value
            else "".join(random.sample(string.ascii_letters + string.digits, 40))
        )
        self["name"] = name
        self["customerId"] = customerId
        self["description"] = description
        self["enabled"] = enabled
        self["createdDate"] = self["lastUpdatedDate"] = int(time.time())
        self["stageKeys"] = stageKeys
        self["tags"] = tags

    def update_operations(self, patch_operations):
        for op in patch_operations:
            if op["op"] == "replace":
                if "/name" in op["path"]:
                    self["name"] = op["value"]
                elif "/customerId" in op["path"]:
                    self["customerId"] = op["value"]
                elif "/description" in op["path"]:
                    self["description"] = op["value"]
                elif "/enabled" in op["path"]:
                    self["enabled"] = self._str2bool(op["value"])
            else:
                raise Exception('Patch operation "%s" not implemented' % op["op"])
        return self

    def _str2bool(self, v):
        return v.lower() == "true"


class UsagePlan(BaseModel, dict):
    def __init__(
        self,
        name=None,
        description=None,
        apiStages=None,
        throttle=None,
        quota=None,
        productCode=None,
        tags=None,
    ):
        super(UsagePlan, self).__init__()
        self["id"] = create_id()
        self["name"] = name
        self["description"] = description
        self["apiStages"] = apiStages if apiStages else []
        self["throttle"] = throttle
        self["quota"] = quota
        self["productCode"] = productCode
        self["tags"] = tags

    def apply_patch_operations(self, patch_operations):
        for op in patch_operations:
            path = op["path"]
            value = op["value"]
            if op["op"] == "replace":
                if "/name" in path:
                    self["name"] = value
                if "/productCode" in path:
                    self["productCode"] = value
                if "/description" in path:
                    self["description"] = value
                if "/quota/limit" in path:
                    self["quota"]["limit"] = value
                if "/quota/period" in path:
                    self["quota"]["period"] = value
                if "/throttle/rateLimit" in path:
                    self["throttle"]["rateLimit"] = value
                if "/throttle/burstLimit" in path:
                    self["throttle"]["burstLimit"] = value


class UsagePlanKey(BaseModel, dict):
    def __init__(self, id, type, name, value):
        super(UsagePlanKey, self).__init__()
        self["id"] = id
        self["name"] = name
        self["type"] = type
        self["value"] = value


class RestAPI(CloudFormationModel):
    def __init__(self, id, region_name, name, description, **kwargs):
        super(RestAPI, self).__init__()
        self.id = id
        self.region_name = region_name
        self.name = name
        self.description = description
        self.version = kwargs.get("version") or "V1"
        self.binaryMediaTypes = kwargs.get("binaryMediaTypes") or []
        self.create_date = int(time.time())
        self.api_key_source = kwargs.get("api_key_source") or "HEADER"
        self.policy = kwargs.get("policy") or None
        self.endpoint_configuration = kwargs.get("endpoint_configuration") or {
            "types": ["EDGE"]
        }
        self.tags = kwargs.get("tags") or {}
        self.disableExecuteApiEndpoint = (
            kwargs.get("disableExecuteApiEndpoint") or False
        )
        self.minimum_compression_size = kwargs.get("minimum_compression_size")
        self.deployments = {}
        self.authorizers = {}
        self.stages = {}
        self.resources = {}
        self.models = {}
        self.add_child("/")  # Add default child

    def __repr__(self):
        return str(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "binaryMediaTypes": self.binaryMediaTypes,
            "createdDate": self.create_date,
            "apiKeySource": self.api_key_source,
            "endpointConfiguration": self.endpoint_configuration,
            "tags": self.tags,
            "policy": self.policy,
            "disableExecuteApiEndpoint": self.disableExecuteApiEndpoint,
            "minimumCompressionSize": self.minimum_compression_size,
        }

    def apply_patch_operations(self, patch_operations):
        for op in patch_operations:
            path = op["path"]
            value = op["value"]
            if op["op"] == "replace":
                if "/name" in path:
                    self.name = value
                if "/description" in path:
                    self.description = value
                if "/apiKeySource" in path:
                    self.api_key_source = value
                if "/binaryMediaTypes" in path:
                    self.binaryMediaTypes = value
                if "/disableExecuteApiEndpoint" in path:
                    self.disableExecuteApiEndpoint = bool(value)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "RootResourceId":
            for res_id, res_obj in self.resources.items():
                if res_obj.path_part == "/" and not res_obj.parent_id:
                    return res_id
            raise Exception("Unable to find root resource for API %s" % self)
        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return "RestApi"

    @staticmethod
    def cloudformation_type():
        return "AWS::ApiGateway::RestApi"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        name = properties["Name"]
        desc = properties.get("Description", "")
        config = properties.get("EndpointConfiguration", None)
        backend = apigateway_backends[region_name]
        return backend.create_rest_api(
            name=name, description=desc, endpoint_configuration=config
        )

    def add_child(self, path, parent_id=None):
        child_id = create_id()
        child = Resource(
            id=child_id,
            region_name=self.region_name,
            api_id=self.id,
            path_part=path,
            parent_id=parent_id,
        )
        self.resources[child_id] = child
        return child

    def add_model(
        self,
        name,
        description=None,
        schema=None,
        content_type=None,
        cli_input_json=None,
        generate_cli_skeleton=None,
    ):
        model_id = create_id()
        new_model = Model(
            id=model_id,
            name=name,
            description=description,
            schema=schema,
            content_type=content_type,
            cli_input_json=cli_input_json,
            generate_cli_skeleton=generate_cli_skeleton,
        )

        self.models[name] = new_model
        return new_model

    def get_resource_for_path(self, path_after_stage_name):
        for resource in self.resources.values():
            if resource.get_path() == path_after_stage_name:
                return resource
        # TODO deal with no matching resource

    def resource_callback(self, request):
        path = path_url(request.url)
        path_after_stage_name = "/".join(path.split("/")[2:])
        if not path_after_stage_name:
            path_after_stage_name = "/"

        resource = self.get_resource_for_path(path_after_stage_name)
        status_code, response = resource.get_response(request)
        return status_code, {}, response

    def update_integration_mocks(self, stage_name):
        stage_url_lower = STAGE_URL.format(
            api_id=self.id.lower(), region_name=self.region_name, stage_name=stage_name
        )
        stage_url_upper = STAGE_URL.format(
            api_id=self.id.upper(), region_name=self.region_name, stage_name=stage_name
        )

        for url in [stage_url_lower, stage_url_upper]:
            responses_mock._matches.insert(
                0,
                responses.CallbackResponse(
                    url=url,
                    method=responses.GET,
                    callback=self.resource_callback,
                    content_type="text/plain",
                    match_querystring=False,
                ),
            )

    def create_authorizer(
        self,
        id,
        name,
        authorizer_type,
        provider_arns=None,
        auth_type=None,
        authorizer_uri=None,
        authorizer_credentials=None,
        identity_source=None,
        identiy_validation_expression=None,
        authorizer_result_ttl=None,
    ):
        authorizer = Authorizer(
            id=id,
            name=name,
            authorizer_type=authorizer_type,
            provider_arns=provider_arns,
            auth_type=auth_type,
            authorizer_uri=authorizer_uri,
            authorizer_credentials=authorizer_credentials,
            identity_source=identity_source,
            identiy_validation_expression=identiy_validation_expression,
            authorizer_result_ttl=authorizer_result_ttl,
        )
        self.authorizers[id] = authorizer
        return authorizer

    def create_stage(
        self,
        name,
        deployment_id,
        variables=None,
        description="",
        cacheClusterEnabled=None,
        cacheClusterSize=None,
        tags=None,
        tracing_enabled=None,
    ):
        if variables is None:
            variables = {}
        stage = Stage(
            name=name,
            deployment_id=deployment_id,
            variables=variables,
            description=description,
            cacheClusterSize=cacheClusterSize,
            cacheClusterEnabled=cacheClusterEnabled,
            tags=tags,
            tracing_enabled=tracing_enabled,
        )
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
            name=name, deployment_id=deployment_id, variables=stage_variables
        )
        self.update_integration_mocks(name)

        return deployment

    def get_deployment(self, deployment_id):
        return self.deployments[deployment_id]

    def get_authorizers(self):
        return list(self.authorizers.values())

    def get_stages(self):
        return list(self.stages.values())

    def get_deployments(self):
        return list(self.deployments.values())

    def delete_deployment(self, deployment_id):
        return self.deployments.pop(deployment_id)


class DomainName(BaseModel, dict):
    def __init__(self, domain_name, **kwargs):
        super(DomainName, self).__init__()
        self["domainName"] = domain_name
        self["regionalDomainName"] = "d-%s.execute-api.%s.amazonaws.com" % (
            create_id(), kwargs.get('region_name') or "us-east-1")
        self["distributionDomainName"] = "d%s.cloudfront.net" % create_id()
        self["domainNameStatus"] = "AVAILABLE"
        self["domainNameStatusMessage"] = "Domain Name Available"
        self["regionalHostedZoneId"] = "Z2FDTNDATAQYW2"
        self["distributionHostedZoneId"] = "Z2FDTNDATAQYW2"
        self["certificateUploadDate"] = int(time.time())
        if kwargs.get("certificate_name"):
            self["certificateName"] = kwargs.get("certificate_name")
        if kwargs.get("certificate_arn"):
            self["certificateArn"] = kwargs.get("certificate_arn")
        if kwargs.get("certificate_body"):
            self["certificateBody"] = kwargs.get("certificate_body")
        if kwargs.get("tags"):
            self["tags"] = kwargs.get("tags")
        if kwargs.get("security_policy"):
            self["securityPolicy"] = kwargs.get("security_policy")
        if kwargs.get("certificate_chain"):
            self["certificateChain"] = kwargs.get("certificate_chain")
        if kwargs.get("regional_certificate_name"):
            self["regionalCertificateName"] = kwargs.get("regional_certificate_name")
        if kwargs.get("certificate_private_key"):
            self["certificatePrivateKey"] = kwargs.get("certificate_private_key")
        if kwargs.get("regional_certificate_arn"):
            self["regionalCertificateArn"] = kwargs.get("regional_certificate_arn")
        if kwargs.get("endpoint_configuration"):
            self["endpointConfiguration"] = kwargs.get("endpoint_configuration")
        if kwargs.get("generate_cli_skeleton"):
            self["generateCliSkeleton"] = kwargs.get("generate_cli_skeleton")


class Model(BaseModel, dict):
    def __init__(self, id, name, **kwargs):
        super(Model, self).__init__()
        self["id"] = id
        self["name"] = name
        if kwargs.get("description"):
            self["description"] = kwargs.get("description")
        if kwargs.get("schema"):
            self["schema"] = kwargs.get("schema")
        if kwargs.get("content_type"):
            self["contentType"] = kwargs.get("content_type")
        if kwargs.get("cli_input_json"):
            self["cliInputJson"] = kwargs.get("cli_input_json")
        if kwargs.get("generate_cli_skeleton"):
            self["generateCliSkeleton"] = kwargs.get("generate_cli_skeleton")


class APIGatewayBackend(BaseBackend):
    def __init__(self, region_name):
        super(APIGatewayBackend, self).__init__()
        self.apis = {}
        self.keys = {}
        self.usage_plans = {}
        self.usage_plan_keys = {}
        self.domain_names = {}
        self.models = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_rest_api(
        self,
        name,
        description,
        api_key_source=None,
        endpoint_configuration=None,
        tags=None,
        policy=None,
        minimum_compression_size=None,
    ):
        api_id = create_id()
        rest_api = RestAPI(
            api_id,
            self.region_name,
            name,
            description,
            api_key_source=api_key_source,
            endpoint_configuration=endpoint_configuration,
            tags=tags,
            policy=policy,
            minimum_compression_size=minimum_compression_size,
        )
        self.apis[api_id] = rest_api
        return rest_api

    def get_rest_api(self, function_id):
        rest_api = self.apis.get(function_id)
        if rest_api is None:
            raise RestAPINotFound()
        return rest_api

    def update_rest_api(self, function_id, patch_operations):
        rest_api = self.apis.get(function_id)
        if rest_api is None:
            raise RestAPINotFound()
        self.apis[function_id].apply_patch_operations(patch_operations)
        return self.apis[function_id]

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
        if not re.match("^\\{?[a-zA-Z0-9._-]+\\+?\\}?$", path_part):
            raise InvalidResourcePathException()
        api = self.get_rest_api(function_id)
        child = api.add_child(path=path_part, parent_id=parent_resource_id)
        return child

    def delete_resource(self, function_id, resource_id):
        api = self.get_rest_api(function_id)
        resource = api.resources.pop(resource_id)
        return resource

    def get_method(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.get_method(method_type)

    def create_method(
        self,
        function_id,
        resource_id,
        method_type,
        authorization_type,
        api_key_required=None,
        request_models=None,
        operation_name=None,
        authorizer_id=None,
        authorization_scopes=None,
        request_validator_id=None,
    ):
        resource = self.get_resource(function_id, resource_id)
        method = resource.add_method(
            method_type,
            authorization_type,
            api_key_required=api_key_required,
            request_models=request_models,
            operation_name=operation_name,
            authorizer_id=authorizer_id,
            authorization_scopes=authorization_scopes,
            request_validator_id=request_validator_id,
        )
        return method

    def update_method(self, function_id, resource_id, method_type, patch_operations):
        resource = self.get_resource(function_id, resource_id)
        method = resource.get_method(method_type)
        return method.apply_operations(patch_operations)

    def get_authorizer(self, restapi_id, authorizer_id):
        api = self.get_rest_api(restapi_id)
        authorizer = api.authorizers.get(authorizer_id)
        if authorizer is None:
            raise AuthorizerNotFoundException()
        else:
            return authorizer

    def get_authorizers(self, restapi_id):
        api = self.get_rest_api(restapi_id)
        return api.get_authorizers()

    def create_authorizer(self, restapi_id, name, authorizer_type, **kwargs):
        api = self.get_rest_api(restapi_id)
        authorizer_id = create_id()
        authorizer = api.create_authorizer(
            authorizer_id,
            name,
            authorizer_type,
            provider_arns=kwargs.get("provider_arns"),
            auth_type=kwargs.get("auth_type"),
            authorizer_uri=kwargs.get("authorizer_uri"),
            authorizer_credentials=kwargs.get("authorizer_credentials"),
            identity_source=kwargs.get("identity_source"),
            identiy_validation_expression=kwargs.get("identiy_validation_expression"),
            authorizer_result_ttl=kwargs.get("authorizer_result_ttl"),
        )
        return api.authorizers.get(authorizer["id"])

    def update_authorizer(self, restapi_id, authorizer_id, patch_operations):
        authorizer = self.get_authorizer(restapi_id, authorizer_id)
        if not authorizer:
            api = self.get_rest_api(restapi_id)
            authorizer = api.authorizers[authorizer_id] = Authorizer()
        return authorizer.apply_operations(patch_operations)

    def delete_authorizer(self, restapi_id, authorizer_id):
        api = self.get_rest_api(restapi_id)
        del api.authorizers[authorizer_id]

    def get_stage(self, function_id, stage_name):
        api = self.get_rest_api(function_id)
        stage = api.stages.get(stage_name)
        if stage is None:
            raise StageNotFoundException()
        return stage

    def get_stages(self, function_id):
        api = self.get_rest_api(function_id)
        return api.get_stages()

    def create_stage(
        self,
        function_id,
        stage_name,
        deploymentId,
        variables=None,
        description="",
        cacheClusterEnabled=None,
        cacheClusterSize=None,
        tags=None,
        tracing_enabled=None,
    ):
        if variables is None:
            variables = {}
        api = self.get_rest_api(function_id)
        api.create_stage(
            stage_name,
            deploymentId,
            variables=variables,
            description=description,
            cacheClusterEnabled=cacheClusterEnabled,
            cacheClusterSize=cacheClusterSize,
            tags=tags,
            tracing_enabled=tracing_enabled,
        )
        return api.stages.get(stage_name)

    def update_stage(self, function_id, stage_name, patch_operations):
        stage = self.get_stage(function_id, stage_name)
        if not stage:
            api = self.get_rest_api(function_id)
            stage = api.stages[stage_name] = Stage()
        return stage.apply_operations(patch_operations)

    def delete_stage(self, function_id, stage_name):
        api = self.get_rest_api(function_id)
        deleted = api.stages.pop(stage_name, None)
        if not deleted:
            raise StageNotFoundException()

    def get_method_response(self, function_id, resource_id, method_type, response_code):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.get_response(response_code)
        return method_response

    def create_method_response(
        self,
        function_id,
        resource_id,
        method_type,
        response_code,
        response_models,
        response_parameters,
    ):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.create_response(
            response_code, response_models, response_parameters
        )
        return method_response

    def update_method_response(
        self, function_id, resource_id, method_type, response_code, patch_operations
    ):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.get_response(response_code)
        method_response.apply_operations(patch_operations)
        return method_response

    def delete_method_response(
        self, function_id, resource_id, method_type, response_code
    ):
        method = self.get_method(function_id, resource_id, method_type)
        method_response = method.delete_response(response_code)
        return method_response

    def create_integration(
        self,
        function_id,
        resource_id,
        method_type,
        integration_type,
        uri,
        integration_method=None,
        credentials=None,
        request_templates=None,
        tls_config=None,
        cache_namespace=None,
    ):
        resource = self.get_resource(function_id, resource_id)
        if credentials and not re.match(
            "^arn:aws:iam::" + str(ACCOUNT_ID), credentials
        ):
            raise CrossAccountNotAllowed()
        if not integration_method and integration_type in [
            "HTTP",
            "HTTP_PROXY",
            "AWS",
            "AWS_PROXY",
        ]:
            raise IntegrationMethodNotDefined()
        if integration_type in ["AWS_PROXY"] and re.match(
            "^arn:aws:apigateway:[a-zA-Z0-9-]+:s3", uri
        ):
            raise AwsProxyNotAllowed()
        if (
            integration_type in ["AWS"]
            and re.match("^arn:aws:apigateway:[a-zA-Z0-9-]+:s3", uri)
            and not credentials
        ):
            raise RoleNotSpecified()
        if integration_type in ["HTTP", "HTTP_PROXY"] and not self._uri_validator(uri):
            raise InvalidHttpEndpoint()
        if integration_type in ["AWS", "AWS_PROXY"] and not re.match("^arn:aws:", uri):
            raise InvalidArn()
        if integration_type in ["AWS", "AWS_PROXY"] and not re.match(
            "^arn:aws:apigateway:[a-zA-Z0-9-]+:[a-zA-Z0-9-]+:(path|action)/", uri
        ):
            raise InvalidIntegrationArn()
        integration = resource.add_integration(
            method_type,
            integration_type,
            uri,
            integration_method=integration_method,
            request_templates=request_templates,
            tls_config=tls_config,
            cache_namespace=cache_namespace,
        )
        return integration

    def get_integration(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.get_integration(method_type)

    def delete_integration(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.delete_integration(method_type)

    def create_integration_response(
        self,
        function_id,
        resource_id,
        method_type,
        status_code,
        selection_pattern,
        response_templates,
        content_handling,
    ):
        integration = self.get_integration(function_id, resource_id, method_type)
        integration_response = integration.create_integration_response(
            status_code, selection_pattern, response_templates, content_handling
        )
        return integration_response

    def get_integration_response(
        self, function_id, resource_id, method_type, status_code
    ):
        integration = self.get_integration(function_id, resource_id, method_type)
        integration_response = integration.get_integration_response(status_code)
        return integration_response

    def delete_integration_response(
        self, function_id, resource_id, method_type, status_code
    ):
        integration = self.get_integration(function_id, resource_id, method_type)
        integration_response = integration.delete_integration_response(status_code)
        return integration_response

    def create_deployment(
        self, function_id, name, description="", stage_variables=None
    ):
        if stage_variables is None:
            stage_variables = {}
        api = self.get_rest_api(function_id)
        methods = [
            list(res.resource_methods.values())
            for res in self.list_resources(function_id)
        ]
        methods = [m for sublist in methods for m in sublist]
        if not any(methods):
            raise NoMethodDefined()
        method_integrations = [
            method["methodIntegration"] if "methodIntegration" in method else None
            for method in methods
        ]
        if not any(method_integrations):
            raise NoIntegrationDefined()
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

    def create_api_key(self, payload):
        if payload.get("value"):
            if len(payload.get("value", [])) < 20:
                raise ApiKeyValueMinLength()
            for api_key in self.get_api_keys(include_values=True):
                if api_key.get("value") == payload["value"]:
                    raise ApiKeyAlreadyExists()
        key = ApiKey(**payload)
        self.keys[key["id"]] = key
        return key

    def get_api_keys(self, include_values=False):
        api_keys = list(self.keys.values())

        if not include_values:
            keys = []
            for api_key in list(self.keys.values()):
                new_key = copy(api_key)
                del new_key["value"]
                keys.append(new_key)
            api_keys = keys

        return api_keys

    def get_api_key(self, api_key_id, include_value=False):
        api_key = self.keys.get(api_key_id)
        if not api_key:
            raise ApiKeyNotFoundException()

        if not include_value:
            new_key = copy(api_key)
            del new_key["value"]
            api_key = new_key

        return api_key

    def update_api_key(self, api_key_id, patch_operations):
        key = self.keys[api_key_id]
        return key.update_operations(patch_operations)

    def delete_api_key(self, api_key_id):
        self.keys.pop(api_key_id)
        return {}

    def create_usage_plan(self, payload):
        plan = UsagePlan(**payload)
        self.usage_plans[plan["id"]] = plan
        return plan

    def get_usage_plans(self, api_key_id=None):
        plans = list(self.usage_plans.values())
        if api_key_id is not None:
            plans = [
                plan
                for plan in plans
                if self.usage_plan_keys.get(plan["id"], {}).get(api_key_id, False)
            ]
        return plans

    def get_usage_plan(self, usage_plan_id):
        if usage_plan_id not in self.usage_plans:
            raise UsagePlanNotFoundException()
        return self.usage_plans[usage_plan_id]

    def update_usage_plan(self, usage_plan_id, patch_operations):
        if usage_plan_id not in self.usage_plans:
            raise UsagePlanNotFoundException()
        self.usage_plans[usage_plan_id].apply_patch_operations(patch_operations)
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

        usage_plan_key = UsagePlanKey(
            id=key_id,
            type=payload["keyType"],
            name=api_key["name"],
            value=api_key["value"],
        )
        self.usage_plan_keys[usage_plan_id][usage_plan_key["id"]] = usage_plan_key
        return usage_plan_key

    def get_usage_plan_keys(self, usage_plan_id):
        if usage_plan_id not in self.usage_plan_keys:
            return []

        return list(self.usage_plan_keys[usage_plan_id].values())

    def get_usage_plan_key(self, usage_plan_id, key_id):
        # first check if is a valid api key
        if key_id not in self.keys:
            raise ApiKeyNotFoundException()

        # then check if is a valid api key and that the key is in the plan
        if (
            usage_plan_id not in self.usage_plan_keys
            or key_id not in self.usage_plan_keys[usage_plan_id]
        ):
            raise UsagePlanNotFoundException()

        return self.usage_plan_keys[usage_plan_id][key_id]

    def delete_usage_plan_key(self, usage_plan_id, key_id):
        self.usage_plan_keys[usage_plan_id].pop(key_id)
        return {}

    def _uri_validator(self, uri):
        try:
            result = urlparse(uri)
            return all([result.scheme, result.netloc, result.path or "/"])
        except Exception:
            return False

    def create_domain_name(
        self,
        domain_name,
        certificate_name=None,
        tags=None,
        certificate_arn=None,
        certificate_body=None,
        certificate_private_key=None,
        certificate_chain=None,
        regional_certificate_name=None,
        regional_certificate_arn=None,
        endpoint_configuration=None,
        security_policy=None,
        generate_cli_skeleton=None,
    ):

        if not domain_name:
            raise InvalidDomainName()

        new_domain_name = DomainName(
            domain_name=domain_name,
            certificate_name=certificate_name,
            certificate_private_key=certificate_private_key,
            certificate_arn=certificate_arn,
            certificate_body=certificate_body,
            certificate_chain=certificate_chain,
            regional_certificate_name=regional_certificate_name,
            regional_certificate_arn=regional_certificate_arn,
            endpoint_configuration=endpoint_configuration,
            tags=tags,
            security_policy=security_policy,
            generate_cli_skeleton=generate_cli_skeleton,
            region_name=self.region_name,
        )

        self.domain_names[domain_name] = new_domain_name
        return new_domain_name

    def get_domain_names(self):
        return list(self.domain_names.values())

    def get_domain_name(self, domain_name):
        domain_info = self.domain_names.get(domain_name)
        if domain_info is None:
            raise DomainNameNotFound()
        else:
            return self.domain_names[domain_name]

    def delete_domain_name(self, domain_name):
        domain_info = self.domain_names.pop(domain_name, None)
        if domain_info is None:
            raise DomainNameNotFound()

    def update_domain_name(self, domain_name, patch_operations):
        domain_info = self.domain_names.get(domain_name)
        if not domain_info:
            raise DomainNameNotFound()
        domain_info.apply_patch_operations(patch_operations)
        return domain_info

    def create_model(
        self,
        rest_api_id,
        name,
        content_type,
        description=None,
        schema=None,
        cli_input_json=None,
        generate_cli_skeleton=None,
    ):

        if not rest_api_id:
            raise InvalidRestApiId
        if not name:
            raise InvalidModelName

        api = self.get_rest_api(rest_api_id)
        new_model = api.add_model(
            name=name,
            description=description,
            schema=schema,
            content_type=content_type,
            cli_input_json=cli_input_json,
            generate_cli_skeleton=generate_cli_skeleton,
        )

        return new_model

    def get_models(self, rest_api_id):
        if not rest_api_id:
            raise InvalidRestApiId
        api = self.get_rest_api(rest_api_id)
        models = api.models.values()
        return list(models)

    def get_model(self, rest_api_id, model_name):
        if not rest_api_id:
            raise InvalidRestApiId
        api = self.get_rest_api(rest_api_id)
        model = api.models.get(model_name)
        if model is None:
            raise ModelNotFound
        else:
            return model


apigateway_backends = {}
for region_name in Session().get_available_regions("apigateway"):
    apigateway_backends[region_name] = APIGatewayBackend(region_name)
for region_name in Session().get_available_regions(
    "apigateway", partition_name="aws-us-gov"
):
    apigateway_backends[region_name] = APIGatewayBackend(region_name)
for region_name in Session().get_available_regions(
    "apigateway", partition_name="aws-cn"
):
    apigateway_backends[region_name] = APIGatewayBackend(region_name)
