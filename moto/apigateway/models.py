from __future__ import absolute_import

import random
import string
import re
from collections import defaultdict
from copy import copy

from openapi_spec_validator import validate_spec
import time

from urllib.parse import urlparse
import responses

from openapi_spec_validator.exceptions import OpenAPIValidationError
from moto.core import get_account_id, BaseBackend, BaseModel, CloudFormationModel
from .utils import create_id, to_path
from moto.core.utils import path_url, BackendDict
from .integration_parsers.aws_parser import TypeAwsParser
from .integration_parsers.http_parser import TypeHttpParser
from .integration_parsers.unknown_parser import TypeUnknownParser
from .exceptions import (
    ConflictException,
    DeploymentNotFoundException,
    ApiKeyNotFoundException,
    UsagePlanNotFoundException,
    AwsProxyNotAllowed,
    CrossAccountNotAllowed,
    IntegrationMethodNotDefined,
    InvalidArn,
    InvalidIntegrationArn,
    InvalidHttpEndpoint,
    InvalidOpenAPIDocumentException,
    InvalidOpenApiDocVersionException,
    InvalidOpenApiModeException,
    InvalidResourcePathException,
    AuthorizerNotFoundException,
    StageNotFoundException,
    ResourceIdNotFoundException,
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
    RequestValidatorNotFound,
    ModelNotFound,
    ApiKeyValueMinLength,
    InvalidBasePathException,
    InvalidRestApiIdForBasePathMappingException,
    InvalidStageException,
    BasePathConflictException,
    BasePathNotFoundException,
    StageStillActive,
    VpcLinkNotFound,
    ValidationException,
    GatewayResponseNotFound,
)
from ..core.models import responses_mock
from moto.apigateway.exceptions import MethodNotFoundException

STAGE_URL = "https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}"


class Deployment(CloudFormationModel, dict):
    def __init__(self, deployment_id, name, description=""):
        super().__init__()
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
        cls, resource_name, cloudformation_json, region_name, **kwargs
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
        passthrough_behavior="WHEN_NO_MATCH",
        cache_key_parameters=None,
        tls_config=None,
        cache_namespace=None,
        timeout_in_millis=None,
    ):
        super().__init__()
        self["type"] = integration_type
        self["uri"] = uri
        self["httpMethod"] = http_method if integration_type != "MOCK" else None
        self["passthroughBehavior"] = passthrough_behavior
        self["cacheKeyParameters"] = cache_key_parameters or []
        self["requestTemplates"] = request_templates
        # self["integrationResponses"] = {"200": IntegrationResponse(200)}  # commented out (tf-compat)
        self[
            "integrationResponses"
        ] = None  # prevent json serialization from including them if none provided
        self["tlsConfig"] = tls_config
        self["cacheNamespace"] = cache_namespace
        self["timeoutInMillis"] = timeout_in_millis

    def create_integration_response(
        self, status_code, selection_pattern, response_templates, content_handling
    ):
        if response_templates == {}:
            response_templates = None
        integration_response = IntegrationResponse(
            status_code, selection_pattern, response_templates, content_handling
        )
        if self.get("integrationResponses") is None:
            self["integrationResponses"] = {}
        self["integrationResponses"][status_code] = integration_response
        return integration_response

    def get_integration_response(self, status_code):
        result = self.get("integrationResponses", {}).get(status_code)
        if not result:
            raise NoIntegrationResponseDefined()
        return result

    def delete_integration_response(self, status_code):
        return self.get("integrationResponses", {}).pop(status_code, None)


class MethodResponse(BaseModel, dict):
    def __init__(self, status_code, response_models=None, response_parameters=None):
        super().__init__()
        self["statusCode"] = status_code
        self["responseModels"] = response_models
        self["responseParameters"] = response_parameters


