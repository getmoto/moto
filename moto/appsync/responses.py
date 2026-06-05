"""Handles incoming appsync requests, invokes methods, returns responses."""

import json
import re
from typing import Any
from uuid import uuid4

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from moto.core.utils import unix_time

from .exceptions import ApiKeyValidityOutOfBoundsException, AWSValidationException
from .models import AppSyncBackend, appsync_backends


class AppSyncResponse(BaseResponse):
    """Handler for AppSync requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="appsync")
        self.automated_parameter_parsing = True

    @staticmethod
    def dns_event_response(request: Any, url: str, headers: Any) -> TYPE_RESPONSE:
        data = json.loads(request.data.decode("utf-8"))

        response: dict[str, list[Any]] = {"failed": [], "successful": []}
        for idx in range(len(data.get("events", []))):
            response["successful"].append({"identifier": str(uuid4()), "index": idx})

        return 200, {}, json.dumps(response).encode("utf-8")

    @property
    def appsync_backend(self) -> AppSyncBackend:
        """Return backend instance specific for this region."""
        return appsync_backends[self.current_account][self.region]

    def create_graphql_api(self) -> str:
        name = self._get_param("name")
        log_config = self._get_param("logConfig")
        authentication_type = self._get_param("authenticationType")
        user_pool_config = self._get_param("userPoolConfig")
        open_id_connect_config = self._get_param("openIDConnectConfig")
        tags = self._get_param("tags")
        additional_authentication_providers = self._get_param(
            "additionalAuthenticationProviders"
        )
        xray_enabled = self._get_param("xrayEnabled", False)
        lambda_authorizer_config = self._get_param("lambdaAuthorizerConfig")
        visibility = self._get_param("visibility")
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
            visibility=visibility,
        )
        response = graphql_api.to_json()
        response["tags"] = self.appsync_backend.list_tags_for_resource(graphql_api.arn)
        return json.dumps({"graphqlApi": response})

    def get_graphql_api(self) -> str:
        api_id = self._get_param("apiId")

        graphql_api = self.appsync_backend.get_graphql_api(api_id=api_id)
        response = graphql_api.to_json()
        response["tags"] = self.appsync_backend.list_tags_for_resource(graphql_api.arn)
        return json.dumps({"graphqlApi": response})

    def delete_graphql_api(self) -> str:
        api_id = self._get_param("apiId")
        self.appsync_backend.delete_graphql_api(api_id=api_id)
        return "{}"

    def update_graphql_api(self) -> str:
        api_id = self._get_param("apiId")

        name = self._get_param("name")
        log_config = self._get_param("logConfig")
        authentication_type = self._get_param("authenticationType")
        user_pool_config = self._get_param("userPoolConfig")
        open_id_connect_config = self._get_param("openIDConnectConfig")
        additional_authentication_providers = self._get_param(
            "additionalAuthenticationProviders"
        )
        xray_enabled = self._get_param("xrayEnabled", False)
        lambda_authorizer_config = self._get_param("lambdaAuthorizerConfig")

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
        return json.dumps({"graphqlApi": api.to_json()})

    def list_graphql_apis(self) -> str:
        graphql_apis = self.appsync_backend.list_graphql_apis()
        return json.dumps({"graphqlApis": [api.to_json() for api in graphql_apis]})

    def create_api_key(self) -> str:
        api_id = self._get_param("apiId")
        description = self._get_param("description")
        expires = self._get_param("expires")

        if expires:
            current_time = int(unix_time())
            min_validity = current_time + 86400  # 1 day in seconds
            if expires < min_validity:
                raise ApiKeyValidityOutOfBoundsException(
                    "API key must be valid for a minimum of 1 days."
                )

        api_key = self.appsync_backend.create_api_key(
            api_id=api_id, description=description, expires=expires
        )
        return json.dumps({"apiKey": api_key.to_json()})

    def delete_api_key(self) -> str:
        api_id = self._get_param("apiId")
        api_key_id = self._get_param("id")
        self.appsync_backend.delete_api_key(api_id=api_id, api_key_id=api_key_id)
        return "{}"

    def list_api_keys(self) -> str:
        api_id = self._get_param("apiId")
        api_keys = self.appsync_backend.list_api_keys(api_id=api_id)
        return json.dumps({"apiKeys": [key.to_json() for key in api_keys]})

    def update_api_key(self) -> str:
        api_id = self._get_param("apiId")
        api_key_id = self._get_param("id")
        description = self._get_param("description")
        expires = self._get_param("expires")

        # Validate that API key expires at least 1 day from now
        if expires:
            current_time = int(unix_time())
            min_validity = current_time + 86400  # 1 day in seconds
            if expires < min_validity:
                raise ApiKeyValidityOutOfBoundsException(
                    "API key must be valid for a minimum of 1 days."
                )

        api_key = self.appsync_backend.update_api_key(
            api_id=api_id,
            api_key_id=api_key_id,
            description=description,
            expires=expires,
        )
        return json.dumps({"apiKey": api_key.to_json()})

    def start_schema_creation(self) -> str:
        api_id = self._get_param("apiId")
        definition = self._get_param("definition")
        status = self.appsync_backend.start_schema_creation(
            api_id=api_id, definition=definition
        )
        return json.dumps({"status": status})

    def get_schema_creation_status(self) -> str:
        api_id = self._get_param("apiId")
        status, details = self.appsync_backend.get_schema_creation_status(api_id=api_id)
        return json.dumps({"status": status, "details": details})

    def tag_resource(self) -> str:
        resource_arn = self._get_param("resourceArn")
        tags = self._get_param("tags")
        self.appsync_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return "{}"

    def untag_resource(self) -> str:
        resource_arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])
        self.appsync_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return "{}"

    def list_tags_for_resource(self) -> str:
        resource_arn = self._get_param("resourceArn")
        tags = self.appsync_backend.list_tags_for_resource(resource_arn=resource_arn)
        return json.dumps({"tags": tags})

    def get_type(self) -> str:
        api_id = self._get_param("apiId")
        type_name = self._get_param("typeName")
        type_format = self._get_param("format")
        graphql_type = self.appsync_backend.get_type(
            api_id=api_id, type_name=type_name, type_format=type_format
        )
        return json.dumps({"type": graphql_type})

    def get_introspection_schema(self) -> str:
        api_id = self._get_param("apiId")
        format_ = self._get_param("format")
        include_directives = self._get_bool_param("includeDirectives", True)
        graphql_schema = self.appsync_backend.get_graphql_schema(api_id=api_id)

        schema = graphql_schema.get_introspection_schema(
            format_=format_, include_directives=include_directives
        )
        return schema

    def get_api_cache(self) -> str:
        api_id = self._get_param("apiId")
        api_cache = self.appsync_backend.get_api_cache(
            api_id=api_id,
        )
        return json.dumps({"apiCache": api_cache.to_json()})

    def delete_api_cache(self) -> str:
        api_id = self._get_param("apiId")
        self.appsync_backend.delete_api_cache(
            api_id=api_id,
        )
        return "{}"

    def create_api_cache(self) -> str:
        api_id = self._get_param("apiId")
        ttl = self._get_param("ttl")
        transit_encryption_enabled = self._get_param("transitEncryptionEnabled")
        at_rest_encryption_enabled = self._get_param("atRestEncryptionEnabled")
        api_caching_behavior = self._get_param("apiCachingBehavior")
        type = self._get_param("type")
        health_metrics_config = self._get_param("healthMetricsConfig")
        api_cache = self.appsync_backend.create_api_cache(
            api_id=api_id,
            ttl=ttl,
            transit_encryption_enabled=transit_encryption_enabled,
            at_rest_encryption_enabled=at_rest_encryption_enabled,
            api_caching_behavior=api_caching_behavior,
            type=type,
            health_metrics_config=health_metrics_config,
        )
        return json.dumps({"apiCache": api_cache.to_json()})

    def update_api_cache(self) -> str:
        api_id = self._get_param("apiId")
        ttl = self._get_param("ttl")
        api_caching_behavior = self._get_param("apiCachingBehavior")
        type = self._get_param("type")
        health_metrics_config = self._get_param("healthMetricsConfig")
        api_cache = self.appsync_backend.update_api_cache(
            api_id=api_id,
            ttl=ttl,
            api_caching_behavior=api_caching_behavior,
            type=type,
            health_metrics_config=health_metrics_config,
        )
        return json.dumps({"apiCache": api_cache.to_json()})

    def flush_api_cache(self) -> str:
        api_id = self._get_param("apiId")
        self.appsync_backend.flush_api_cache(
            api_id=api_id,
        )
        return "{}"

    def create_api(self) -> str:
        name = self._get_param("name")

        if name:
            pattern = r"^[A-Za-z0-9_\-\ ]+$"
            if not re.match(pattern, name):
                raise AWSValidationException(
                    "1 validation error detected: "
                    "Value at 'name' failed to satisfy constraint: "
                    "Member must satisfy regular expression pattern: "
                    "[A-Za-z0-9_\\-\\ ]+"
                )

        owner_contact = self._get_param("ownerContact")
        tags = self._get_param("tags", {})
        event_config = self._get_param("eventConfig")

        api = self.appsync_backend.create_api(
            name=name,
            owner_contact=owner_contact,
            tags=tags,
            event_config=event_config,
        )

        response = api.to_json()
        return json.dumps({"api": response})

    def list_apis(self) -> str:
        apis = self.appsync_backend.list_apis()
        return json.dumps({"apis": [api.to_json() for api in apis]})

    def delete_api(self) -> str:
        api_id = self._get_param("apiId")
        self.appsync_backend.delete_api(api_id=api_id)
        return "{}"

    def create_channel_namespace(self) -> str:
        api_id = self._get_param("apiId")
        name = self._get_param("name")

        if name:
            pattern = r"^[A-Za-z0-9](?:[A-Za-z0-9\-]{0,48}[A-Za-z0-9])?$"
            if not re.match(pattern, name):
                raise AWSValidationException(
                    "1 validation error detected: "
                    "Value at 'name' failed to satisfy constraint: "
                    "Member must satisfy regular expression pattern: "
                    "([A-Za-z0-9](?:[A-Za-z0-9\\-]{0,48}[A-Za-z0-9])?)"
                )

        subscribe_auth_modes = self._get_param("subscribeAuthModes")
        publish_auth_modes = self._get_param("publishAuthModes")
        code_handlers = self._get_param("codeHandlers")
        tags = self._get_param("tags", {})
        handler_configs = self._get_param("handlerConfigs", {})

        channel_namespace = self.appsync_backend.create_channel_namespace(
            api_id=api_id,
            name=name,
            subscribe_auth_modes=subscribe_auth_modes,
            publish_auth_modes=publish_auth_modes,
            code_handlers=code_handlers,
            tags=tags,
            handler_configs=handler_configs,
        )

        return json.dumps({"channelNamespace": channel_namespace.to_json()})

    def list_channel_namespaces(self) -> str:
        api_id = self._get_param("apiId")
        channel_namespaces = self.appsync_backend.list_channel_namespaces(api_id=api_id)
        return json.dumps(
            {
                "channelNamespaces": [
                    channel_namespace.to_json()
                    for channel_namespace in channel_namespaces
                ]
            }
        )

    def delete_channel_namespace(self) -> str:
        api_id = self._get_param("apiId")
        name = self._get_param("name")

        self.appsync_backend.delete_channel_namespace(
            api_id=api_id,
            name=name,
        )
        return "{}"

    def get_api(self) -> str:
        api_id = self._get_param("apiId")

        api = self.appsync_backend.get_api(api_id=api_id)
        response = api.to_json()
        response["tags"] = self.appsync_backend.list_tags_for_resource(api.api_arn)
        return json.dumps({"api": response})
