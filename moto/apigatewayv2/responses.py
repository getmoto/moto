"""Handles incoming apigatewayv2 requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from urllib.parse import unquote

from .exceptions import UnknownProtocol
from .models import apigatewayv2_backends


class ApiGatewayV2Response(BaseResponse):
    """Handler for ApiGatewayV2 requests and responses."""

    @property
    def apigatewayv2_backend(self):
        """Return backend instance specific for this region."""
        return apigatewayv2_backends[self.region]

    def apis(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_api()
        if self.method == "GET":
            return self.get_apis()

    def api(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_api()
        if self.method == "PATCH":
            return self.update_api()
        if self.method == "PUT":
            return self.reimport_api()
        if self.method == "DELETE":
            return self.delete_api()

    def authorizer(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_authorizer()
        if self.method == "GET":
            return self.get_authorizer()
        if self.method == "PATCH":
            return self.update_authorizer()

    def authorizers(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_authorizer()

    def cors(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_cors_configuration()

    def route_request_parameter(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_route_request_parameter()

    def model(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_model()
        if self.method == "GET":
            return self.get_model()
        if self.method == "PATCH":
            return self.update_model()

    def models(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_model()

    def integration(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_integration()
        if self.method == "GET":
            return self.get_integration()
        if self.method == "PATCH":
            return self.update_integration()

    def integrations(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_integrations()
        if self.method == "POST":
            return self.create_integration()

    def integration_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_integration_response()
        if self.method == "GET":
            return self.get_integration_response()
        if self.method == "PATCH":
            return self.update_integration_response()

    def integration_responses(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_integration_responses()
        if self.method == "POST":
            return self.create_integration_response()

    def route(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_route()
        if self.method == "GET":
            return self.get_route()
        if self.method == "PATCH":
            return self.update_route()

    def routes(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_routes()
        if self.method == "POST":
            return self.create_route()

    def route_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "DELETE":
            return self.delete_route_response()
        if self.method == "GET":
            return self.get_route_response()

    def route_responses(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_route_response()

    def tags(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.tag_resource()
        if self.method == "GET":
            return self.get_tags()
        if self.method == "DELETE":
            return self.untag_resource()

    def vpc_link(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if request.method == "DELETE":
            return self.delete_vpc_link()
        if request.method == "GET":
            return self.get_vpc_link()
        if request.method == "PATCH":
            return self.update_vpc_link()

    def vpc_links(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if request.method == "GET":
            return self.get_vpc_links()
        if request.method == "POST":
            return self.create_vpc_link()

    def create_api(self):
        params = json.loads(self.body)

        api_key_selection_expression = params.get("apiKeySelectionExpression")
        cors_configuration = params.get("corsConfiguration")
        description = params.get("description")
        disable_schema_validation = params.get("disableSchemaValidation")
        disable_execute_api_endpoint = params.get("disableExecuteApiEndpoint")
        name = params.get("name")
        protocol_type = params.get("protocolType")
        route_selection_expression = params.get("routeSelectionExpression")
        tags = params.get("tags")
        version = params.get("version")

        if protocol_type not in ["HTTP", "WEBSOCKET"]:
            raise UnknownProtocol

        api = self.apigatewayv2_backend.create_api(
            api_key_selection_expression=api_key_selection_expression,
            cors_configuration=cors_configuration,
            description=description,
            disable_schema_validation=disable_schema_validation,
            disable_execute_api_endpoint=disable_execute_api_endpoint,
            name=name,
            protocol_type=protocol_type,
            route_selection_expression=route_selection_expression,
            tags=tags,
            version=version,
        )
        return 200, {}, json.dumps(api.to_json())

    def delete_api(self):
        api_id = self.path.split("/")[-1]
        self.apigatewayv2_backend.delete_api(api_id=api_id)
        return 200, "", "{}"

    def get_api(self):
        api_id = self.path.split("/")[-1]
        api = self.apigatewayv2_backend.get_api(api_id=api_id)
        return 200, {}, json.dumps(api.to_json())

    def get_apis(self):
        apis = self.apigatewayv2_backend.get_apis()
        return 200, {}, json.dumps({"items": [a.to_json() for a in apis]})

    def update_api(self):
        api_id = self.path.split("/")[-1]
        params = json.loads(self.body)
        api_key_selection_expression = params.get("apiKeySelectionExpression")
        cors_configuration = params.get("corsConfiguration")
        description = params.get("description")
        disable_schema_validation = params.get("disableSchemaValidation")
        disable_execute_api_endpoint = params.get("disableExecuteApiEndpoint")
        name = params.get("name")
        route_selection_expression = params.get("routeSelectionExpression")
        version = params.get("version")
        api = self.apigatewayv2_backend.update_api(
            api_id=api_id,
            api_key_selection_expression=api_key_selection_expression,
            cors_configuration=cors_configuration,
            description=description,
            disable_schema_validation=disable_schema_validation,
            disable_execute_api_endpoint=disable_execute_api_endpoint,
            name=name,
            route_selection_expression=route_selection_expression,
            version=version,
        )
        return 200, {}, json.dumps(api.to_json())

    def reimport_api(self):
        api_id = self.path.split("/")[-1]
        params = json.loads(self.body)
        body = params.get("body")
        fail_on_warnings = (
            str(self._get_param("failOnWarnings", "false")).lower() == "true"
        )

        api = self.apigatewayv2_backend.reimport_api(api_id, body, fail_on_warnings)
        return 201, {}, json.dumps(api.to_json())

    def create_authorizer(self):
        api_id = self.path.split("/")[-2]
        params = json.loads(self.body)

        auth_creds_arn = params.get("authorizerCredentialsArn")
        auth_payload_format_version = (
            params.get("authorizerPayloadFormatVersion") or "2.0"
        )
        auth_result_ttl = params.get("authorizerResultTtlInSeconds")
        authorizer_type = params.get("authorizerType")
        authorizer_uri = params.get("authorizerUri")
        enable_simple_response = params.get("enableSimpleResponses")
        identity_source = params.get("identitySource")
        identity_validation_expr = params.get("identityValidationExpression")
        jwt_config = params.get("jwtConfiguration")
        name = params.get("name")
        authorizer = self.apigatewayv2_backend.create_authorizer(
            api_id,
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
        return 200, {}, json.dumps(authorizer.to_json())

    def delete_authorizer(self):
        api_id = self.path.split("/")[-3]
        authorizer_id = self.path.split("/")[-1]

        self.apigatewayv2_backend.delete_authorizer(api_id, authorizer_id)
        return 200, {}, "{}"

    def get_authorizer(self):
        api_id = self.path.split("/")[-3]
        authorizer_id = self.path.split("/")[-1]

        authorizer = self.apigatewayv2_backend.get_authorizer(api_id, authorizer_id)
        return 200, {}, json.dumps(authorizer.to_json())

    def update_authorizer(self):
        api_id = self.path.split("/")[-3]
        authorizer_id = self.path.split("/")[-1]
        params = json.loads(self.body)

        auth_creds_arn = params.get("authorizerCredentialsArn")
        auth_payload_format_version = params.get("authorizerPayloadFormatVersion")
        auth_result_ttl = params.get("authorizerResultTtlInSeconds")
        authorizer_type = params.get("authorizerType")
        authorizer_uri = params.get("authorizerUri")
        enable_simple_response = params.get("enableSimpleResponses")
        identity_source = params.get("identitySource")
        identity_validation_expr = params.get("identityValidationExpression")
        jwt_config = params.get("jwtConfiguration")
        name = params.get("name")
        authorizer = self.apigatewayv2_backend.update_authorizer(
            api_id,
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
        return 200, {}, json.dumps(authorizer.to_json())

    def delete_cors_configuration(self):
        api_id = self.path.split("/")[-2]
        self.apigatewayv2_backend.delete_cors_configuration(api_id)
        return 200, {}, "{}"

    def create_model(self):
        api_id = self.path.split("/")[-2]
        params = json.loads(self.body)

        content_type = params.get("contentType")
        description = params.get("description")
        name = params.get("name")
        schema = params.get("schema")
        model = self.apigatewayv2_backend.create_model(
            api_id, content_type, description, name, schema
        )
        return 200, {}, json.dumps(model.to_json())

    def delete_model(self):
        api_id = self.path.split("/")[-3]
        model_id = self.path.split("/")[-1]

        self.apigatewayv2_backend.delete_model(api_id, model_id)
        return 200, {}, "{}"

    def get_model(self):
        api_id = self.path.split("/")[-3]
        model_id = self.path.split("/")[-1]

        model = self.apigatewayv2_backend.get_model(api_id, model_id)
        return 200, {}, json.dumps(model.to_json())

    def update_model(self):
        api_id = self.path.split("/")[-3]
        model_id = self.path.split("/")[-1]
        params = json.loads(self.body)

        content_type = params.get("contentType")
        description = params.get("description")
        name = params.get("name")
        schema = params.get("schema")

        model = self.apigatewayv2_backend.update_model(
            api_id,
            model_id,
            content_type=content_type,
            description=description,
            name=name,
            schema=schema,
        )
        return 200, {}, json.dumps(model.to_json())

    def get_tags(self):
        resource_arn = unquote(self.path.split("/tags/")[1])
        tags = self.apigatewayv2_backend.get_tags(resource_arn)
        return 200, {}, json.dumps({"tags": tags})

    def tag_resource(self):
        resource_arn = unquote(self.path.split("/tags/")[1])
        tags = json.loads(self.body).get("tags", {})
        self.apigatewayv2_backend.tag_resource(resource_arn, tags)
        return 201, {}, "{}"

    def untag_resource(self):
        resource_arn = unquote(self.path.split("/tags/")[1])
        tag_keys = self.querystring.get("tagKeys")
        self.apigatewayv2_backend.untag_resource(resource_arn, tag_keys)
        return 200, {}, "{}"

    def create_route(self):
        api_id = self.path.split("/")[-2]
        params = json.loads(self.body)
        api_key_required = params.get("apiKeyRequired", False)
        authorization_scopes = params.get("authorizationScopes")
        authorization_type = params.get("authorizationType", "NONE")
        authorizer_id = params.get("authorizerId")
        model_selection_expression = params.get("modelSelectionExpression")
        operation_name = params.get("operationName")
        request_models = params.get("requestModels")
        request_parameters = params.get("requestParameters")
        route_key = params.get("routeKey")
        route_response_selection_expression = params.get(
            "routeResponseSelectionExpression"
        )
        target = params.get("target")
        route = self.apigatewayv2_backend.create_route(
            api_id=api_id,
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
        return 201, {}, json.dumps(route.to_json())

    def delete_route(self):
        api_id = self.path.split("/")[-3]
        route_id = self.path.split("/")[-1]
        self.apigatewayv2_backend.delete_route(api_id=api_id, route_id=route_id)
        return 200, {}, "{}"

    def delete_route_request_parameter(self):
        api_id = self.path.split("/")[-5]
        route_id = self.path.split("/")[-3]
        request_param = self.path.split("/")[-1]
        self.apigatewayv2_backend.delete_route_request_parameter(
            api_id, route_id, request_param
        )
        return 200, {}, "{}"

    def get_route(self):
        api_id = self.path.split("/")[-3]
        route_id = self.path.split("/")[-1]
        api = self.apigatewayv2_backend.get_route(api_id=api_id, route_id=route_id)
        return 200, {}, json.dumps(api.to_json())

    def get_routes(self):
        api_id = self.path.split("/")[-2]
        apis = self.apigatewayv2_backend.get_routes(api_id=api_id)
        return 200, {}, json.dumps({"items": [api.to_json() for api in apis]})

    def update_route(self):
        api_id = self.path.split("/")[-3]
        route_id = self.path.split("/")[-1]

        params = json.loads(self.body)
        api_key_required = params.get("apiKeyRequired")
        authorization_scopes = params.get("authorizationScopes")
        authorization_type = params.get("authorizationType")
        authorizer_id = params.get("authorizerId")
        model_selection_expression = params.get("modelSelectionExpression")
        operation_name = params.get("operationName")
        request_models = params.get("requestModels")
        request_parameters = params.get("requestParameters")
        route_key = params.get("routeKey")
        route_response_selection_expression = params.get(
            "routeResponseSelectionExpression"
        )
        target = params.get("target")
        api = self.apigatewayv2_backend.update_route(
            api_id=api_id,
            api_key_required=api_key_required,
            authorization_scopes=authorization_scopes,
            authorization_type=authorization_type,
            authorizer_id=authorizer_id,
            model_selection_expression=model_selection_expression,
            operation_name=operation_name,
            request_models=request_models,
            request_parameters=request_parameters,
            route_id=route_id,
            route_key=route_key,
            route_response_selection_expression=route_response_selection_expression,
            target=target,
        )
        return 200, {}, json.dumps(api.to_json())

    def create_route_response(self):
        api_id = self.path.split("/")[-4]
        route_id = self.path.split("/")[-2]
        params = json.loads(self.body)

        response_models = params.get("responseModels")
        route_response_key = params.get("routeResponseKey")
        model_selection_expression = params.get("modelSelectionExpression")
        route_response = self.apigatewayv2_backend.create_route_response(
            api_id,
            route_id,
            route_response_key,
            model_selection_expression=model_selection_expression,
            response_models=response_models,
        )
        return 200, {}, json.dumps(route_response.to_json())

    def delete_route_response(self):
        api_id = self.path.split("/")[-5]
        route_id = self.path.split("/")[-3]
        route_response_id = self.path.split("/")[-1]

        self.apigatewayv2_backend.delete_route_response(
            api_id, route_id, route_response_id
        )
        return 200, {}, "{}"

    def get_route_response(self):
        api_id = self.path.split("/")[-5]
        route_id = self.path.split("/")[-3]
        route_response_id = self.path.split("/")[-1]

        route_response = self.apigatewayv2_backend.get_route_response(
            api_id, route_id, route_response_id
        )
        return 200, {}, json.dumps(route_response.to_json())

    def create_integration(self):
        api_id = self.path.split("/")[-2]

        params = json.loads(self.body)
        connection_id = params.get("connectionId")
        connection_type = params.get("connectionType")
        content_handling_strategy = params.get("contentHandlingStrategy")
        credentials_arn = params.get("credentialsArn")
        description = params.get("description")
        integration_method = params.get("integrationMethod")
        integration_subtype = params.get("integrationSubtype")
        integration_type = params.get("integrationType")
        integration_uri = params.get("integrationUri")
        passthrough_behavior = params.get("passthroughBehavior")
        payload_format_version = params.get("payloadFormatVersion")
        request_parameters = params.get("requestParameters")
        request_templates = params.get("requestTemplates")
        response_parameters = params.get("responseParameters")
        template_selection_expression = params.get("templateSelectionExpression")
        timeout_in_millis = params.get("timeoutInMillis")
        tls_config = params.get("tlsConfig")
        integration = self.apigatewayv2_backend.create_integration(
            api_id=api_id,
            connection_id=connection_id,
            connection_type=connection_type,
            content_handling_strategy=content_handling_strategy,
            credentials_arn=credentials_arn,
            description=description,
            integration_method=integration_method,
            integration_subtype=integration_subtype,
            integration_type=integration_type,
            integration_uri=integration_uri,
            passthrough_behavior=passthrough_behavior,
            payload_format_version=payload_format_version,
            request_parameters=request_parameters,
            request_templates=request_templates,
            response_parameters=response_parameters,
            template_selection_expression=template_selection_expression,
            timeout_in_millis=timeout_in_millis,
            tls_config=tls_config,
        )
        return 200, {}, json.dumps(integration.to_json())

    def get_integration(self):
        api_id = self.path.split("/")[-3]
        integration_id = self.path.split("/")[-1]

        integration = self.apigatewayv2_backend.get_integration(
            api_id=api_id, integration_id=integration_id
        )
        return 200, {}, json.dumps(integration.to_json())

    def get_integrations(self):
        api_id = self.path.split("/")[-2]

        integrations = self.apigatewayv2_backend.get_integrations(api_id=api_id)
        return 200, {}, json.dumps({"items": [i.to_json() for i in integrations]})

    def delete_integration(self):
        api_id = self.path.split("/")[-3]
        integration_id = self.path.split("/")[-1]

        self.apigatewayv2_backend.delete_integration(
            api_id=api_id, integration_id=integration_id
        )
        return 200, {}, "{}"

    def update_integration(self):
        api_id = self.path.split("/")[-3]
        integration_id = self.path.split("/")[-1]

        params = json.loads(self.body)
        connection_id = params.get("connectionId")
        connection_type = params.get("connectionType")
        content_handling_strategy = params.get("contentHandlingStrategy")
        credentials_arn = params.get("credentialsArn")
        description = params.get("description")
        integration_method = params.get("integrationMethod")
        integration_subtype = params.get("integrationSubtype")
        integration_type = params.get("integrationType")
        integration_uri = params.get("integrationUri")
        passthrough_behavior = params.get("passthroughBehavior")
        payload_format_version = params.get("payloadFormatVersion")
        request_parameters = params.get("requestParameters")
        request_templates = params.get("requestTemplates")
        response_parameters = params.get("responseParameters")
        template_selection_expression = params.get("templateSelectionExpression")
        timeout_in_millis = params.get("timeoutInMillis")
        tls_config = params.get("tlsConfig")
        integration = self.apigatewayv2_backend.update_integration(
            api_id=api_id,
            connection_id=connection_id,
            connection_type=connection_type,
            content_handling_strategy=content_handling_strategy,
            credentials_arn=credentials_arn,
            description=description,
            integration_id=integration_id,
            integration_method=integration_method,
            integration_subtype=integration_subtype,
            integration_type=integration_type,
            integration_uri=integration_uri,
            passthrough_behavior=passthrough_behavior,
            payload_format_version=payload_format_version,
            request_parameters=request_parameters,
            request_templates=request_templates,
            response_parameters=response_parameters,
            template_selection_expression=template_selection_expression,
            timeout_in_millis=timeout_in_millis,
            tls_config=tls_config,
        )
        return 200, {}, json.dumps(integration.to_json())

    def create_integration_response(self):
        api_id = self.path.split("/")[-4]
        int_id = self.path.split("/")[-2]

        params = json.loads(self.body)
        content_handling_strategy = params.get("contentHandlingStrategy")
        integration_response_key = params.get("integrationResponseKey")
        response_parameters = params.get("responseParameters")
        response_templates = params.get("responseTemplates")
        template_selection_expression = params.get("templateSelectionExpression")
        integration_response = self.apigatewayv2_backend.create_integration_response(
            api_id=api_id,
            integration_id=int_id,
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )
        return 200, {}, json.dumps(integration_response.to_json())

    def delete_integration_response(self):
        api_id = self.path.split("/")[-5]
        int_id = self.path.split("/")[-3]
        int_res_id = self.path.split("/")[-1]

        self.apigatewayv2_backend.delete_integration_response(
            api_id=api_id, integration_id=int_id, integration_response_id=int_res_id
        )
        return 200, {}, "{}"

    def get_integration_response(self):
        api_id = self.path.split("/")[-5]
        int_id = self.path.split("/")[-3]
        int_res_id = self.path.split("/")[-1]

        int_response = self.apigatewayv2_backend.get_integration_response(
            api_id=api_id, integration_id=int_id, integration_response_id=int_res_id
        )
        return 200, {}, json.dumps(int_response.to_json())

    def get_integration_responses(self):
        api_id = self.path.split("/")[-4]
        int_id = self.path.split("/")[-2]

        int_response = self.apigatewayv2_backend.get_integration_responses(
            api_id=api_id, integration_id=int_id
        )
        return 200, {}, json.dumps({"items": [res.to_json() for res in int_response]})

    def update_integration_response(self):
        api_id = self.path.split("/")[-5]
        int_id = self.path.split("/")[-3]
        int_res_id = self.path.split("/")[-1]

        params = json.loads(self.body)
        content_handling_strategy = params.get("contentHandlingStrategy")
        integration_response_key = params.get("integrationResponseKey")
        response_parameters = params.get("responseParameters")
        response_templates = params.get("responseTemplates")
        template_selection_expression = params.get("templateSelectionExpression")
        integration_response = self.apigatewayv2_backend.update_integration_response(
            api_id=api_id,
            integration_id=int_id,
            integration_response_id=int_res_id,
            content_handling_strategy=content_handling_strategy,
            integration_response_key=integration_response_key,
            response_parameters=response_parameters,
            response_templates=response_templates,
            template_selection_expression=template_selection_expression,
        )
        return 200, {}, json.dumps(integration_response.to_json())

    def create_vpc_link(self):
        params = json.loads(self.body)

        name = params.get("name")
        sg_ids = params.get("securityGroupIds")
        subnet_ids = params.get("subnetIds")
        tags = params.get("tags")
        vpc_link = self.apigatewayv2_backend.create_vpc_link(
            name, sg_ids, subnet_ids, tags
        )
        return 200, {}, json.dumps(vpc_link.to_json())

    def delete_vpc_link(self):
        vpc_link_id = self.path.split("/")[-1]
        self.apigatewayv2_backend.delete_vpc_link(vpc_link_id)
        return 200, {}, "{}"

    def get_vpc_link(self):
        vpc_link_id = self.path.split("/")[-1]
        vpc_link = self.apigatewayv2_backend.get_vpc_link(vpc_link_id)
        return 200, {}, json.dumps(vpc_link.to_json())

    def get_vpc_links(self):
        vpc_links = self.apigatewayv2_backend.get_vpc_links()
        return 200, {}, json.dumps({"items": [link.to_json() for link in vpc_links]})

    def update_vpc_link(self):
        vpc_link_id = self.path.split("/")[-1]
        params = json.loads(self.body)
        name = params.get("name")

        vpc_link = self.apigatewayv2_backend.update_vpc_link(vpc_link_id, name=name)
        return 200, {}, json.dumps(vpc_link.to_json())