class Method(CloudFormationModel, dict):
    def __init__(self, method_type, authorization_type, **kwargs):
        super().__init__()
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
        self["methodResponses"] = {}

    @staticmethod
    def cloudformation_name_type():
        return "Method"

    @staticmethod
    def cloudformation_type():
        return "AWS::ApiGateway::Method"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        rest_api_id = properties["RestApiId"]
        resource_id = properties["ResourceId"]
        method_type = properties["HttpMethod"]
        auth_type = properties["AuthorizationType"]
        key_req = properties["ApiKeyRequired"]
        backend = apigateway_backends[region_name]
        m = backend.put_method(
            function_id=rest_api_id,
            resource_id=resource_id,
            method_type=method_type,
            authorization_type=auth_type,
            api_key_required=key_req,
        )
        int_method = properties["Integration"]["IntegrationHttpMethod"]
        int_type = properties["Integration"]["Type"]
        int_uri = properties["Integration"]["Uri"]
        backend.put_integration(
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
        self["methodResponses"][response_code] = method_response
        return method_response

    def get_response(self, response_code):
        return self["methodResponses"].get(response_code)

    def delete_response(self, response_code):
        return self["methodResponses"].pop(response_code, None)


class Resource(CloudFormationModel):
    def __init__(self, resource_id, region_name, api_id, path_part, parent_id):
        super().__init__()
        self.id = resource_id
        self.region_name = region_name
        self.api_id = api_id
        self.path_part = path_part
        self.parent_id = parent_id
        self.resource_methods = {}
        self.integration_parsers = defaultdict(TypeUnknownParser)
        self.integration_parsers["HTTP"] = TypeHttpParser()
        self.integration_parsers["AWS"] = TypeAwsParser()

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
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        api_id = properties["RestApiId"]
        parent = properties["ParentId"]
        path = properties["PathPart"]

        backend = apigateway_backends[region_name]
        if parent == api_id:
            # A Root path (/) is automatically created. Any new paths should use this as their parent
            resources = backend.get_resources(function_id=api_id)
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

        status, result = self.integration_parsers[integration_type].invoke(
            request, integration
        )

        return status, result

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

    def delete_method(self, method_type):
        self.resource_methods.pop(method_type)

    def add_integration(
        self,
        method_type,
        integration_type,
        uri,
        request_templates=None,
        passthrough_behavior=None,
        integration_method=None,
        tls_config=None,
        cache_namespace=None,
        timeout_in_millis=None,
    ):
        integration_method = integration_method or method_type
        integration = Integration(
            integration_type,
            uri,
            integration_method,
            request_templates=request_templates,
            passthrough_behavior=passthrough_behavior,
            tls_config=tls_config,
            cache_namespace=cache_namespace,
            timeout_in_millis=timeout_in_millis,
        )
        self.resource_methods[method_type]["methodIntegration"] = integration
        return integration

    def get_integration(self, method_type):
        return self.resource_methods.get(method_type, {}).get("methodIntegration", {})

    def delete_integration(self, method_type):
        return self.resource_methods[method_type].pop("methodIntegration")


class Authorizer(BaseModel, dict):
    def __init__(self, authorizer_id, name, authorizer_type, **kwargs):
        super().__init__()
        self["id"] = authorizer_id
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
        super().__init__()
        if variables is None:
            variables = {}
        self["stageName"] = name
        self["deploymentId"] = deployment_id
        self["methodSettings"] = {}
        self["variables"] = variables
        self["description"] = description
        self["cacheClusterEnabled"] = cacheClusterEnabled
        if self["cacheClusterEnabled"]:
            self["cacheClusterStatus"] = "AVAILABLE"
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
                if self["cacheClusterEnabled"]:
                    self["cacheClusterStatus"] = "AVAILABLE"
                    if "cacheClusterSize" not in self:
                        self["cacheClusterSize"] = str(0.5)
                else:
                    self["cacheClusterStatus"] = "NOT_AVAILABLE"
            elif "/cacheClusterSize" in op["path"]:
                self["cacheClusterSize"] = str(op["value"])
            elif "/description" in op["path"]:
                self["description"] = op["value"]
            elif "/deploymentId" in op["path"]:
                self["deploymentId"] = op["value"]
            elif op["op"] == "replace":
                if op["path"] == "/tracingEnabled":
                    self["tracingEnabled"] = self._str2bool(op["value"])
                elif op["path"].startswith("/accessLogSettings/"):
                    self["accessLogSettings"] = self.get("accessLogSettings", {})
                    self["accessLogSettings"][op["path"].split("/")[-1]] = op["value"]
                else:
                    # (e.g., path could be '/*/*/logging/loglevel')
                    split_path = op["path"].split("/", 3)
                    if len(split_path) != 4:
                        continue
                    self._patch_method_setting(
                        "/".join(split_path[1:3]), split_path[3], op["value"]
                    )
            elif op["op"] == "remove":
                if op["path"] == "/accessLogSettings":
                    self["accessLogSettings"] = None
            else:
                raise ValidationException(
                    "Member must satisfy enum value set: [add, remove, move, test, replace, copy]"
                )
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

        return mappings.get(key)

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
        generateDistinctId=False,  # pylint: disable=unused-argument
        value=None,
        stageKeys=None,
        tags=None,
        customerId=None,
    ):
        super().__init__()
        self["id"] = create_id()
        self["value"] = value or "".join(
            random.sample(string.ascii_letters + string.digits, 40)
        )
        self["name"] = name
        self["customerId"] = customerId
        self["description"] = description
        self["enabled"] = enabled
        self["createdDate"] = self["lastUpdatedDate"] = int(time.time())
        self["stageKeys"] = stageKeys or []
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
        super().__init__()
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


