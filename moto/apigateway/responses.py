from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import apigateway_backends
from .exceptions import (
    ApiKeyNotFoundException,
    UsagePlanNotFoundException,
    BadRequestException,
    CrossAccountNotAllowed,
    AuthorizerNotFoundException,
    StageNotFoundException,
    ApiKeyAlreadyExists,
    DomainNameNotFound,
    InvalidDomainName,
    InvalidRestApiId,
    InvalidModelName,
    RestAPINotFound,
    ModelNotFound,
    ApiKeyValueMinLength,
)

API_KEY_SOURCES = ["AUTHORIZER", "HEADER"]
AUTHORIZER_TYPES = ["TOKEN", "REQUEST", "COGNITO_USER_POOLS"]
ENDPOINT_CONFIGURATION_TYPES = ["PRIVATE", "EDGE", "REGIONAL"]


class APIGatewayResponse(BaseResponse):
    def error(self, type_, message, status=400):
        return (
            status,
            self.response_headers,
            json.dumps({"__type": type_, "message": message}),
        )

    @property
    def backend(self):
        return apigateway_backends[self.region]

    def restapis(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            apis = self.backend.list_apis()
            return 200, {}, json.dumps({"item": [api.to_dict() for api in apis]})
        elif self.method == "POST":
            name = self._get_param("name")
            description = self._get_param("description")
            api_key_source = self._get_param("apiKeySource")
            endpoint_configuration = self._get_param("endpointConfiguration")
            tags = self._get_param("tags")
            policy = self._get_param("policy")

            # Param validation
            if api_key_source and api_key_source not in API_KEY_SOURCES:
                return self.error(
                    "ValidationException",
                    (
                        "1 validation error detected: "
                        "Value '{api_key_source}' at 'createRestApiInput.apiKeySource' failed "
                        "to satisfy constraint: Member must satisfy enum value set: "
                        "[AUTHORIZER, HEADER]"
                    ).format(api_key_source=api_key_source),
                )

            if endpoint_configuration and "types" in endpoint_configuration:
                invalid_types = list(
                    set(endpoint_configuration["types"])
                    - set(ENDPOINT_CONFIGURATION_TYPES)
                )
                if invalid_types:
                    return self.error(
                        "ValidationException",
                        (
                            "1 validation error detected: Value '{endpoint_type}' "
                            "at 'createRestApiInput.endpointConfiguration.types' failed "
                            "to satisfy constraint: Member must satisfy enum value set: "
                            "[PRIVATE, EDGE, REGIONAL]"
                        ).format(endpoint_type=invalid_types[0]),
                    )

            rest_api = self.backend.create_rest_api(
                name,
                description,
                api_key_source=api_key_source,
                endpoint_configuration=endpoint_configuration,
                tags=tags,
                policy=policy,
            )
            return 200, {}, json.dumps(rest_api.to_dict())

    def restapis_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == "GET":
            rest_api = self.backend.get_rest_api(function_id)
            return 200, {}, json.dumps(rest_api.to_dict())
        elif self.method == "DELETE":
            rest_api = self.backend.delete_rest_api(function_id)
            return 200, {}, json.dumps(rest_api.to_dict())

    def resources(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == "GET":
            resources = self.backend.list_resources(function_id)
            return (
                200,
                {},
                json.dumps({"item": [resource.to_dict() for resource in resources]}),
            )

    def resource_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]
        resource_id = self.path.split("/")[-1]

        try:
            if self.method == "GET":
                resource = self.backend.get_resource(function_id, resource_id)
            elif self.method == "POST":
                path_part = self._get_param("pathPart")
                resource = self.backend.create_resource(
                    function_id, resource_id, path_part
                )
            elif self.method == "DELETE":
                resource = self.backend.delete_resource(function_id, resource_id)
            return 200, {}, json.dumps(resource.to_dict())
        except BadRequestException as e:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#BadRequestException", e.message
            )

    def resource_methods(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]

        if self.method == "GET":
            method = self.backend.get_method(function_id, resource_id, method_type)
            return 200, {}, json.dumps(method)
        elif self.method == "PUT":
            authorization_type = self._get_param("authorizationType")
            api_key_required = self._get_param("apiKeyRequired")
            method = self.backend.create_method(
                function_id,
                resource_id,
                method_type,
                authorization_type,
                api_key_required,
            )
            return 200, {}, json.dumps(method)

    def resource_method_responses(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]
        response_code = url_path_parts[8]

        if self.method == "GET":
            method_response = self.backend.get_method_response(
                function_id, resource_id, method_type, response_code
            )
        elif self.method == "PUT":
            method_response = self.backend.create_method_response(
                function_id, resource_id, method_type, response_code
            )
        elif self.method == "DELETE":
            method_response = self.backend.delete_method_response(
                function_id, resource_id, method_type, response_code
            )
        return 200, {}, json.dumps(method_response)

    def restapis_authorizers(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        restapi_id = url_path_parts[2]

        if self.method == "POST":
            name = self._get_param("name")
            authorizer_type = self._get_param("type")

            provider_arns = self._get_param("providerARNs")
            auth_type = self._get_param("authType")
            authorizer_uri = self._get_param("authorizerUri")
            authorizer_credentials = self._get_param("authorizerCredentials")
            identity_source = self._get_param("identitySource")
            identiy_validation_expression = self._get_param(
                "identityValidationExpression"
            )
            authorizer_result_ttl = self._get_param(
                "authorizerResultTtlInSeconds", if_none=300
            )

            # Param validation
            if authorizer_type and authorizer_type not in AUTHORIZER_TYPES:
                return self.error(
                    "ValidationException",
                    (
                        "1 validation error detected: "
                        "Value '{authorizer_type}' at 'createAuthorizerInput.type' failed "
                        "to satisfy constraint: Member must satisfy enum value set: "
                        "[TOKEN, REQUEST, COGNITO_USER_POOLS]"
                    ).format(authorizer_type=authorizer_type),
                )

            authorizer_response = self.backend.create_authorizer(
                restapi_id,
                name,
                authorizer_type,
                provider_arns=provider_arns,
                auth_type=auth_type,
                authorizer_uri=authorizer_uri,
                authorizer_credentials=authorizer_credentials,
                identity_source=identity_source,
                identiy_validation_expression=identiy_validation_expression,
                authorizer_result_ttl=authorizer_result_ttl,
            )
        elif self.method == "GET":
            authorizers = self.backend.get_authorizers(restapi_id)
            return 200, {}, json.dumps({"item": authorizers})

        return 200, {}, json.dumps(authorizer_response)

    def authorizers(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        restapi_id = url_path_parts[2]
        authorizer_id = url_path_parts[4]

        if self.method == "GET":
            try:
                authorizer_response = self.backend.get_authorizer(
                    restapi_id, authorizer_id
                )
            except AuthorizerNotFoundException as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            authorizer_response = self.backend.update_authorizer(
                restapi_id, authorizer_id, patch_operations
            )
        elif self.method == "DELETE":
            self.backend.delete_authorizer(restapi_id, authorizer_id)
            return 202, {}, "{}"
        return 200, {}, json.dumps(authorizer_response)

    def restapis_stages(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]

        if self.method == "POST":
            stage_name = self._get_param("stageName")
            deployment_id = self._get_param("deploymentId")
            stage_variables = self._get_param("variables", if_none={})
            description = self._get_param("description", if_none="")
            cacheClusterEnabled = self._get_param("cacheClusterEnabled", if_none=False)
            cacheClusterSize = self._get_param("cacheClusterSize")

            stage_response = self.backend.create_stage(
                function_id,
                stage_name,
                deployment_id,
                variables=stage_variables,
                description=description,
                cacheClusterEnabled=cacheClusterEnabled,
                cacheClusterSize=cacheClusterSize,
            )
        elif self.method == "GET":
            stages = self.backend.get_stages(function_id)
            return 200, {}, json.dumps({"item": stages})

        return 200, {}, json.dumps(stage_response)

    def stages(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        stage_name = url_path_parts[4]

        if self.method == "GET":
            try:
                stage_response = self.backend.get_stage(function_id, stage_name)
            except StageNotFoundException as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            stage_response = self.backend.update_stage(
                function_id, stage_name, patch_operations
            )
        elif self.method == "DELETE":
            self.backend.delete_stage(function_id, stage_name)
            return 202, {}, "{}"
        return 200, {}, json.dumps(stage_response)

    def integrations(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]

        try:
            if self.method == "GET":
                integration_response = self.backend.get_integration(
                    function_id, resource_id, method_type
                )
            elif self.method == "PUT":
                integration_type = self._get_param("type")
                uri = self._get_param("uri")
                integration_http_method = self._get_param("httpMethod")
                creds = self._get_param("credentials")
                request_templates = self._get_param("requestTemplates")
                integration_response = self.backend.create_integration(
                    function_id,
                    resource_id,
                    method_type,
                    integration_type,
                    uri,
                    credentials=creds,
                    integration_method=integration_http_method,
                    request_templates=request_templates,
                )
            elif self.method == "DELETE":
                integration_response = self.backend.delete_integration(
                    function_id, resource_id, method_type
                )
            return 200, {}, json.dumps(integration_response)
        except BadRequestException as e:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#BadRequestException", e.message
            )
        except CrossAccountNotAllowed as e:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#AccessDeniedException", e.message
            )

    def integration_responses(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]
        status_code = url_path_parts[9]

        try:
            if self.method == "GET":
                integration_response = self.backend.get_integration_response(
                    function_id, resource_id, method_type, status_code
                )
            elif self.method == "PUT":
                selection_pattern = self._get_param("selectionPattern")
                response_templates = self._get_param("responseTemplates")
                content_handling = self._get_param("contentHandling")
                integration_response = self.backend.create_integration_response(
                    function_id,
                    resource_id,
                    method_type,
                    status_code,
                    selection_pattern,
                    response_templates,
                    content_handling,
                )
            elif self.method == "DELETE":
                integration_response = self.backend.delete_integration_response(
                    function_id, resource_id, method_type, status_code
                )
            return 200, {}, json.dumps(integration_response)
        except BadRequestException as e:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#BadRequestException", e.message
            )

    def deployments(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        try:
            if self.method == "GET":
                deployments = self.backend.get_deployments(function_id)
                return 200, {}, json.dumps({"item": deployments})
            elif self.method == "POST":
                name = self._get_param("stageName")
                description = self._get_param("description", if_none="")
                stage_variables = self._get_param("variables", if_none={})
                deployment = self.backend.create_deployment(
                    function_id, name, description, stage_variables
                )
                return 200, {}, json.dumps(deployment)
        except BadRequestException as e:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#BadRequestException", e.message
            )

    def individual_deployment(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        deployment_id = url_path_parts[4]

        if self.method == "GET":
            deployment = self.backend.get_deployment(function_id, deployment_id)
        elif self.method == "DELETE":
            deployment = self.backend.delete_deployment(function_id, deployment_id)
        return 200, {}, json.dumps(deployment)

    def apikeys(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            try:
                apikey_response = self.backend.create_apikey(json.loads(self.body))
            except ApiKeyAlreadyExists as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )

            except ApiKeyValueMinLength as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )
            return 201, {}, json.dumps(apikey_response)

        elif self.method == "GET":
            include_values = self._get_bool_param("includeValues")
            apikeys_response = self.backend.get_apikeys(include_values=include_values)
            return 200, {}, json.dumps({"item": apikeys_response})

    def apikey_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        apikey = url_path_parts[2]

        status_code = 200
        if self.method == "GET":
            include_value = self._get_bool_param("includeValue")
            apikey_response = self.backend.get_apikey(
                apikey, include_value=include_value
            )
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            apikey_response = self.backend.update_apikey(apikey, patch_operations)
        elif self.method == "DELETE":
            apikey_response = self.backend.delete_apikey(apikey)
            status_code = 202

        return status_code, {}, json.dumps(apikey_response)

    def usage_plans(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            usage_plan_response = self.backend.create_usage_plan(json.loads(self.body))
        elif self.method == "GET":
            api_key_id = self.querystring.get("keyId", [None])[0]
            usage_plans_response = self.backend.get_usage_plans(api_key_id=api_key_id)
            return 200, {}, json.dumps({"item": usage_plans_response})
        return 200, {}, json.dumps(usage_plan_response)

    def usage_plan_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        usage_plan = url_path_parts[2]

        if self.method == "GET":
            try:
                usage_plan_response = self.backend.get_usage_plan(usage_plan)
            except (UsagePlanNotFoundException) as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )
        elif self.method == "DELETE":
            usage_plan_response = self.backend.delete_usage_plan(usage_plan)
        return 200, {}, json.dumps(usage_plan_response)

    def usage_plan_keys(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        usage_plan_id = url_path_parts[2]

        if self.method == "POST":
            try:
                usage_plan_response = self.backend.create_usage_plan_key(
                    usage_plan_id, json.loads(self.body)
                )
            except ApiKeyNotFoundException as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )
            return 201, {}, json.dumps(usage_plan_response)
        elif self.method == "GET":
            usage_plans_response = self.backend.get_usage_plan_keys(usage_plan_id)
            return 200, {}, json.dumps({"item": usage_plans_response})

    def usage_plan_key_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        usage_plan_id = url_path_parts[2]
        key_id = url_path_parts[4]

        if self.method == "GET":
            try:
                usage_plan_response = self.backend.get_usage_plan_key(
                    usage_plan_id, key_id
                )
            except (UsagePlanNotFoundException, ApiKeyNotFoundException) as error:
                return (
                    error.code,
                    {},
                    '{{"message":"{0}","code":"{1}"}}'.format(
                        error.message, error.error_type
                    ),
                )
        elif self.method == "DELETE":
            usage_plan_response = self.backend.delete_usage_plan_key(
                usage_plan_id, key_id
            )
        return 200, {}, json.dumps(usage_plan_response)

    def domain_names(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        try:
            if self.method == "GET":
                domain_names = self.backend.get_domain_names()
                return 200, {}, json.dumps({"item": domain_names})

            elif self.method == "POST":
                domain_name = self._get_param("domainName")
                certificate_name = self._get_param("certificateName")
                tags = self._get_param("tags")
                certificate_arn = self._get_param("certificateArn")
                certificate_body = self._get_param("certificateBody")
                certificate_private_key = self._get_param("certificatePrivateKey")
                certificate_chain = self._get_param("certificateChain")
                regional_certificate_name = self._get_param("regionalCertificateName")
                regional_certificate_arn = self._get_param("regionalCertificateArn")
                endpoint_configuration = self._get_param("endpointConfiguration")
                security_policy = self._get_param("securityPolicy")
                generate_cli_skeleton = self._get_param("generateCliSkeleton")
                domain_name_resp = self.backend.create_domain_name(
                    domain_name,
                    certificate_name,
                    tags,
                    certificate_arn,
                    certificate_body,
                    certificate_private_key,
                    certificate_chain,
                    regional_certificate_name,
                    regional_certificate_arn,
                    endpoint_configuration,
                    security_policy,
                    generate_cli_skeleton,
                )
                return 200, {}, json.dumps(domain_name_resp)

        except InvalidDomainName as error:
            return (
                error.code,
                {},
                '{{"message":"{0}","code":"{1}"}}'.format(
                    error.message, error.error_type
                ),
            )

    def domain_name_induvidual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        domain_name = url_path_parts[2]
        domain_names = {}
        try:
            if self.method == "GET":
                if domain_name is not None:
                    domain_names = self.backend.get_domain_name(domain_name)
            return 200, {}, json.dumps(domain_names)
        except DomainNameNotFound as error:
            return (
                error.code,
                {},
                '{{"message":"{0}","code":"{1}"}}'.format(
                    error.message, error.error_type
                ),
            )

    def models(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        rest_api_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        try:
            if self.method == "GET":
                models = self.backend.get_models(rest_api_id)
                return 200, {}, json.dumps({"item": models})

            elif self.method == "POST":
                name = self._get_param("name")
                description = self._get_param("description")
                schema = self._get_param("schema")
                content_type = self._get_param("contentType")
                cli_input_json = self._get_param("cliInputJson")
                generate_cli_skeleton = self._get_param("generateCliSkeleton")
                model = self.backend.create_model(
                    rest_api_id,
                    name,
                    content_type,
                    description,
                    schema,
                    cli_input_json,
                    generate_cli_skeleton,
                )

                return 200, {}, json.dumps(model)

        except (InvalidRestApiId, InvalidModelName, RestAPINotFound) as error:
            return (
                error.code,
                {},
                '{{"message":"{0}","code":"{1}"}}'.format(
                    error.message, error.error_type
                ),
            )

    def model_induvidual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        rest_api_id = url_path_parts[2]
        model_name = url_path_parts[4]
        model_info = {}
        try:
            if self.method == "GET":
                model_info = self.backend.get_model(rest_api_id, model_name)
            return 200, {}, json.dumps(model_info)
        except (
            ModelNotFound,
            RestAPINotFound,
            InvalidRestApiId,
            InvalidModelName,
        ) as error:
            return (
                error.code,
                {},
                '{{"message":"{0}","code":"{1}"}}'.format(
                    error.message, error.error_type
                ),
            )
