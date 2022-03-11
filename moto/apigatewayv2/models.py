"""ApiGatewayV2Backend class with methods for supported APIs."""
import random
import string
import yaml

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time
from moto.utilities.tagging_service import TaggingService

from .exceptions import (
    ApiNotFound,
    AuthorizerNotFound,
    BadRequestException,
    ModelNotFound,
    RouteResponseNotFound,
    IntegrationNotFound,
    IntegrationResponseNotFound,
    RouteNotFound,
    VpcLinkNotFound,
)


class Authorizer(BaseModel):
    def __init__(
        self,
        auth_creds_arn,
        auth_payload_format_version,
        auth_result_ttl,
        authorizer_type,
        authorizer_uri,
        enable_simple_response,
        identity_source,
        identity_validation_expr,
        jwt_config,
        name,
    ):
        self.id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.auth_creds_arn = auth_creds_arn
        self.auth_payload_format_version = auth_payload_format_version
        self.auth_result_ttl = auth_result_ttl
        self.authorizer_type = authorizer_type
        self.authorizer_uri = authorizer_uri
        self.enable_simple_response = enable_simple_response
        self.identity_source = identity_source
        self.identity_validation_expr = identity_validation_expr
        self.jwt_config = jwt_config
        self.name = name

    def update(
        self,
        auth_creds_arn,
        auth_payload_format_version,
        auth_result_ttl,
        authorizer_type,
        authorizer_uri,
        enable_simple_response,
        identity_source,
        identity_validation_expr,
        jwt_config,
        name,
    ):
        if auth_creds_arn is not None:
            self.auth_creds_arn = auth_creds_arn
        if auth_payload_format_version is not None:
            self.auth_payload_format_version = auth_payload_format_version
        if auth_result_ttl is not None:
            self.auth_result_ttl = auth_result_ttl
        if authorizer_type is not None:
            self.authorizer_type is authorizer_type
        if authorizer_uri is not None:
            self.authorizer_uri = authorizer_uri
        if enable_simple_response is not None:
            self.enable_simple_response = enable_simple_response
        if identity_source is not None:
            self.identity_source = identity_source
        if identity_validation_expr is not None:
            self.identity_validation_expr = identity_validation_expr
        if jwt_config is not None:
            self.jwt_config = jwt_config
        if name is not None:
            self.name = name

    def to_json(self):
        return {
            "authorizerId": self.id,
            "authorizerCredentialsArn": self.auth_creds_arn,
            "authorizerPayloadFormatVersion": self.auth_payload_format_version,
            "authorizerResultTtlInSeconds": self.auth_result_ttl,
            "authorizerType": self.authorizer_type,
            "authorizerUri": self.authorizer_uri,
            "enableSimpleResponses": self.enable_simple_response,
            "identitySource": self.identity_source,
            "identityValidationExpression": self.identity_validation_expr,
            "jwtConfiguration": self.jwt_config,
            "name": self.name,
        }


