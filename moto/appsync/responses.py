"""Handles incoming appsync requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from urllib.parse import unquote
from .models import appsync_backends


class AppSyncResponse(BaseResponse):
    """Handler for AppSync requests and responses."""

    def __init__(self):
        super().__init__(service_name="appsync")

    @property
    def appsync_backend(self):
        """Return backend instance specific for this region."""
        return appsync_backends[self.current_account][self.region]

    def graph_ql(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_graphql_api()
        if request.method == "GET":
            return self.list_graphql_apis()

    def graph_ql_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_graphql_api()
        if request.method == "DELETE":
            return self.delete_graphql_api()
        if request.method == "POST":
            return self.update_graphql_api()

    def api_key(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_api_key()
        if request.method == "GET":
            return self.list_api_keys()

    def schemacreation(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.start_schema_creation()
        if request.method == "GET":
            return self.get_schema_creation_status()

    def api_key_individual(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.delete_api_key()
        if request.method == "POST":
            return self.update_api_key()

    def tags(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.tag_resource()
        if request.method == "DELETE":
            return self.untag_resource()
        if request.method == "GET":
            return self.list_tags_for_resource()

    def types(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_type()

    def create_graphql_api(self):
        params = json.loads(self.body)
        name = params.get("name")
        log_config = params.get("logConfig")
        authentication_type = params.get("authenticationType")
        user_pool_config = params.get("userPoolConfig")
        open_id_connect_config = params.get("openIDConnectConfig")
        tags = params.get("tags")
        additional_authentication_providers = params.get(
            "additionalAuthenticationProviders"
        )
        xray_enabled = params.get("xrayEnabled", False)
        lambda_authorizer_config = params.get("lambdaAuthorizerConfig")
        graphql_api = self.appsync_backend.create_graphql_api(
            name=name,
            log_config=log_config,
            authentication_type=authentication_type,
            user_pool_config=user_pool_config,
            open_id_connect_config=open_id_connect_config,
            additional_authentication_providers=additional_authentication_providers,
            xray_enabled=xray_enabled,
            lambda_authorizer_config=lambda_authorizer_config,
            tags=tags,
        )
        response = graphql_api.to_json()
        response["tags"] = self.appsync_backend.list_tags_for_resource(graphql_api.arn)
        return 200, {}, json.dumps(dict(graphqlApi=response))

    def get_graphql_api(self):
        api_id = self.path.split("/")[-1]

        graphql_api = self.appsync_backend.get_graphql_api(api_id=api_id)
        response = graphql_api.to_json()
        response["tags"] = self.appsync_backend.list_tags_for_resource(graphql_api.arn)
        return 200, {}, json.dumps(dict(graphqlApi=response))

    def delete_graphql_api(self):
        api_id = self.path.split("/")[-1]
        self.appsync_backend.delete_graphql_api(api_id=api_id)
        return 200, {}, json.dumps(dict())

    def update_graphql_api(self):
        api_id = self.path.split("/")[-1]

        params = json.loads(self.body)
        name = params.get("name")
        log_config = params.get("logConfig")
        authentication_type = params.get("authenticationType")
        user_pool_config = params.get("userPoolConfig")
        open_id_connect_config = params.get("openIDConnectConfig")
        additional_authentication_providers = params.get(
            "additionalAuthenticationProviders"
        )
        xray_enabled = params.get("xrayEnabled", False)
        lambda_authorizer_config = params.get("lambdaAuthorizerConfig")

        api = self.appsync_backend.update_graphql_api(
            api_id=api_id,
            name=name,
            log_config=log_config,
            authentication_type=authentication_type,
            user_pool_config=user_pool_config,
            open_id_connect_config=open_id_connect_config,
            additional_authentication_providers=additional_authentication_providers,
            xray_enabled=xray_enabled,
            lambda_authorizer_config=lambda_authorizer_config,
        )
        return 200, {}, json.dumps(dict(graphqlApi=api.to_json()))

    def list_graphql_apis(self):
        graphql_apis = self.appsync_backend.list_graphql_apis()
        return (
            200,
            {},
            json.dumps(dict(graphqlApis=[api.to_json() for api in graphql_apis])),
        )

    def create_api_key(self):
        params = json.loads(self.body)
        # /v1/apis/[api_id]/apikeys
        api_id = self.path.split("/")[-2]
        description = params.get("description")
        expires = params.get("expires")
        api_key = self.appsync_backend.create_api_key(
            api_id=api_id, description=description, expires=expires
        )
        return 200, {}, json.dumps(dict(apiKey=api_key.to_json()))

    def delete_api_key(self):
        api_id = self.path.split("/")[-3]
        api_key_id = self.path.split("/")[-1]
        self.appsync_backend.delete_api_key(api_id=api_id, api_key_id=api_key_id)
        return 200, {}, json.dumps(dict())

    def list_api_keys(self):
        # /v1/apis/[api_id]/apikeys
        api_id = self.path.split("/")[-2]
        api_keys = self.appsync_backend.list_api_keys(api_id=api_id)
        return 200, {}, json.dumps(dict(apiKeys=[key.to_json() for key in api_keys]))

    def update_api_key(self):
        api_id = self.path.split("/")[-3]
        api_key_id = self.path.split("/")[-1]
        params = json.loads(self.body)
        description = params.get("description")
        expires = params.get("expires")
        api_key = self.appsync_backend.update_api_key(
            api_id=api_id,
            api_key_id=api_key_id,
            description=description,
            expires=expires,
        )
        return 200, {}, json.dumps(dict(apiKey=api_key.to_json()))

    def start_schema_creation(self):
        params = json.loads(self.body)
        api_id = self.path.split("/")[-2]
        definition = params.get("definition")
        status = self.appsync_backend.start_schema_creation(
            api_id=api_id, definition=definition
        )
        return 200, {}, json.dumps({"status": status})

    def get_schema_creation_status(self):
        api_id = self.path.split("/")[-2]
        status, details = self.appsync_backend.get_schema_creation_status(api_id=api_id)
        return 200, {}, json.dumps(dict(status=status, details=details))

    def tag_resource(self):
        resource_arn = self._extract_arn_from_path()
        params = json.loads(self.body)
        tags = params.get("tags")
        self.appsync_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return 200, {}, json.dumps(dict())

    def untag_resource(self):
        resource_arn = self._extract_arn_from_path()
        tag_keys = self.querystring.get("tagKeys", [])
        self.appsync_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return 200, {}, json.dumps(dict())

    def list_tags_for_resource(self):
        resource_arn = self._extract_arn_from_path()
        tags = self.appsync_backend.list_tags_for_resource(resource_arn=resource_arn)
        return 200, {}, json.dumps(dict(tags=tags))

    def _extract_arn_from_path(self):
        # /v1/tags/arn_that_may_contain_a_slash
        path = unquote(self.path)
        return "/".join(path.split("/")[3:])

    def get_type(self):
        api_id = unquote(self.path.split("/")[-3])
        type_name = self.path.split("/")[-1]
        type_format = self.querystring.get("format")[0]
        graphql_type = self.appsync_backend.get_type(
            api_id=api_id, type_name=type_name, type_format=type_format
        )
        return 200, {}, json.dumps(dict(type=graphql_type))
