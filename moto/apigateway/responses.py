import json
from typing import Any, Dict, List
from urllib.parse import unquote

from moto.utilities.utils import merge_multiple_dicts
from moto.core.responses import BaseResponse, TYPE_RESPONSE
from .models import apigateway_backends, APIGatewayBackend
from .utils import deserialize_body
from .exceptions import InvalidRequestInput

API_KEY_SOURCES = ["AUTHORIZER", "HEADER"]
AUTHORIZER_TYPES = ["TOKEN", "REQUEST", "COGNITO_USER_POOLS"]
ENDPOINT_CONFIGURATION_TYPES = ["PRIVATE", "EDGE", "REGIONAL"]


class APIGatewayResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="apigateway")

    def error(self, type_: str, message: str, status: int = 400) -> TYPE_RESPONSE:
        headers = self.response_headers or {}
        headers["X-Amzn-Errortype"] = type_
        return (status, headers, json.dumps({"__type": type_, "message": message}))

    @property
    def backend(self) -> APIGatewayBackend:
        return apigateway_backends[self.current_account][self.region]

    def __validate_api_key_source(self, api_key_source: str) -> TYPE_RESPONSE:  # type: ignore[return]
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

    def __validate_endpoint_configuration(self, endpoint_configuration: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        if endpoint_configuration and "types" in endpoint_configuration:
            invalid_types = list(
                set(endpoint_configuration["types"]) - set(ENDPOINT_CONFIGURATION_TYPES)
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

    def restapis(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            apis = self.backend.list_apis()
            return 200, {}, json.dumps({"item": [api.to_dict() for api in apis]})
        elif self.method == "POST":
            api_doc = deserialize_body(self.body)
            if api_doc:
                fail_on_warnings = self._get_bool_param("failonwarnings") or False
                rest_api = self.backend.import_rest_api(api_doc, fail_on_warnings)

                return 200, {}, json.dumps(rest_api.to_dict())

            name = self._get_param("name")
            description = self._get_param("description")

            api_key_source = self._get_param("apiKeySource")
            endpoint_configuration = self._get_param("endpointConfiguration")
            tags = self._get_param("tags")
            policy = self._get_param("policy")
            minimum_compression_size = self._get_param("minimumCompressionSize")
            disable_execute_api_endpoint = self._get_param("disableExecuteApiEndpoint")

            # Param validation
            response = self.__validate_api_key_source(api_key_source)
            if response is not None:
                return response

            response = self.__validate_endpoint_configuration(endpoint_configuration)
            if response is not None:
                return response

            rest_api = self.backend.create_rest_api(
                name,
                description,
                api_key_source=api_key_source,
                endpoint_configuration=endpoint_configuration,
                tags=tags,
                policy=policy,
                minimum_compression_size=minimum_compression_size,
                disable_execute_api_endpoint=disable_execute_api_endpoint,
            )

            return 200, {}, json.dumps(rest_api.to_dict())

    def __validte_rest_patch_operations(self, patch_operations: List[Dict[str, str]]) -> TYPE_RESPONSE:  # type: ignore[return]
        for op in patch_operations:
            path = op["path"]
            if "apiKeySource" in path:
                value = op["value"]
                return self.__validate_api_key_source(value)

    def restapis_individual(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == "GET":
            rest_api = self.backend.get_rest_api(function_id)
        elif self.method == "DELETE":
            rest_api = self.backend.delete_rest_api(function_id)
        elif self.method == "PUT":
            mode = self._get_param("mode", "merge")
            fail_on_warnings = self._get_bool_param("failonwarnings") or False

            api_doc = deserialize_body(self.body)

            rest_api = self.backend.put_rest_api(
                function_id, api_doc, mode=mode, fail_on_warnings=fail_on_warnings
            )
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            response = self.__validte_rest_patch_operations(patch_operations)
            if response is not None:
                return response
            rest_api = self.backend.update_rest_api(function_id, patch_operations)

        return 200, {}, json.dumps(rest_api.to_dict())

    def resources(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == "GET":
            resources = self.backend.get_resources(function_id)
            return (
                200,
                {},
                json.dumps({"item": [resource.to_dict() for resource in resources]}),
            )

    def gateway_response(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self.put_gateway_response()
        elif request.method == "GET":
            return self.get_gateway_response()
        elif request.method == "DELETE":
            return self.delete_gateway_response()

    def gateway_responses(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_gateway_responses()

    def resource_individual(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]
        resource_id = self.path.split("/")[-1]

        if self.method == "GET":
            resource = self.backend.get_resource(function_id, resource_id)
            return 200, {}, json.dumps(resource.to_dict())
        elif self.method == "POST":
            path_part = self._get_param("pathPart")
            resource = self.backend.create_resource(function_id, resource_id, path_part)
            return 201, {}, json.dumps(resource.to_dict())
        elif self.method == "DELETE":
            resource = self.backend.delete_resource(function_id, resource_id)
            return 202, {}, json.dumps(resource.to_dict())

    def resource_methods(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]

        if self.method == "GET":
            method = self.backend.get_method(function_id, resource_id, method_type)
            return 200, {}, json.dumps(method.to_json())
        elif self.method == "PUT":
            authorization_type = self._get_param("authorizationType")
            api_key_required = self._get_param("apiKeyRequired")
            request_models = self._get_param("requestModels")
            operation_name = self._get_param("operationName")
            authorizer_id = self._get_param("authorizerId")
            authorization_scopes = self._get_param("authorizationScopes")
            request_validator_id = self._get_param("requestValidatorId")
            request_parameters = self._get_param("requestParameters")
            method = self.backend.put_method(
                function_id,
                resource_id,
                method_type,
                authorization_type,
                api_key_required,
                request_models=request_models,
                request_parameters=request_parameters,
                operation_name=operation_name,
                authorizer_id=authorizer_id,
                authorization_scopes=authorization_scopes,
                request_validator_id=request_validator_id,
            )
            return 201, {}, json.dumps(method.to_json())

        elif self.method == "DELETE":
            self.backend.delete_method(function_id, resource_id, method_type)
            return 204, {}, ""

        return 200, {}, ""

    def resource_method_responses(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
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
            return 200, {}, json.dumps(method_response.to_json())  # type: ignore[union-attr]
        elif self.method == "PUT":
            response_models = self._get_param("responseModels")
            response_parameters = self._get_param("responseParameters")
            method_response = self.backend.put_method_response(
                function_id,
                resource_id,
                method_type,
                response_code,
                response_models,
                response_parameters,
            )
            return 201, {}, json.dumps(method_response.to_json())
        elif self.method == "DELETE":
            method_response = self.backend.delete_method_response(
                function_id, resource_id, method_type, response_code
            )
            return 204, {}, json.dumps(method_response.to_json())  # type: ignore[union-attr]
        raise Exception(f'Unexpected HTTP method "{self.method}"')

    def restapis_authorizers(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
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
                restapi_id=restapi_id,
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
            return 201, {}, json.dumps(authorizer_response.to_json())
        elif self.method == "GET":
            authorizers = self.backend.get_authorizers(restapi_id)
            return 200, {}, json.dumps({"item": [a.to_json() for a in authorizers]})

    def request_validators(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        restapi_id = url_path_parts[2]

        if self.method == "GET":
            validators = self.backend.get_request_validators(restapi_id)
            res = json.dumps(
                {"item": [validator.to_dict() for validator in validators]}
            )
            return 200, {}, res
        if self.method == "POST":
            name = self._get_param("name")
            body = self._get_bool_param("validateRequestBody")
            params = self._get_bool_param("validateRequestParameters")
            validator = self.backend.create_request_validator(
                restapi_id, name, body, params
            )
            return 201, {}, json.dumps(validator.to_dict())

    def request_validator_individual(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        restapi_id = url_path_parts[2]
        validator_id = url_path_parts[4]

        if self.method == "GET":
            validator = self.backend.get_request_validator(restapi_id, validator_id)
            return 200, {}, json.dumps(validator.to_dict())
        if self.method == "DELETE":
            self.backend.delete_request_validator(restapi_id, validator_id)
            return 202, {}, ""
        if self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            validator = self.backend.update_request_validator(
                restapi_id, validator_id, patch_operations
            )
            return 200, {}, json.dumps(validator.to_dict())

    def authorizers(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        restapi_id = url_path_parts[2]
        authorizer_id = url_path_parts[4]

        if self.method == "GET":
            authorizer_response = self.backend.get_authorizer(restapi_id, authorizer_id)
            return 200, {}, json.dumps(authorizer_response.to_json())
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            authorizer_response = self.backend.update_authorizer(
                restapi_id, authorizer_id, patch_operations
            )
            return 200, {}, json.dumps(authorizer_response.to_json())
        elif self.method == "DELETE":
            self.backend.delete_authorizer(restapi_id, authorizer_id)
            return 202, {}, "{}"

    def restapis_stages(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
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
            tags = self._get_param("tags")
            tracing_enabled = self._get_param("tracingEnabled")

            stage_response = self.backend.create_stage(
                function_id,
                stage_name,
                deployment_id,
                variables=stage_variables,
                description=description,
                cacheClusterEnabled=cacheClusterEnabled,
                cacheClusterSize=cacheClusterSize,
                tags=tags,
                tracing_enabled=tracing_enabled,
            )
            return 201, {}, json.dumps(stage_response.to_json())
        elif self.method == "GET":
            stages = self.backend.get_stages(function_id)
            return 200, {}, json.dumps({"item": [s.to_json() for s in stages]})

    def restapis_stages_tags(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[4]
        stage_name = url_path_parts[6]
        if self.method == "PUT":
            tags = self._get_param("tags")
            if tags:
                stage = self.backend.get_stage(function_id, stage_name)
                stage.tags = merge_multiple_dicts(stage.tags or {}, tags)
            return 200, {}, json.dumps({"item": tags})
        if self.method == "DELETE":
            stage = self.backend.get_stage(function_id, stage_name)
            for tag in (stage.tags or {}).copy():
                if tag in (self.querystring.get("tagKeys") or {}):
                    stage.tags.pop(tag, None)  # type: ignore[union-attr]
            return 200, {}, json.dumps({"item": ""})

    def stages(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        stage_name = url_path_parts[4]

        if self.method == "GET":
            stage_response = self.backend.get_stage(function_id, stage_name)
            return 200, {}, json.dumps(stage_response.to_json())
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            stage_response = self.backend.update_stage(
                function_id, stage_name, patch_operations
            )
            return 200, {}, json.dumps(stage_response.to_json())
        elif self.method == "DELETE":
            self.backend.delete_stage(function_id, stage_name)
            return 202, {}, "{}"

    def export(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        rest_api_id = url_path_parts[-5]
        export_type = url_path_parts[-1]

        body = self.backend.export_api(rest_api_id, export_type)

        now = body["info"]["version"]
        filename = f"swagger_{now}Z.json"
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        return 200, headers, json.dumps(body).encode("utf-8")

    def integrations(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]

        if self.method == "GET":
            integration_response = self.backend.get_integration(
                function_id, resource_id, method_type
            )
            if integration_response:
                return 200, {}, json.dumps(integration_response.to_json())
            return 200, {}, "{}"
        elif self.method == "PUT":
            integration_type = self._get_param("type")
            uri = self._get_param("uri")
            credentials = self._get_param("credentials")
            request_templates = self._get_param("requestTemplates")
            passthrough_behavior = self._get_param("passthroughBehavior")
            tls_config = self._get_param("tlsConfig")
            cache_namespace = self._get_param("cacheNamespace")
            timeout_in_millis = self._get_param("timeoutInMillis")
            request_parameters = self._get_param("requestParameters")
            content_handling = self._get_param("contentHandling")
            connection_type = self._get_param("connectionType")
            self.backend.get_method(function_id, resource_id, method_type)

            integration_http_method = self._get_param(
                "httpMethod"
            )  # default removed because it's a required parameter

            integration_response = self.backend.put_integration(
                function_id,
                resource_id,
                method_type,
                integration_type,
                uri,
                credentials=credentials,
                integration_method=integration_http_method,
                request_templates=request_templates,
                passthrough_behavior=passthrough_behavior,
                tls_config=tls_config,
                cache_namespace=cache_namespace,
                timeout_in_millis=timeout_in_millis,
                request_parameters=request_parameters,
                content_handling=content_handling,
                connection_type=connection_type,
            )
            return 201, {}, json.dumps(integration_response.to_json())
        elif self.method == "DELETE":
            integration_response = self.backend.delete_integration(
                function_id, resource_id, method_type
            )
            return 204, {}, json.dumps(integration_response.to_json())

    def integration_responses(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        resource_id = url_path_parts[4]
        method_type = url_path_parts[6]
        status_code = url_path_parts[9]

        if self.method == "GET":
            integration_response = self.backend.get_integration_response(
                function_id, resource_id, method_type, status_code
            )
            return 200, {}, json.dumps(integration_response.to_json())
        elif self.method == "PUT":
            if not self.body:
                raise InvalidRequestInput()

            selection_pattern = self._get_param("selectionPattern")
            response_templates = self._get_param("responseTemplates")
            response_parameters = self._get_param("responseParameters")
            content_handling = self._get_param("contentHandling")
            integration_response = self.backend.put_integration_response(
                function_id,
                resource_id,
                method_type,
                status_code,
                selection_pattern,
                response_templates,
                response_parameters,
                content_handling,
            )
            return 201, {}, json.dumps(integration_response.to_json())
        elif self.method == "DELETE":
            integration_response = self.backend.delete_integration_response(
                function_id, resource_id, method_type, status_code
            )
            return 204, {}, json.dumps(integration_response.to_json())

    def deployments(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        function_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == "GET":
            deployments = self.backend.get_deployments(function_id)
            return 200, {}, json.dumps({"item": [d.to_json() for d in deployments]})
        elif self.method == "POST":
            name = self._get_param("stageName")
            description = self._get_param("description")
            stage_variables = self._get_param("variables", if_none={})
            deployment = self.backend.create_deployment(
                function_id, name, description, stage_variables
            )
            return 201, {}, json.dumps(deployment.to_json())

    def individual_deployment(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        function_id = url_path_parts[2]
        deployment_id = url_path_parts[4]

        if self.method == "GET":
            deployment = self.backend.get_deployment(function_id, deployment_id)
            return 200, {}, json.dumps(deployment.to_json())
        elif self.method == "DELETE":
            deployment = self.backend.delete_deployment(function_id, deployment_id)
            return 202, {}, json.dumps(deployment.to_json())

    def apikeys(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            apikey_response = self.backend.create_api_key(json.loads(self.body))
            return 201, {}, json.dumps(apikey_response.to_json())

        elif self.method == "GET":
            include_values = self._get_bool_param("includeValues") or False
            apikeys_response = self.backend.get_api_keys()
            resp = [a.to_json() for a in apikeys_response]
            if not include_values:
                for key in resp:
                    key.pop("value")
            return 200, {}, json.dumps({"item": resp})

    def apikey_individual(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        apikey = url_path_parts[2]

        if self.method == "GET":
            include_value = self._get_bool_param("includeValue") or False
            apikey_resp = self.backend.get_api_key(apikey).to_json()
            if not include_value:
                apikey_resp.pop("value")
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            apikey_resp = self.backend.update_api_key(
                apikey, patch_operations
            ).to_json()
        elif self.method == "DELETE":
            self.backend.delete_api_key(apikey)
            return 202, {}, "{}"

        return 200, {}, json.dumps(apikey_resp)

    def usage_plans(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if self.method == "POST":
            usage_plan_response = self.backend.create_usage_plan(json.loads(self.body))
            return 201, {}, json.dumps(usage_plan_response.to_json())
        elif self.method == "GET":
            api_key_id = self.querystring.get("keyId", [None])[0]
            usage_plans_response = self.backend.get_usage_plans(api_key_id=api_key_id)
            return (
                200,
                {},
                json.dumps({"item": [u.to_json() for u in usage_plans_response]}),
            )

    def usage_plan_individual(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        usage_plan = url_path_parts[2]

        if self.method == "GET":
            usage_plan_response = self.backend.get_usage_plan(usage_plan)
            return 200, {}, json.dumps(usage_plan_response.to_json())
        elif self.method == "DELETE":
            self.backend.delete_usage_plan(usage_plan)
            return 202, {}, "{}"
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            usage_plan_response = self.backend.update_usage_plan(
                usage_plan, patch_operations
            )
            return 200, {}, json.dumps(usage_plan_response.to_json())

    def usage_plan_keys(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        usage_plan_id = url_path_parts[2]

        if self.method == "POST":
            usage_plan_response = self.backend.create_usage_plan_key(
                usage_plan_id, json.loads(self.body)
            )
            return 201, {}, json.dumps(usage_plan_response.to_json())
        elif self.method == "GET":
            usage_plans_response = self.backend.get_usage_plan_keys(usage_plan_id)
            return (
                200,
                {},
                json.dumps({"item": [u.to_json() for u in usage_plans_response]}),
            )

    def usage_plan_key_individual(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        usage_plan_id = url_path_parts[2]
        key_id = url_path_parts[4]

        if self.method == "GET":
            usage_plan_response = self.backend.get_usage_plan_key(usage_plan_id, key_id)
            return 200, {}, json.dumps(usage_plan_response.to_json())
        elif self.method == "DELETE":
            self.backend.delete_usage_plan_key(usage_plan_id, key_id)
            return 202, {}, "{}"

    def domain_names(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            domain_names = self.backend.get_domain_names()
            return 200, {}, json.dumps({"item": [d.to_json() for d in domain_names]})

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
            )
            return 201, {}, json.dumps(domain_name_resp.to_json())

    def domain_name_induvidual(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        domain_name = url_path_parts[2]

        if self.method == "GET":
            if domain_name is not None:
                domain_names = self.backend.get_domain_name(domain_name)
                return 200, {}, json.dumps(domain_names.to_json())
            return 200, {}, "{}"
        elif self.method == "DELETE":
            if domain_name is not None:
                self.backend.delete_domain_name(domain_name)
            return 202, {}, json.dumps({})
        else:
            msg = f'Method "{self.method}" for API GW domain names not implemented'
            return 404, {}, json.dumps({"error": msg})

    def models(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        rest_api_id = self.path.replace("/restapis/", "", 1).split("/")[0]

        if self.method == "GET":
            models = self.backend.get_models(rest_api_id)
            return 200, {}, json.dumps({"item": [m.to_json() for m in models]})

        elif self.method == "POST":
            name = self._get_param("name")
            description = self._get_param("description")
            schema = self._get_param("schema")
            content_type = self._get_param("contentType")
            model = self.backend.create_model(
                rest_api_id,
                name,
                content_type,
                description,
                schema,
            )
            return 201, {}, json.dumps(model.to_json())

    def model_induvidual(
        self, request: Any, full_url: str, headers: Dict[str, str]
    ) -> TYPE_RESPONSE:
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        rest_api_id = url_path_parts[2]
        model_name = url_path_parts[4]

        if self.method == "GET":
            model_info = self.backend.get_model(rest_api_id, model_name)
            return 200, {}, json.dumps(model_info.to_json())
        return 200, {}, "{}"

    def base_path_mappings(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        domain_name = url_path_parts[2]

        if self.method == "GET":
            base_path_mappings = self.backend.get_base_path_mappings(domain_name)
            return (
                200,
                {},
                json.dumps({"item": [m.to_json() for m in base_path_mappings]}),
            )
        elif self.method == "POST":
            base_path = self._get_param("basePath")
            rest_api_id = self._get_param("restApiId")
            stage = self._get_param("stage")

            base_path_mapping_resp = self.backend.create_base_path_mapping(
                domain_name, rest_api_id, base_path, stage
            )
            return 201, {}, json.dumps(base_path_mapping_resp.to_json())

    def base_path_mapping_individual(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]

        self.setup_class(request, full_url, headers)

        url_path_parts = self.path.split("/")
        domain_name = url_path_parts[2]
        base_path = unquote(url_path_parts[4])

        if self.method == "GET":
            base_path_mapping = self.backend.get_base_path_mapping(
                domain_name, base_path
            )
            return 200, {}, json.dumps(base_path_mapping.to_json())
        elif self.method == "DELETE":
            self.backend.delete_base_path_mapping(domain_name, base_path)
            return 202, {}, ""
        elif self.method == "PATCH":
            patch_operations = self._get_param("patchOperations")
            base_path_mapping = self.backend.update_base_path_mapping(
                domain_name, base_path, patch_operations
            )
            return 200, {}, json.dumps(base_path_mapping.to_json())

    def vpc_link(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        url_path_parts = self.path.split("/")
        vpc_link_id = url_path_parts[-1]

        if self.method == "DELETE":
            self.backend.delete_vpc_link(vpc_link_id=vpc_link_id)
            return 202, {}, "{}"
        if self.method == "GET":
            vpc_link = self.backend.get_vpc_link(vpc_link_id=vpc_link_id)
            return 200, {}, json.dumps(vpc_link.to_json())

    def vpc_links(self, request: Any, full_url: str, headers: Dict[str, str]) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            vpc_links = self.backend.get_vpc_links()
            return 200, {}, json.dumps({"item": [v.to_json() for v in vpc_links]})
        if self.method == "POST":
            name = self._get_param("name")
            description = self._get_param("description")
            target_arns = self._get_param("targetArns")
            tags = self._get_param("tags")
            vpc_link = self.backend.create_vpc_link(
                name=name, description=description, target_arns=target_arns, tags=tags
            )
            return 202, {}, json.dumps(vpc_link.to_json())

    def put_gateway_response(self) -> TYPE_RESPONSE:
        rest_api_id = self.path.split("/")[-3]
        response_type = self.path.split("/")[-1]
        params = json.loads(self.body)
        status_code = params.get("statusCode")
        response_parameters = params.get("responseParameters")
        response_templates = params.get("responseTemplates")
        response = self.backend.put_gateway_response(
            rest_api_id=rest_api_id,
            response_type=response_type,
            status_code=status_code,
            response_parameters=response_parameters,
            response_templates=response_templates,
        )
        return 201, {}, json.dumps(response.to_json())

    def get_gateway_response(self) -> TYPE_RESPONSE:
        rest_api_id = self.path.split("/")[-3]
        response_type = self.path.split("/")[-1]
        response = self.backend.get_gateway_response(
            rest_api_id=rest_api_id, response_type=response_type
        )
        return 200, {}, json.dumps(response.to_json())

    def get_gateway_responses(self) -> TYPE_RESPONSE:
        rest_api_id = self.path.split("/")[-2]
        responses = self.backend.get_gateway_responses(rest_api_id=rest_api_id)
        return 200, {}, json.dumps(dict(item=[gw.to_json() for gw in responses]))

    def delete_gateway_response(self) -> TYPE_RESPONSE:
        rest_api_id = self.path.split("/")[-3]
        response_type = self.path.split("/")[-1]
        self.backend.delete_gateway_response(
            rest_api_id=rest_api_id, response_type=response_type
        )
        return 202, {}, json.dumps(dict())