class Integration(BaseModel):
    def __init__(
        self,
        connection_id,
        connection_type,
        content_handling_strategy,
        credentials_arn,
        description,
        integration_method,
        integration_type,
        integration_uri,
        passthrough_behavior,
        payload_format_version,
        integration_subtype,
        request_parameters,
        request_templates,
        response_parameters,
        template_selection_expression,
        timeout_in_millis,
        tls_config,
    ):
        self.id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.connection_id = connection_id
        self.connection_type = connection_type
        self.content_handling_strategy = content_handling_strategy
        self.credentials_arn = credentials_arn
        self.description = description
        self.integration_method = integration_method
        self.integration_response_selection_expression = None
        self.integration_type = integration_type
        self.integration_subtype = integration_subtype
        self.integration_uri = integration_uri
        self.passthrough_behavior = passthrough_behavior
        self.payload_format_version = payload_format_version
        self.request_parameters = request_parameters
        self.request_templates = request_templates
        self.response_parameters = response_parameters
        self.template_selection_expression = template_selection_expression
        self.timeout_in_millis = timeout_in_millis
        self.tls_config = tls_config

        if self.integration_type in ["MOCK", "HTTP"]:
            self.integration_response_selection_expression = (
                "${integration.response.statuscode}"
            )
        elif self.integration_type in ["AWS"]:
            self.integration_response_selection_expression = (
                "${integration.response.body.errorMessage}"
            )
        if (
            self.integration_type in ["AWS", "MOCK", "HTTP"]
            and self.passthrough_behavior is None
        ):
            self.passthrough_behavior = "WHEN_NO_MATCH"
        if self.integration_uri is not None and self.integration_method is None:
            self.integration_method = "POST"
        if self.integration_type in ["AWS", "MOCK"]:
            self.timeout_in_millis = self.timeout_in_millis or 29000
        else:
            self.timeout_in_millis = self.timeout_in_millis or 30000

        self.responses = dict()

    def create_response(
        self,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        response = IntegrationResponse(
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )
        self.responses[response.id] = response
        return response

    def delete_response(self, integration_response_id):
        self.responses.pop(integration_response_id)

    def get_response(self, integration_response_id):
        if integration_response_id not in self.responses:
            raise IntegrationResponseNotFound(integration_response_id)
        return self.responses[integration_response_id]

    def get_responses(self):
        return self.responses.values()

    def update_response(
        self,
        integration_response_id,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        int_response = self.responses[integration_response_id]
        int_response.update(
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )
        return int_response

    def update(
        self,
        connection_id,
        connection_type,
        content_handling_strategy,
        credentials_arn,
        description,
        integration_method,
        integration_type,
        integration_uri,
        passthrough_behavior,
        payload_format_version,
        integration_subtype,
        request_parameters,
        request_templates,
        response_parameters,
        template_selection_expression,
        timeout_in_millis,
        tls_config,
    ):
        if connection_id is not None:
            self.connection_id = connection_id
        if connection_type is not None:
            self.connection_type = connection_type
        if content_handling_strategy is not None:
            self.content_handling_strategy = content_handling_strategy
        if credentials_arn is not None:
            self.credentials_arn = credentials_arn
        if description is not None:
            self.description = description
        if integration_method is not None:
            self.integration_method = integration_method
        if integration_type is not None:
            self.integration_type = integration_type
        if integration_uri is not None:
            self.integration_uri = integration_uri
        if passthrough_behavior is not None:
            self.passthrough_behavior = passthrough_behavior
        if payload_format_version is not None:
            self.payload_format_version = payload_format_version
        if integration_subtype is not None:
            self.integration_subtype = integration_subtype
        if request_parameters is not None:
            # Skip parameters with an empty value
            req_params = {
                key: value for (key, value) in request_parameters.items() if value
            }
            self.request_parameters = req_params
        if request_templates is not None:
            self.request_templates = request_templates
        if response_parameters is not None:
            self.response_parameters = response_parameters
        if template_selection_expression is not None:
            self.template_selection_expression = template_selection_expression
        if timeout_in_millis is not None:
            self.timeout_in_millis = timeout_in_millis
        if tls_config is not None:
            self.tls_config = tls_config

    def to_json(self):
        return {
            "connectionId": self.connection_id,
            "connectionType": self.connection_type,
            "contentHandlingStrategy": self.content_handling_strategy,
            "credentialsArn": self.credentials_arn,
            "description": self.description,
            "integrationId": self.id,
            "integrationMethod": self.integration_method,
            "integrationResponseSelectionExpression": self.integration_response_selection_expression,
            "integrationType": self.integration_type,
            "integrationSubtype": self.integration_subtype,
            "integrationUri": self.integration_uri,
            "passthroughBehavior": self.passthrough_behavior,
            "payloadFormatVersion": self.payload_format_version,
            "requestParameters": self.request_parameters,
            "requestTemplates": self.request_templates,
            "responseParameters": self.response_parameters,
            "templateSelectionExpression": self.template_selection_expression,
            "timeoutInMillis": self.timeout_in_millis,
            "tlsConfig": self.tls_config,
        }


class IntegrationResponse(BaseModel):
    def __init__(
        self,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        self.id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.content_handling_strategy = content_handling_strategy
        self.integration_response_key = integration_response_key
        self.response_parameters = response_parameters
        self.response_templates = response_templates
        self.template_selection_expression = template_selection_expression

    def update(
        self,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        if content_handling_strategy is not None:
            self.content_handling_strategy = content_handling_strategy
        if integration_response_key is not None:
            self.integration_response_key = integration_response_key
        if response_parameters is not None:
            self.response_parameters = response_parameters
        if response_templates is not None:
            self.response_templates = response_templates
        if template_selection_expression is not None:
            self.template_selection_expression = template_selection_expression

    def to_json(self):
        return {
            "integrationResponseId": self.id,
            "integrationResponseKey": self.integration_response_key,
            "contentHandlingStrategy": self.content_handling_strategy,
            "responseParameters": self.response_parameters,
            "responseTemplates": self.response_templates,
            "templateSelectionExpression": self.template_selection_expression,
        }


class Model(BaseModel):
    def __init__(self, content_type, description, name, schema):
        self.id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.content_type = content_type
        self.description = description
        self.name = name
        self.schema = schema

    def update(self, content_type, description, name, schema):
        if content_type is not None:
            self.content_type = content_type
        if description is not None:
            self.description = description
        if name is not None:
            self.name = name
        if schema is not None:
            self.schema = schema

    def to_json(self):
        return {
            "modelId": self.id,
            "contentType": self.content_type,
            "description": self.description,
            "name": self.name,
            "schema": self.schema,
        }


class RouteResponse(BaseModel):
    def __init__(self, route_response_key, model_selection_expression, response_models):
        self.id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.route_response_key = route_response_key
        self.model_selection_expression = model_selection_expression
        self.response_models = response_models

    def to_json(self):
        return {
            "modelSelectionExpression": self.model_selection_expression,
            "responseModels": self.response_models,
            "routeResponseId": self.id,
            "routeResponseKey": self.route_response_key,
        }


class Route(BaseModel):
    def __init__(
        self,
        api_key_required,
        authorization_scopes,
        authorization_type,
        authorizer_id,
        model_selection_expression,
        operation_name,
        request_models,
        request_parameters,
        route_key,
        route_response_selection_expression,
        target,
    ):
        self.route_id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.api_key_required = api_key_required
        self.authorization_scopes = authorization_scopes
        self.authorization_type = authorization_type
        self.authorizer_id = authorizer_id
        self.model_selection_expression = model_selection_expression
        self.operation_name = operation_name
        self.request_models = request_models
        self.request_parameters = request_parameters or {}
        self.route_key = route_key
        self.route_response_selection_expression = route_response_selection_expression
        self.target = target

        self.route_responses = dict()

    def create_route_response(
        self, route_response_key, model_selection_expression, response_models
    ):
        route_response = RouteResponse(
            route_response_key,
            model_selection_expression=model_selection_expression,
            response_models=response_models,
        )
        self.route_responses[route_response.id] = route_response
        return route_response

    def get_route_response(self, route_response_id):
        if route_response_id not in self.route_responses:
            raise RouteResponseNotFound(route_response_id)
        return self.route_responses[route_response_id]

    def delete_route_response(self, route_response_id):
        self.route_responses.pop(route_response_id, None)

    def delete_route_request_parameter(self, request_param):
        del self.request_parameters[request_param]

    def update(
        self,
        api_key_required,
        authorization_scopes,
        authorization_type,
        authorizer_id,
        model_selection_expression,
        operation_name,
        request_models,
        request_parameters,
        route_key,
        route_response_selection_expression,
        target,
    ):
        if api_key_required is not None:
            self.api_key_required = api_key_required
        if authorization_scopes:
            self.authorization_scopes = authorization_scopes
        if authorization_type:
            self.authorization_type = authorization_type
        if authorizer_id is not None:
            self.authorizer_id = authorizer_id
        if model_selection_expression:
            self.model_selection_expression = model_selection_expression
        if operation_name is not None:
            self.operation_name = operation_name
        if request_models:
            self.request_models = request_models
        if request_parameters:
            self.request_parameters = request_parameters
        if route_key:
            self.route_key = route_key
        if route_response_selection_expression is not None:
            self.route_response_selection_expression = (
                route_response_selection_expression
            )
        if target:
            self.target = target

    def to_json(self):
        return {
            "apiKeyRequired": self.api_key_required,
            "authorizationScopes": self.authorization_scopes,
            "authorizationType": self.authorization_type,
            "authorizerId": self.authorizer_id,
            "modelSelectionExpression": self.model_selection_expression,
            "operationName": self.operation_name,
            "requestModels": self.request_models,
            "requestParameters": self.request_parameters,
            "routeId": self.route_id,
            "routeKey": self.route_key,
            "routeResponseSelectionExpression": self.route_response_selection_expression,
            "target": self.target,
        }


class Api(BaseModel):
    def __init__(
        self,
        region,
        name,
        api_key_selection_expression,
        cors_configuration,
        description,
        disable_execute_api_endpoint,
        disable_schema_validation,
        protocol_type,
        route_selection_expression,
        tags,
        version,
        backend,
    ):
        self.api_id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.api_endpoint = f"https://{self.api_id}.execute-api.{region}.amazonaws.com"
        self.backend = backend
        self.name = name
        self.api_key_selection_expression = (
            api_key_selection_expression or "$request.header.x-api-key"
        )
        self.created_date = unix_time()
        self.cors_configuration = cors_configuration
        self.description = description
        self.disable_execute_api_endpoint = disable_execute_api_endpoint or False
        self.disable_schema_validation = disable_schema_validation
        self.protocol_type = protocol_type
        self.route_selection_expression = (
            route_selection_expression or "$request.method $request.path"
        )
        self.version = version

        self.authorizers = dict()
        self.integrations = dict()
        self.models = dict()
        self.routes = dict()

        self.arn = f"arn:aws:apigateway:{region}::/apis/{self.api_id}"
        self.backend.tag_resource(self.arn, tags)

    def clear(self):
        self.authorizers = dict()
        self.integrations = dict()
        self.models = dict()
        self.routes = dict()

    def delete_cors_configuration(self):
        self.cors_configuration = None

    def create_authorizer(
        self,
        auth_creds_arn,
        auth_payload_format_version,
        auth_result_ttl,
        authorizer_type,
        authorizer_uri,
        enable_simple_response,
        identity_source,
        identity_validation_expr,
        jwt_config,
        name,
    ):
        authorizer = Authorizer(
            auth_creds_arn=auth_creds_arn,
            auth_payload_format_version=auth_payload_format_version,
            auth_result_ttl=auth_result_ttl,
            authorizer_type=authorizer_type,
            authorizer_uri=authorizer_uri,
            enable_simple_response=enable_simple_response,
            identity_source=identity_source,
            identity_validation_expr=identity_validation_expr,
            jwt_config=jwt_config,
            name=name,
        )
        self.authorizers[authorizer.id] = authorizer
        return authorizer

    def delete_authorizer(self, authorizer_id):
        self.authorizers.pop(authorizer_id, None)

    def get_authorizer(self, authorizer_id):
        if authorizer_id not in self.authorizers:
            raise AuthorizerNotFound(authorizer_id)
        return self.authorizers[authorizer_id]

    def update_authorizer(
        self,
        authorizer_id,
        auth_creds_arn,
        auth_payload_format_version,
        auth_result_ttl,
        authorizer_type,
        authorizer_uri,
        enable_simple_response,
        identity_source,
        identity_validation_expr,
        jwt_config,
        name,
    ):
        authorizer = self.authorizers[authorizer_id]
        authorizer.update(
            auth_creds_arn=auth_creds_arn,
            auth_payload_format_version=auth_payload_format_version,
            auth_result_ttl=auth_result_ttl,
            authorizer_type=authorizer_type,
            authorizer_uri=authorizer_uri,
            enable_simple_response=enable_simple_response,
            identity_source=identity_source,
            identity_validation_expr=identity_validation_expr,
            jwt_config=jwt_config,
            name=name,
        )
        return authorizer

    def create_model(self, content_type, description, name, schema):
        model = Model(content_type, description, name, schema)
        self.models[model.id] = model
        return model

    def delete_model(self, model_id):
        self.models.pop(model_id, None)

    def get_model(self, model_id):
        if model_id not in self.models:
            raise ModelNotFound(model_id)
        return self.models[model_id]

    def update_model(self, model_id, content_type, description, name, schema):
        model = self.models[model_id]
        model.update(content_type, description, name, schema)
        return model

    def import_api(self, body, fail_on_warnings):
        self.clear()
        body = yaml.safe_load(body)
        for path, path_details in body.get("paths", {}).items():
            for method, method_details in path_details.items():
                route_key = f"{method.upper()} {path}"
                for int_type, type_details in method_details.items():
                    if int_type == "responses":
                        for status_code, response_details in type_details.items():
                            content = response_details.get("content", {})
                            for content_type in content.values():
                                for ref in content_type.get("schema", {}).values():
                                    if ref not in self.models and fail_on_warnings:
                                        attr = f"paths.'{path}'({method}).{int_type}.{status_code}.content.schema.{ref}"
                                        raise BadRequestException(
                                            f"Warnings found during import:\n\tParse issue: attribute {attr} is missing"
                                        )
                    if int_type == "x-amazon-apigateway-integration":
                        integration = self.create_integration(
                            connection_type="INTERNET",
                            description="AutoCreate from OpenAPI Import",
                            integration_type=type_details.get("type"),
                            integration_method=type_details.get("httpMethod"),
                            payload_format_version=type_details.get(
                                "payloadFormatVersion"
                            ),
                            integration_uri=type_details.get("uri"),
                        )
                        self.create_route(
                            api_key_required=False,
                            authorization_scopes=[],
                            route_key=route_key,
                            target=f"integrations/{integration.id}",
                        )
        if "title" in body.get("info", {}):
            self.name = body["info"]["title"]
        if "version" in body.get("info", {}):
            self.version = str(body["info"]["version"])
        if "x-amazon-apigateway-cors" in body:
            self.cors_configuration = body["x-amazon-apigateway-cors"]

    def update(
        self,
        api_key_selection_expression,
        cors_configuration,
        description,
        disable_schema_validation,
        disable_execute_api_endpoint,
        name,
        route_selection_expression,
        version,
    ):
        if api_key_selection_expression is not None:
            self.api_key_selection_expression = api_key_selection_expression
        if cors_configuration is not None:
            self.cors_configuration = cors_configuration
        if description is not None:
            self.description = description
        if disable_execute_api_endpoint is not None:
            self.disable_execute_api_endpoint = disable_execute_api_endpoint
        if disable_schema_validation is not None:
            self.disable_schema_validation = disable_schema_validation
        if name is not None:
            self.name = name
        if route_selection_expression is not None:
            self.route_selection_expression = route_selection_expression
        if version is not None:
            self.version = version

    def create_integration(
        self,
        connection_type,
        description,
        integration_method,
        integration_type,
        integration_uri,
        connection_id=None,
        content_handling_strategy=None,
        credentials_arn=None,
        passthrough_behavior=None,
        payload_format_version=None,
        integration_subtype=None,
        request_parameters=None,
        request_templates=None,
        response_parameters=None,
        template_selection_expression=None,
        timeout_in_millis=None,
        tls_config=None,
    ):
        integration = Integration(
            connection_id=connection_id,
            connection_type=connection_type,
            content_handling_strategy=content_handling_strategy,
            credentials_arn=credentials_arn,
            description=description,
            integration_method=integration_method,
            integration_type=integration_type,
            integration_uri=integration_uri,
            passthrough_behavior=passthrough_behavior,
            payload_format_version=payload_format_version,
            integration_subtype=integration_subtype,
            request_parameters=request_parameters,
            request_templates=request_templates,
            response_parameters=response_parameters,
            template_selection_expression=template_selection_expression,
            timeout_in_millis=timeout_in_millis,
            tls_config=tls_config,
        )
        self.integrations[integration.id] = integration
        return integration

    def delete_integration(self, integration_id):
        self.integrations.pop(integration_id, None)

    def get_integration(self, integration_id):
        if integration_id not in self.integrations:
            raise IntegrationNotFound(integration_id)
        return self.integrations[integration_id]

    def get_integrations(self):
        return self.integrations.values()

    def update_integration(
        self,
        integration_id,
        connection_id,
        connection_type,
        content_handling_strategy,
        credentials_arn,
        description,
        integration_method,
        integration_type,
        integration_uri,
        passthrough_behavior,
        payload_format_version,
        integration_subtype,
        request_parameters,
        request_templates,
        response_parameters,
        template_selection_expression,
        timeout_in_millis,
        tls_config,
    ):
        integration = self.integrations[integration_id]
        integration.update(
            connection_id=connection_id,
            connection_type=connection_type,
            content_handling_strategy=content_handling_strategy,
            credentials_arn=credentials_arn,
            description=description,
            integration_method=integration_method,
            integration_type=integration_type,
            integration_uri=integration_uri,
            passthrough_behavior=passthrough_behavior,
            payload_format_version=payload_format_version,
            integration_subtype=integration_subtype,
            request_parameters=request_parameters,
            request_templates=request_templates,
            response_parameters=response_parameters,
            template_selection_expression=template_selection_expression,
            timeout_in_millis=timeout_in_millis,
            tls_config=tls_config,
        )
        return integration

    def create_integration_response(
        self,
        integration_id,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        integration = self.get_integration(integration_id)
        return integration.create_response(
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )

    def delete_integration_response(self, integration_id, integration_response_id):
        integration = self.get_integration(integration_id)
        integration.delete_response(integration_response_id)

    def get_integration_response(self, integration_id, integration_response_id):
        integration = self.get_integration(integration_id)
        return integration.get_response(integration_response_id)

    def get_integration_responses(self, integration_id):
        integration = self.get_integration(integration_id)
        return integration.get_responses()

    def update_integration_response(
        self,
        integration_id,
        integration_response_id,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        integration = self.get_integration(integration_id)
        return integration.update_response(
            integration_response_id=integration_response_id,
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )

    def create_route(
        self,
        api_key_required,
        authorization_scopes,
        route_key,
        target,
        authorization_type=None,
        authorizer_id=None,
        model_selection_expression=None,
        operation_name=None,
        request_models=None,
        request_parameters=None,
        route_response_selection_expression=None,
    ):
        route = Route(
            api_key_required=api_key_required,
            authorization_scopes=authorization_scopes,
            authorization_type=authorization_type,
            authorizer_id=authorizer_id,
            model_selection_expression=model_selection_expression,
            operation_name=operation_name,
            request_models=request_models,
            request_parameters=request_parameters,
            route_key=route_key,
            route_response_selection_expression=route_response_selection_expression,
            target=target,
        )
        self.routes[route.route_id] = route
        return route

    def delete_route(self, route_id):
        self.routes.pop(route_id, None)

    def delete_route_request_parameter(self, route_id, request_param):
        route = self.get_route(route_id)
        route.delete_route_request_parameter(request_param)

    def get_route(self, route_id):
        if route_id not in self.routes:
            raise RouteNotFound(route_id)
        return self.routes[route_id]

    def get_routes(self):
        return self.routes.values()

    def update_route(
        self,
        route_id,
        api_key_required,
        authorization_scopes,
        authorization_type,
        authorizer_id,
        model_selection_expression,
        operation_name,
        request_models,
        request_parameters,
        route_key,
        route_response_selection_expression,
        target,
    ):
        route = self.get_route(route_id)
        route.update(
            api_key_required=api_key_required,
            authorization_scopes=authorization_scopes,
            authorization_type=authorization_type,
            authorizer_id=authorizer_id,
            model_selection_expression=model_selection_expression,
            operation_name=operation_name,
            request_models=request_models,
            request_parameters=request_parameters,
            route_key=route_key,
            route_response_selection_expression=route_response_selection_expression,
            target=target,
        )
        return route

    def create_route_response(
        self, route_id, route_response_key, model_selection_expression, response_models
    ):
        route = self.get_route(route_id)
        return route.create_route_response(
            route_response_key,
            model_selection_expression=model_selection_expression,
            response_models=response_models,
        )

    def delete_route_response(self, route_id, route_response_id):
        route = self.get_route(route_id)
        route.delete_route_response(route_response_id)

    def get_route_response(self, route_id, route_response_id):
        route = self.get_route(route_id)
        return route.get_route_response(route_response_id)

    def to_json(self):
        return {
            "apiId": self.api_id,
            "apiEndpoint": self.api_endpoint,
            "apiKeySelectionExpression": self.api_key_selection_expression,
            "createdDate": self.created_date,
            "corsConfiguration": self.cors_configuration,
            "description": self.description,
            "disableExecuteApiEndpoint": self.disable_execute_api_endpoint,
            "disableSchemaValidation": self.disable_schema_validation,
            "name": self.name,
            "protocolType": self.protocol_type,
            "routeSelectionExpression": self.route_selection_expression,
            "tags": self.backend.get_tags(self.arn),
            "version": self.version,
        }


class VpcLink(BaseModel):
    def __init__(self, name, sg_ids, subnet_ids, tags, backend):
        self.created = unix_time()
        self.id = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        self.name = name
        self.sg_ids = sg_ids
        self.subnet_ids = subnet_ids

        self.arn = f"arn:aws:apigateway:{backend.region_name}::/vpclinks/{self.id}"
        self.backend = backend
        self.backend.tag_resource(self.arn, tags)

    def update(self, name):
        self.name = name

    def to_json(self):
        return {
            "createdDate": self.created,
            "name": self.name,
            "securityGroupIds": self.sg_ids,
            "subnetIds": self.subnet_ids,
            "tags": self.backend.get_tags(self.arn),
            "vpcLinkId": self.id,
            "vpcLinkStatus": "AVAILABLE",
            "vpcLinkVersion": "V2",
        }


class ApiGatewayV2Backend(BaseBackend):
    """Implementation of ApiGatewayV2 APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.apis = dict()
        self.vpc_links = dict()
        self.tagger = TaggingService()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_api(
        self,
        api_key_selection_expression,
        cors_configuration,
        description,
        disable_schema_validation,
        disable_execute_api_endpoint,
        name,
        protocol_type,
        route_selection_expression,
        tags,
        version,
    ):
        """
        The following parameters are not yet implemented:
        CredentialsArn, RouteKey, Tags, Target
        """
        api = Api(
            region=self.region_name,
            cors_configuration=cors_configuration,
            description=description,
            name=name,
            api_key_selection_expression=api_key_selection_expression,
            disable_execute_api_endpoint=disable_execute_api_endpoint,
            disable_schema_validation=disable_schema_validation,
            protocol_type=protocol_type,
            route_selection_expression=route_selection_expression,
            tags=tags,
            version=version,
            backend=self,
        )
        self.apis[api.api_id] = api
        return api

    def delete_api(self, api_id):
        self.apis.pop(api_id, None)

    def get_api(self, api_id):
        if api_id not in self.apis:
            raise ApiNotFound(api_id)
        return self.apis[api_id]

    def get_apis(self):
        """
        Pagination is not yet implemented
        """
        return self.apis.values()

    def update_api(
        self,
        api_id,
        api_key_selection_expression,
        cors_configuration,
        description,
        disable_schema_validation,
        disable_execute_api_endpoint,
        name,
        route_selection_expression,
        version,
    ):
        """
        The following parameters have not yet been implemented: CredentialsArn, RouteKey, Target
        """
        api = self.get_api(api_id)
        api.update(
            api_key_selection_expression=api_key_selection_expression,
            cors_configuration=cors_configuration,
            description=description,
            disable_schema_validation=disable_schema_validation,
            disable_execute_api_endpoint=disable_execute_api_endpoint,
            name=name,
            route_selection_expression=route_selection_expression,
            version=version,
        )
        return api

    def reimport_api(self, api_id, body, fail_on_warnings):
        """
        Only YAML is supported at the moment. Full OpenAPI-support is not guaranteed. Only limited validation is implemented
        """
        api = self.get_api(api_id)
        api.import_api(body, fail_on_warnings)
        return api

    def delete_cors_configuration(self, api_id):
        api = self.get_api(api_id)
        api.delete_cors_configuration()

    def create_authorizer(
        self,
        api_id,
        auth_creds_arn,
        auth_payload_format_version,
        auth_result_ttl,
        authorizer_uri,
        authorizer_type,
        enable_simple_response,
        identity_source,
        identity_validation_expr,
        jwt_config,
        name,
    ):
        api = self.get_api(api_id)
        authorizer = api.create_authorizer(
            auth_creds_arn=auth_creds_arn,
            auth_payload_format_version=auth_payload_format_version,
            auth_result_ttl=auth_result_ttl,
            authorizer_type=authorizer_type,
            authorizer_uri=authorizer_uri,
            enable_simple_response=enable_simple_response,
            identity_source=identity_source,
            identity_validation_expr=identity_validation_expr,
            jwt_config=jwt_config,
            name=name,
        )
        return authorizer

    def delete_authorizer(self, api_id, authorizer_id):
        api = self.get_api(api_id)
        api.delete_authorizer(authorizer_id=authorizer_id)

    def get_authorizer(self, api_id, authorizer_id):
        api = self.get_api(api_id)
        authorizer = api.get_authorizer(authorizer_id=authorizer_id)
        return authorizer

    def update_authorizer(
        self,
        api_id,
        authorizer_id,
        auth_creds_arn,
        auth_payload_format_version,
        auth_result_ttl,
        authorizer_uri,
        authorizer_type,
        enable_simple_response,
        identity_source,
        identity_validation_expr,
        jwt_config,
        name,
    ):
        api = self.get_api(api_id)
        authorizer = api.update_authorizer(
            authorizer_id=authorizer_id,
            auth_creds_arn=auth_creds_arn,
            auth_payload_format_version=auth_payload_format_version,
            auth_result_ttl=auth_result_ttl,
            authorizer_type=authorizer_type,
            authorizer_uri=authorizer_uri,
            enable_simple_response=enable_simple_response,
            identity_source=identity_source,
            identity_validation_expr=identity_validation_expr,
            jwt_config=jwt_config,
            name=name,
        )
        return authorizer

    def create_model(self, api_id, content_type, description, name, schema):
        api = self.get_api(api_id)
        model = api.create_model(
            content_type=content_type, description=description, name=name, schema=schema
        )
        return model

    def delete_model(self, api_id, model_id):
        api = self.get_api(api_id)
        api.delete_model(model_id=model_id)

    def get_model(self, api_id, model_id):
        api = self.get_api(api_id)
        return api.get_model(model_id)

    def update_model(self, api_id, model_id, content_type, description, name, schema):
        api = self.get_api(api_id)
        return api.update_model(model_id, content_type, description, name, schema)

    def get_tags(self, resource_id):
        return self.tagger.get_tag_dict_for_resource(resource_id)

    def tag_resource(self, resource_arn, tags):
        tags = TaggingService.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn, tag_keys):
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def create_route(
        self,
        api_id,
        api_key_required,
        authorization_scopes,
        authorization_type,
        authorizer_id,
        model_selection_expression,
        operation_name,
        request_models,
        request_parameters,
        route_key,
        route_response_selection_expression,
        target,
    ):
        api = self.get_api(api_id)
        route = api.create_route(
            api_key_required=api_key_required,
            authorization_scopes=authorization_scopes,
            authorization_type=authorization_type,
            authorizer_id=authorizer_id,
            model_selection_expression=model_selection_expression,
            operation_name=operation_name,
            request_models=request_models,
            request_parameters=request_parameters,
            route_key=route_key,
            route_response_selection_expression=route_response_selection_expression,
            target=target,
        )
        return route

    def delete_route(self, api_id, route_id):
        api = self.get_api(api_id)
        api.delete_route(route_id)

    def delete_route_request_parameter(self, api_id, route_id, request_param):
        api = self.get_api(api_id)
        api.delete_route_request_parameter(route_id, request_param)

    def get_route(self, api_id, route_id):
        api = self.get_api(api_id)
        return api.get_route(route_id)

    def get_routes(self, api_id):
        """
        Pagination is not yet implemented
        """
        api = self.get_api(api_id)
        return api.get_routes()

    def update_route(
        self,
        api_id,
        api_key_required,
        authorization_scopes,
        authorization_type,
        authorizer_id,
        model_selection_expression,
        operation_name,
        request_models,
        request_parameters,
        route_id,
        route_key,
        route_response_selection_expression,
        target,
    ):
        api = self.get_api(api_id)
        route = api.update_route(
            route_id=route_id,
            api_key_required=api_key_required,
            authorization_scopes=authorization_scopes,
            authorization_type=authorization_type,
            authorizer_id=authorizer_id,
            model_selection_expression=model_selection_expression,
            operation_name=operation_name,
            request_models=request_models,
            request_parameters=request_parameters,
            route_key=route_key,
            route_response_selection_expression=route_response_selection_expression,
            target=target,
        )
        return route

    def create_route_response(
        self,
        api_id,
        route_id,
        route_response_key,
        model_selection_expression,
        response_models,
    ):
        """
        The following parameters are not yet implemented: ResponseModels, ResponseParameters
        """
        api = self.get_api(api_id)
        return api.create_route_response(
            route_id,
            route_response_key,
            model_selection_expression=model_selection_expression,
            response_models=response_models,
        )

    def delete_route_response(self, api_id, route_id, route_response_id):
        api = self.get_api(api_id)
        api.delete_route_response(route_id, route_response_id)

    def get_route_response(self, api_id, route_id, route_response_id):
        api = self.get_api(api_id)
        return api.get_route_response(route_id, route_response_id)

    def create_integration(
        self,
        api_id,
        connection_id,
        connection_type,
        content_handling_strategy,
        credentials_arn,
        description,
        integration_method,
        integration_subtype,
        integration_type,
        integration_uri,
        passthrough_behavior,
        payload_format_version,
        request_parameters,
        request_templates,
        response_parameters,
        template_selection_expression,
        timeout_in_millis,
        tls_config,
    ):
        api = self.get_api(api_id)
        integration = api.create_integration(
            connection_id=connection_id,
            connection_type=connection_type,
            content_handling_strategy=content_handling_strategy,
            credentials_arn=credentials_arn,
            description=description,
            integration_method=integration_method,
            integration_type=integration_type,
            integration_uri=integration_uri,
            passthrough_behavior=passthrough_behavior,
            payload_format_version=payload_format_version,
            integration_subtype=integration_subtype,
            request_parameters=request_parameters,
            request_templates=request_templates,
            response_parameters=response_parameters,
            template_selection_expression=template_selection_expression,
            timeout_in_millis=timeout_in_millis,
            tls_config=tls_config,
        )
        return integration

    def get_integration(self, api_id, integration_id):
        api = self.get_api(api_id)
        integration = api.get_integration(integration_id)
        return integration

    def get_integrations(self, api_id):
        """
        Pagination is not yet implemented
        """
        api = self.get_api(api_id)
        return api.get_integrations()

    def delete_integration(self, api_id, integration_id):
        api = self.get_api(api_id)
        api.delete_integration(integration_id)

    def update_integration(
        self,
        api_id,
        connection_id,
        connection_type,
        content_handling_strategy,
        credentials_arn,
        description,
        integration_id,
        integration_method,
        integration_subtype,
        integration_type,
        integration_uri,
        passthrough_behavior,
        payload_format_version,
        request_parameters,
        request_templates,
        response_parameters,
        template_selection_expression,
        timeout_in_millis,
        tls_config,
    ):
        api = self.get_api(api_id)
        integration = api.update_integration(
            integration_id=integration_id,
            connection_id=connection_id,
            connection_type=connection_type,
            content_handling_strategy=content_handling_strategy,
            credentials_arn=credentials_arn,
            description=description,
            integration_method=integration_method,
            integration_type=integration_type,
            integration_uri=integration_uri,
            passthrough_behavior=passthrough_behavior,
            payload_format_version=payload_format_version,
            integration_subtype=integration_subtype,
            request_parameters=request_parameters,
            request_templates=request_templates,
            response_parameters=response_parameters,
            template_selection_expression=template_selection_expression,
            timeout_in_millis=timeout_in_millis,
            tls_config=tls_config,
        )
        return integration

    def create_integration_response(
        self,
        api_id,
        integration_id,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        api = self.get_api(api_id)
        integration_response = api.create_integration_response(
            integration_id=integration_id,
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )
        return integration_response

    def delete_integration_response(
        self, api_id, integration_id, integration_response_id
    ):
        api = self.get_api(api_id)
        api.delete_integration_response(
            integration_id, integration_response_id=integration_response_id
        )

    def get_integration_response(self, api_id, integration_id, integration_response_id):
        api = self.get_api(api_id)
        return api.get_integration_response(
            integration_id, integration_response_id=integration_response_id
        )

    def get_integration_responses(self, api_id, integration_id):
        api = self.get_api(api_id)
        return api.get_integration_responses(integration_id)

    def update_integration_response(
        self,
        api_id,
        integration_id,
        integration_response_id,
        content_handling_strategy,
        integration_response_key,
        response_parameters,
        response_templates,
        template_selection_expression,
    ):
        api = self.get_api(api_id)
        integration_response = api.update_integration_response(
            integration_id=integration_id,
            integration_response_id=integration_response_id,
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )
        return integration_response

    def create_vpc_link(self, name, sg_ids, subnet_ids, tags):
        vpc_link = VpcLink(
            name, sg_ids=sg_ids, subnet_ids=subnet_ids, tags=tags, backend=self
        )
        self.vpc_links[vpc_link.id] = vpc_link
        return vpc_link

    def get_vpc_link(self, vpc_link_id):
        if vpc_link_id not in self.vpc_links:
            raise VpcLinkNotFound(vpc_link_id)
        return self.vpc_links[vpc_link_id]

    def delete_vpc_link(self, vpc_link_id):
        self.vpc_links.pop(vpc_link_id, None)

    def get_vpc_links(self):
        return self.vpc_links.values()

    def update_vpc_link(self, vpc_link_id, name):
        vpc_link = self.get_vpc_link(vpc_link_id)
        vpc_link.update(name)
        return vpc_link


apigatewayv2_backends = BackendDict(ApiGatewayV2Backend, "apigatewayv2")