class RequestValidator(BaseModel, dict):
    PROP_ID = "id"
    PROP_NAME = "name"
    PROP_VALIDATE_REQUEST_BODY = "validateRequestBody"
    PROP_VALIDATE_REQUEST_PARAMETERS = "validateRequestParameters"

    # operations
    OP_PATH = "path"
    OP_VALUE = "value"
    OP_REPLACE = "replace"
    OP_OP = "op"

    def __init__(self, _id, name, validateRequestBody, validateRequestParameters):
        super().__init__()
        self[RequestValidator.PROP_ID] = _id
        self[RequestValidator.PROP_NAME] = name
        self[RequestValidator.PROP_VALIDATE_REQUEST_BODY] = validateRequestBody
        self[
            RequestValidator.PROP_VALIDATE_REQUEST_PARAMETERS
        ] = validateRequestParameters

    def apply_patch_operations(self, operations):
        for operation in operations:
            path = operation[RequestValidator.OP_PATH]
            value = operation[RequestValidator.OP_VALUE]
            if operation[RequestValidator.OP_OP] == RequestValidator.OP_REPLACE:
                if to_path(RequestValidator.PROP_NAME) in path:
                    self[RequestValidator.PROP_NAME] = value
                if to_path(RequestValidator.PROP_VALIDATE_REQUEST_BODY) in path:
                    self[
                        RequestValidator.PROP_VALIDATE_REQUEST_BODY
                    ] = value.lower() in ("true")
                if to_path(RequestValidator.PROP_VALIDATE_REQUEST_PARAMETERS) in path:
                    self[
                        RequestValidator.PROP_VALIDATE_REQUEST_PARAMETERS
                    ] = value.lower() in ("true")

    def to_dict(self):
        return {
            "id": self["id"],
            "name": self["name"],
            "validateRequestBody": self["validateRequestBody"],
            "validateRequestParameters": self["validateRequestParameters"],
        }


class UsagePlanKey(BaseModel, dict):
    def __init__(self, plan_id, plan_type, name, value):
        super().__init__()
        self["id"] = plan_id
        self["name"] = name
        self["type"] = plan_type
        self["value"] = value


class VpcLink(BaseModel, dict):
    def __init__(self, name, description, target_arns, tags):
        super().__init__()
        self["id"] = create_id()
        self["name"] = name
        self["description"] = description
        self["targetArns"] = target_arns
        self["tags"] = tags
        self["status"] = "AVAILABLE"


class RestAPI(CloudFormationModel):

    PROP_ID = "id"
    PROP_NAME = "name"
    PROP_DESCRIPTION = "description"
    PROP_VERSION = "version"
    PROP_BINARY_MEDIA_TYPES = "binaryMediaTypes"
    PROP_CREATED_DATE = "createdDate"
    PROP_API_KEY_SOURCE = "apiKeySource"
    PROP_ENDPOINT_CONFIGURATION = "endpointConfiguration"
    PROP_TAGS = "tags"
    PROP_POLICY = "policy"
    PROP_DISABLE_EXECUTE_API_ENDPOINT = "disableExecuteApiEndpoint"
    PROP_MINIMUM_COMPRESSION_SIZE = "minimumCompressionSize"

    # operations
    OPERATION_ADD = "add"
    OPERATION_REPLACE = "replace"
    OPERATION_REMOVE = "remove"
    OPERATION_PATH = "path"
    OPERATION_VALUE = "value"
    OPERATION_OP = "op"

    def __init__(self, api_id, region_name, name, description, **kwargs):
        super().__init__()
        self.id = api_id
        self.region_name = region_name
        self.name = name
        self.description = description
        self.version = kwargs.get(RestAPI.PROP_VERSION) or "V1"
        self.binaryMediaTypes = kwargs.get(RestAPI.PROP_BINARY_MEDIA_TYPES) or []
        self.create_date = int(time.time())
        self.api_key_source = kwargs.get("api_key_source") or "HEADER"
        self.policy = kwargs.get(RestAPI.PROP_POLICY) or None
        self.endpoint_configuration = kwargs.get("endpoint_configuration") or {
            "types": ["EDGE"]
        }
        self.tags = kwargs.get(RestAPI.PROP_TAGS) or {}
        self.disableExecuteApiEndpoint = (
            kwargs.get(RestAPI.PROP_DISABLE_EXECUTE_API_ENDPOINT) or False
        )
        self.minimum_compression_size = kwargs.get("minimum_compression_size")
        self.deployments = {}
        self.authorizers = {}
        self.gateway_responses = {}
        self.stages = {}
        self.resources = {}
        self.models = {}
        self.request_validators = {}
        self.default = self.add_child("/")  # Add default child

    def __repr__(self):
        return str(self.id)

    def to_dict(self):
        return {
            self.PROP_ID: self.id,
            self.PROP_NAME: self.name,
            self.PROP_DESCRIPTION: self.description,
            self.PROP_VERSION: self.version,
            self.PROP_BINARY_MEDIA_TYPES: self.binaryMediaTypes,
            self.PROP_CREATED_DATE: self.create_date,
            self.PROP_API_KEY_SOURCE: self.api_key_source,
            self.PROP_ENDPOINT_CONFIGURATION: self.endpoint_configuration,
            self.PROP_TAGS: self.tags,
            self.PROP_POLICY: self.policy,
            self.PROP_DISABLE_EXECUTE_API_ENDPOINT: self.disableExecuteApiEndpoint,
            self.PROP_MINIMUM_COMPRESSION_SIZE: self.minimum_compression_size,
        }

    def apply_patch_operations(self, patch_operations):

        for op in patch_operations:
            path = op[self.OPERATION_PATH]
            value = ""
            if self.OPERATION_VALUE in op:
                value = op[self.OPERATION_VALUE]
            operaton = op[self.OPERATION_OP]
            if operaton == self.OPERATION_REPLACE:
                if to_path(self.PROP_NAME) in path:
                    self.name = value
                if to_path(self.PROP_DESCRIPTION) in path:
                    self.description = value
                if to_path(self.PROP_API_KEY_SOURCE) in path:
                    self.api_key_source = value
                if to_path(self.PROP_BINARY_MEDIA_TYPES) in path:
                    self.binaryMediaTypes = [value]
                if to_path(self.PROP_DISABLE_EXECUTE_API_ENDPOINT) in path:
                    self.disableExecuteApiEndpoint = bool(value)
            elif operaton == self.OPERATION_ADD:
                if to_path(self.PROP_BINARY_MEDIA_TYPES) in path:
                    self.binaryMediaTypes.append(value)
            elif operaton == self.OPERATION_REMOVE:
                if to_path(self.PROP_BINARY_MEDIA_TYPES) in path:
                    self.binaryMediaTypes.remove(value)
                if to_path(self.PROP_DESCRIPTION) in path:
                    self.description = ""

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["RootResourceId"]

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
        cls, resource_name, cloudformation_json, region_name, **kwargs
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
            resource_id=child_id,
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
            model_id=model_id,
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
        path_after_stage_name = "/" + "/".join(path.split("/")[2:])

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

        for resource in self.resources.values():
            path = resource.get_path()
            path = "" if path == "/" else path

            for http_method in resource.resource_methods.keys():
                for url in [stage_url_lower, stage_url_upper]:
                    callback_response = responses.CallbackResponse(
                        url=url + path,
                        method=http_method,
                        callback=self.resource_callback,
                        content_type="text/plain",
                    )
                    responses_mock.add(callback_response)

    def create_authorizer(
        self,
        authorizer_id,
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
            authorizer_id=authorizer_id,
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
        self.authorizers[authorizer_id] = authorizer
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
        if name in self.stages:
            raise ConflictException("Stage already exists")
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
        if name:
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
        if deployment_id not in self.deployments:
            raise DeploymentNotFoundException()
        deployment = self.deployments[deployment_id]
        if deployment["stageName"] and deployment["stageName"] in self.stages:
            # Stage is still active
            raise StageStillActive()

        return self.deployments.pop(deployment_id)

    def create_request_validator(
        self, name, validateRequestBody, validateRequestParameters
    ):
        validator_id = create_id()
        request_validator = RequestValidator(
            _id=validator_id,
            name=name,
            validateRequestBody=validateRequestBody,
            validateRequestParameters=validateRequestParameters,
        )
        self.request_validators[validator_id] = request_validator
        return request_validator

    def get_request_validators(self):
        return list(self.request_validators.values())

    def get_request_validator(self, validator_id):
        reqeust_validator = self.request_validators.get(validator_id)
        if reqeust_validator is None:
            raise RequestValidatorNotFound()
        return reqeust_validator

    def delete_request_validator(self, validator_id):
        reqeust_validator = self.request_validators.pop(validator_id)
        return reqeust_validator

    def update_request_validator(self, validator_id, patch_operations):
        self.request_validators[validator_id].apply_patch_operations(patch_operations)
        return self.request_validators[validator_id]

    def put_gateway_response(
        self, response_type, status_code, response_parameters, response_templates
    ):
        response = GatewayResponse(
            response_type=response_type,
            status_code=status_code,
            response_parameters=response_parameters,
            response_templates=response_templates,
        )
        self.gateway_responses[response_type] = response
        return response

    def get_gateway_response(self, response_type):
        if response_type not in self.gateway_responses:
            raise GatewayResponseNotFound()
        return self.gateway_responses[response_type]

    def get_gateway_responses(self):
        return list(self.gateway_responses.values())

    def delete_gateway_response(self, response_type):
        self.gateway_responses.pop(response_type, None)


class DomainName(BaseModel, dict):
    def __init__(self, domain_name, **kwargs):
        super().__init__()
        self["domainName"] = domain_name
        self["regionalDomainName"] = "d-%s.execute-api.%s.amazonaws.com" % (
            create_id(),
            kwargs.get("region_name") or "us-east-1",
        )
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
    def __init__(self, model_id, name, **kwargs):
        super().__init__()
        self["id"] = model_id
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


class BasePathMapping(BaseModel, dict):

    # operations
    OPERATION_REPLACE = "replace"
    OPERATION_PATH = "path"
    OPERATION_VALUE = "value"
    OPERATION_OP = "op"

    def __init__(self, domain_name, rest_api_id, **kwargs):
        super().__init__()
        self["domain_name"] = domain_name
        self["restApiId"] = rest_api_id
        if kwargs.get("basePath"):
            self["basePath"] = kwargs.get("basePath")
        else:
            self["basePath"] = "(none)"
        if kwargs.get("stage"):
            self["stage"] = kwargs.get("stage")

    def apply_patch_operations(self, patch_operations):

        for op in patch_operations:
            path = op["path"]
            value = op["value"]
            operation = op["op"]
            if operation == self.OPERATION_REPLACE:
                if "/basePath" in path:
                    self["basePath"] = value
                if "/restapiId" in path:
                    self["restApiId"] = value
                if "/stage" in path:
                    self["stage"] = value


class GatewayResponse(BaseModel, dict):
    def __init__(
        self, response_type, status_code, response_parameters, response_templates
    ):
        super().__init__()
        self["responseType"] = response_type
        if status_code is not None:
            self["statusCode"] = status_code
        if response_parameters is not None:
            self["responseParameters"] = response_parameters
        if response_templates is not None:
            self["responseTemplates"] = response_templates
        self["defaultResponse"] = False


class APIGatewayBackend(BaseBackend):
    """
    API Gateway mock.

    The public URLs of an API integration are mocked as well, i.e. the following would be supported in Moto:

    .. sourcecode:: python

        client.put_integration(
            restApiId=api_id,
            ...,
            uri="http://httpbin.org/robots.txt",
            integrationHttpMethod="GET"
        )
        deploy_url = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/dev"
        requests.get(deploy_url).content.should.equal(b"a fake response")

    Limitations:
     - Integrations of type HTTP are supported
     - Integrations of type AWS with service DynamoDB are supported
     - Other types (AWS_PROXY, MOCK, etc) are ignored
     - Other services are not yet supported
     - The BasePath of an API is ignored
     - TemplateMapping is not yet supported for requests/responses
     - This only works when using the decorators, not in ServerMode
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.apis = {}
        self.keys = {}
        self.usage_plans = {}
        self.usage_plan_keys = {}
        self.domain_names = {}
        self.models = {}
        self.base_path_mappings = {}
        self.vpc_links = {}

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

    def import_rest_api(self, api_doc, fail_on_warnings):
        """
        Only a subset of the OpenAPI spec 3.x is currently implemented.
        """
        if fail_on_warnings:
            try:
                validate_spec(api_doc)
            except OpenAPIValidationError as e:
                raise InvalidOpenAPIDocumentException(e)
        name = api_doc["info"]["title"]
        description = api_doc["info"]["description"]
        api = self.create_rest_api(name=name, description=description)
        self.put_rest_api(api.id, api_doc, fail_on_warnings=fail_on_warnings)
        return api

    def get_rest_api(self, function_id):
        rest_api = self.apis.get(function_id)
        if rest_api is None:
            raise RestAPINotFound()
        return rest_api

    def put_rest_api(self, function_id, api_doc, mode="merge", fail_on_warnings=False):
        """
        Only a subset of the OpenAPI spec 3.x is currently implemented.
        """
        if mode not in ["merge", "overwrite"]:
            raise InvalidOpenApiModeException()

        if api_doc.get("swagger") is not None or (
            api_doc.get("openapi") is not None and api_doc["openapi"][0] != "3"
        ):
            raise InvalidOpenApiDocVersionException()

        if fail_on_warnings:
            try:
                validate_spec(api_doc)
            except OpenAPIValidationError as e:
                raise InvalidOpenAPIDocumentException(e)

        if mode == "overwrite":
            api = self.get_rest_api(function_id)
            api.resources = {}
            api.default = api.add_child("/")  # Add default child

        for (path, resource_doc) in sorted(
            api_doc["paths"].items(), key=lambda x: x[0]
        ):
            parent_path_part = path[0 : path.rfind("/")] or "/"
            parent_resource_id = (
                self.apis[function_id].get_resource_for_path(parent_path_part).id
            )
            resource = self.create_resource(
                function_id=function_id,
                parent_resource_id=parent_resource_id,
                path_part=path[path.rfind("/") + 1 :],
            )

            for (method_type, method_doc) in resource_doc.items():
                method_type = method_type.upper()
                if method_doc.get("x-amazon-apigateway-integration") is None:
                    self.put_method(function_id, resource.id, method_type, None)
                    method_responses = method_doc.get("responses", {}).items()
                    for (response_code, _) in method_responses:
                        self.put_method_response(
                            function_id,
                            resource.id,
                            method_type,
                            response_code,
                            response_models=None,
                            response_parameters=None,
                        )

        return self.get_rest_api(function_id)

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

    def get_resources(self, function_id):
        api = self.get_rest_api(function_id)
        return api.resources.values()

    def get_resource(self, function_id, resource_id):
        api = self.get_rest_api(function_id)
        if resource_id not in api.resources:
            raise ResourceIdNotFoundException
        resource = api.resources[resource_id]
        return resource

    def create_resource(self, function_id, parent_resource_id, path_part):
        api = self.get_rest_api(function_id)
        if not path_part:
            # We're attempting to create the default resource, which already exists.
            return api.default
        if not re.match("^\\{?[a-zA-Z0-9._-]+\\+?\\}?$", path_part):
            raise InvalidResourcePathException()
        child = api.add_child(path=path_part, parent_id=parent_resource_id)
        return child

    def delete_resource(self, function_id, resource_id):
        api = self.get_rest_api(function_id)
        resource = api.resources.pop(resource_id)
        return resource

    def get_method(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.get_method(method_type)

    def put_method(
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

    def delete_method(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        resource.delete_method(method_type)

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

    def put_method_response(
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

    def put_integration(
        self,
        function_id,
        resource_id,
        method_type,
        integration_type,
        uri,
        integration_method=None,
        credentials=None,
        request_templates=None,
        passthrough_behavior=None,
        tls_config=None,
        cache_namespace=None,
        timeout_in_millis=None,
    ):
        resource = self.get_resource(function_id, resource_id)
        if credentials and not re.match(
            "^arn:aws:iam::" + str(get_account_id()), credentials
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
            passthrough_behavior=passthrough_behavior,
            tls_config=tls_config,
            cache_namespace=cache_namespace,
            timeout_in_millis=timeout_in_millis,
        )
        return integration

    def get_integration(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.get_integration(method_type)

    def delete_integration(self, function_id, resource_id, method_type):
        resource = self.get_resource(function_id, resource_id)
        return resource.delete_integration(method_type)

    def put_integration_response(
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
            for res in self.get_resources(function_id)
        ]
        methods = [m for sublist in methods for m in sublist]
        if not any(methods):
            raise NoMethodDefined()
        method_integrations = [
            method.get("methodIntegration", None) for method in methods
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
            plan_id=key_id,
            plan_type=payload["keyType"],
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

    def get_request_validators(self, restapi_id):
        restApi = self.get_rest_api(restapi_id)
        return restApi.get_request_validators()

    def create_request_validator(self, restapi_id, name, body, params):
        restApi = self.get_rest_api(restapi_id)
        return restApi.create_request_validator(
            name=name, validateRequestBody=body, validateRequestParameters=params
        )

    def get_request_validator(self, restapi_id, validator_id):
        restApi = self.get_rest_api(restapi_id)
        return restApi.get_request_validator(validator_id)

    def delete_request_validator(self, restapi_id, validator_id):
        restApi = self.get_rest_api(restapi_id)
        restApi.delete_request_validator(validator_id)

    def update_request_validator(self, restapi_id, validator_id, patch_operations):
        restApi = self.get_rest_api(restapi_id)
        return restApi.update_request_validator(validator_id, patch_operations)

    def create_base_path_mapping(
        self, domain_name, rest_api_id, base_path=None, stage=None
    ):
        if domain_name not in self.domain_names:
            raise DomainNameNotFound()

        if base_path and "/" in base_path:
            raise InvalidBasePathException()

        if rest_api_id not in self.apis:
            raise InvalidRestApiIdForBasePathMappingException()

        if stage and self.apis[rest_api_id].stages.get(stage) is None:
            raise InvalidStageException()

        new_base_path_mapping = BasePathMapping(
            domain_name=domain_name,
            rest_api_id=rest_api_id,
            basePath=base_path,
            stage=stage,
        )

        new_base_path = new_base_path_mapping.get("basePath")
        if self.base_path_mappings.get(domain_name) is None:
            self.base_path_mappings[domain_name] = {}
        else:
            if (
                self.base_path_mappings[domain_name].get(new_base_path)
                and new_base_path != "(none)"
            ):
                raise BasePathConflictException()
        self.base_path_mappings[domain_name][new_base_path] = new_base_path_mapping
        return new_base_path_mapping

    def get_base_path_mappings(self, domain_name):

        if domain_name not in self.domain_names:
            raise DomainNameNotFound()

        return list(self.base_path_mappings[domain_name].values())

    def get_base_path_mapping(self, domain_name, base_path):

        if domain_name not in self.domain_names:
            raise DomainNameNotFound()

        if base_path not in self.base_path_mappings[domain_name]:
            raise BasePathNotFoundException()

        return self.base_path_mappings[domain_name][base_path]

    def delete_base_path_mapping(self, domain_name, base_path):

        if domain_name not in self.domain_names:
            raise DomainNameNotFound()

        if base_path not in self.base_path_mappings[domain_name]:
            raise BasePathNotFoundException()

        self.base_path_mappings[domain_name].pop(base_path)

    def update_base_path_mapping(self, domain_name, base_path, patch_operations):

        if domain_name not in self.domain_names:
            raise DomainNameNotFound()

        if base_path not in self.base_path_mappings[domain_name]:
            raise BasePathNotFoundException()

        base_path_mapping = self.get_base_path_mapping(domain_name, base_path)

        rest_api_ids = [
            op["value"] for op in patch_operations if op["path"] == "/restapiId"
        ]
        if len(rest_api_ids) == 0:
            modified_rest_api_id = base_path_mapping["restApiId"]
        else:
            modified_rest_api_id = rest_api_ids[-1]

        stages = [op["value"] for op in patch_operations if op["path"] == "/stage"]
        if len(stages) == 0:
            modified_stage = base_path_mapping.get("stage")
        else:
            modified_stage = stages[-1]

        base_paths = [
            op["value"] for op in patch_operations if op["path"] == "/basePath"
        ]
        if len(base_paths) == 0:
            modified_base_path = base_path_mapping["basePath"]
        else:
            modified_base_path = base_paths[-1]

        rest_api = self.apis.get(modified_rest_api_id)
        if rest_api is None:
            raise InvalidRestApiIdForBasePathMappingException()
        if modified_stage and rest_api.stages.get(modified_stage) is None:
            raise InvalidStageException()

        base_path_mapping.apply_patch_operations(patch_operations)

        if base_path != modified_base_path:
            self.base_path_mappings[domain_name].pop(base_path)
            self.base_path_mappings[domain_name][modified_base_path] = base_path_mapping

        return base_path_mapping

    def create_vpc_link(self, name, description, target_arns, tags):
        vpc_link = VpcLink(
            name, description=description, target_arns=target_arns, tags=tags
        )
        self.vpc_links[vpc_link["id"]] = vpc_link
        return vpc_link

    def delete_vpc_link(self, vpc_link_id):
        self.vpc_links.pop(vpc_link_id, None)

    def get_vpc_link(self, vpc_link_id):
        if vpc_link_id not in self.vpc_links:
            raise VpcLinkNotFound
        return self.vpc_links[vpc_link_id]

    def get_vpc_links(self):
        """
        Pagination has not yet been implemented
        """
        return list(self.vpc_links.values())

    def put_gateway_response(
        self,
        rest_api_id,
        response_type,
        status_code,
        response_parameters,
        response_templates,
    ):
        api = self.get_rest_api(rest_api_id)
        response = api.put_gateway_response(
            response_type,
            status_code=status_code,
            response_parameters=response_parameters,
            response_templates=response_templates,
        )
        return response

    def get_gateway_response(self, rest_api_id, response_type):
        api = self.get_rest_api(rest_api_id)
        return api.get_gateway_response(response_type)

    def get_gateway_responses(self, rest_api_id):
        """
        Pagination is not yet implemented
        """
        api = self.get_rest_api(rest_api_id)
        return api.get_gateway_responses()

    def delete_gateway_response(self, rest_api_id, response_type):
        api = self.get_rest_api(rest_api_id)
        api.delete_gateway_response(response_type)


apigateway_backends = BackendDict(APIGatewayBackend, "apigateway")
