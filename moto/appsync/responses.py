"""Handles incoming appsync requests, invokes methods, returns responses."""

import json
import re
from typing import Any
from uuid import uuid4

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import ActionResult, BaseResponse, EmptyResult
from moto.core.utils import unix_time, utcfromtimestamp

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

    def create_graphql_api(self) -> ActionResult:
        name = self._get_param("name")
        log_config = self._get_param("logConfig")
        authentication_type = self._get_param("authenticationType")
        user_pool_config = self._get_param("userPoolConfig")
        open_id_connect_config = self._get_param("openIDConnectConfig")
        tags = self._get_param("tags")
        additional_authentication_providers = self._get_param(
            "additionalAuthenticationProviders"
        )
        xray_enabled = self._get_bool_param("xrayEnabled", False)
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
        result = {
            "graphqlApi": {
                "name": graphql_api.name,
                "apiId": graphql_api.api_id,
                "authenticationType": graphql_api.authentication_type,
                "arn": graphql_api.arn,
                "uris": {"GRAPHQL": "http://graphql.uri"},
                "additionalAuthenticationProviders": graphql_api.additional_authentication_providers,
                "lambdaAuthorizerConfig": graphql_api.lambda_authorizer_config,
                "logConfig": graphql_api.log_config,
                "openIDConnectConfig": graphql_api.open_id_connect_config,
                "userPoolConfig": graphql_api.user_pool_config,
                "xrayEnabled": graphql_api.xray_enabled,
                "visibility": graphql_api.visibility,
                "tags": self.appsync_backend.list_tags_for_resource(graphql_api.arn),
            }
        }
        return ActionResult(result)

    def get_graphql_api(self) -> ActionResult:
        api_id = self._get_param("apiId")
        graphql_api = self.appsync_backend.get_graphql_api(api_id=api_id)
        result = {
            "graphqlApi": {
                "name": graphql_api.name,
                "apiId": graphql_api.api_id,
                "authenticationType": graphql_api.authentication_type,
                "arn": graphql_api.arn,
                "uris": {"GRAPHQL": "http://graphql.uri"},
                "additionalAuthenticationProviders": graphql_api.additional_authentication_providers,
                "lambdaAuthorizerConfig": graphql_api.lambda_authorizer_config,
                "logConfig": graphql_api.log_config,
                "openIDConnectConfig": graphql_api.open_id_connect_config,
                "userPoolConfig": graphql_api.user_pool_config,
                "xrayEnabled": graphql_api.xray_enabled,
                "visibility": graphql_api.visibility,
                "tags": self.appsync_backend.list_tags_for_resource(graphql_api.arn),
            }
        }
        return ActionResult(result)

    def delete_graphql_api(self) -> ActionResult:
        api_id = self._get_param("apiId")
        self.appsync_backend.delete_graphql_api(api_id=api_id)
        return EmptyResult()

    def update_graphql_api(self) -> ActionResult:
        api_id = self._get_param("apiId")

        name = self._get_param("name")
        log_config = self._get_param("logConfig")
        authentication_type = self._get_param("authenticationType")
        user_pool_config = self._get_param("userPoolConfig")
        open_id_connect_config = self._get_param("openIDConnectConfig")
        additional_authentication_providers = self._get_param(
            "additionalAuthenticationProviders"
        )
        xray_enabled = self._get_bool_param("xrayEnabled", False)
        lambda_authorizer_config = self._get_param("lambdaAuthorizerConfig")

        graphql_api = self.appsync_backend.update_graphql_api(
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
        result = {
            "graphqlApi": {
                "name": graphql_api.name,
                "apiId": graphql_api.api_id,
                "authenticationType": graphql_api.authentication_type,
                "arn": graphql_api.arn,
                "uris": {"GRAPHQL": "http://graphql.uri"},
                "additionalAuthenticationProviders": graphql_api.additional_authentication_providers,
                "lambdaAuthorizerConfig": graphql_api.lambda_authorizer_config,
                "logConfig": graphql_api.log_config,
                "openIDConnectConfig": graphql_api.open_id_connect_config,
                "userPoolConfig": graphql_api.user_pool_config,
                "xrayEnabled": graphql_api.xray_enabled,
                "visibility": graphql_api.visibility,
                "tags": self.appsync_backend.list_tags_for_resource(graphql_api.arn),
            }
        }
        return ActionResult(result)

    def list_graphql_apis(self) -> ActionResult:
        graphql_apis = self.appsync_backend.list_graphql_apis()
        result = {
            "graphqlApis": [
                {
                    "name": graphql_api.name,
                    "apiId": graphql_api.api_id,
                    "authenticationType": graphql_api.authentication_type,
                    "arn": graphql_api.arn,
                    "uris": {"GRAPHQL": "http://graphql.uri"},
                    "additionalAuthenticationProviders": graphql_api.additional_authentication_providers,
                    "lambdaAuthorizerConfig": graphql_api.lambda_authorizer_config,
                    "logConfig": graphql_api.log_config,
                    "openIDConnectConfig": graphql_api.open_id_connect_config,
                    "userPoolConfig": graphql_api.user_pool_config,
                    "xrayEnabled": graphql_api.xray_enabled,
                    "visibility": graphql_api.visibility,
                    "tags": self.appsync_backend.list_tags_for_resource(
                        graphql_api.arn
                    ),
                }
                for graphql_api in graphql_apis
            ]
        }
        return ActionResult(result)

    def create_api_key(self) -> ActionResult:
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
            api_id=api_id,
            description=description,
            expires=utcfromtimestamp(expires) if expires else None,
        )
        result = {
            "apiKey": {
                "id": api_key.key_id,
                "description": api_key.description,
                "expires": int(unix_time(api_key.expires)),
                "deletes": int(unix_time(api_key.expires)),
            }
        }
        return ActionResult(result)

    def delete_api_key(self) -> ActionResult:
        api_id = self._get_param("apiId")
        api_key_id = self._get_param("id")
        self.appsync_backend.delete_api_key(api_id=api_id, api_key_id=api_key_id)
        return EmptyResult()

    def list_api_keys(self) -> ActionResult:
        api_id = self._get_param("apiId")
        api_keys = self.appsync_backend.list_api_keys(api_id=api_id)
        result = {
            "apiKeys": [
                {
                    "id": api_key.key_id,
                    "description": api_key.description,
                    "expires": int(unix_time(api_key.expires)),
                    "deletes": int(unix_time(api_key.expires)),
                }
                for api_key in api_keys
            ]
        }
        return ActionResult(result)

    def update_api_key(self) -> ActionResult:
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
            expires=utcfromtimestamp(expires) if expires else None,
        )
        result = {
            "apiKey": {
                "id": api_key.key_id,
                "description": api_key.description,
                "expires": int(unix_time(api_key.expires)),
                "deletes": int(unix_time(api_key.expires)),
            }
        }
        return ActionResult(result)

    def start_schema_creation(self) -> ActionResult:
        api_id = self._get_param("apiId")
        definition = self._get_param("definition")
        status = self.appsync_backend.start_schema_creation(
            api_id=api_id, definition=definition
        )
        result = {"status": status}
        return ActionResult(result)

    def get_schema_creation_status(self) -> ActionResult:
        api_id = self._get_param("apiId")
        status, details = self.appsync_backend.get_schema_creation_status(api_id=api_id)
        result = {"status": status, "details": details}
        return ActionResult(result)

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tags = self._get_param("tags")
        self.appsync_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])
        self.appsync_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return EmptyResult()

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tags = self.appsync_backend.list_tags_for_resource(resource_arn=resource_arn)
        result = {"tags": tags}
        return ActionResult(result)

    def get_type(self) -> ActionResult:
        api_id = self._get_param("apiId")
        type_name = self._get_param("typeName")
        type_format = self._get_param("format")
        graphql_type = self.appsync_backend.get_type(
            api_id=api_id, type_name=type_name, type_format=type_format
        )
        result = {"type": graphql_type}
        return ActionResult(result)

    def get_introspection_schema(self) -> ActionResult:
        api_id = self._get_param("apiId")
        format_ = self._get_param("format")
        include_directives = self._get_bool_param("includeDirectives", True)
        graphql_schema = self.appsync_backend.get_graphql_schema(api_id=api_id)

        schema = graphql_schema.get_introspection_schema(
            format_=format_, include_directives=include_directives
        )
        result = {"schema": schema}
        return ActionResult(result)

    def get_api_cache(self) -> ActionResult:
        api_id = self._get_param("apiId")
        api_cache = self.appsync_backend.get_api_cache(
            api_id=api_id,
        )
        result = {
            "apiCache": {
                "ttl": api_cache.ttl,
                "transitEncryptionEnabled": api_cache.transit_encryption_enabled,
                "atRestEncryptionEnabled": api_cache.at_rest_encryption_enabled,
                "apiCachingBehavior": api_cache.api_caching_behavior,
                "type": api_cache.type,
                "healthMetricsConfig": api_cache.health_metrics_config,
                "status": api_cache.status,
            }
        }
        return ActionResult(result)

    def delete_api_cache(self) -> ActionResult:
        api_id = self._get_param("apiId")
        self.appsync_backend.delete_api_cache(
            api_id=api_id,
        )
        return EmptyResult()

    def create_api_cache(self) -> ActionResult:
        api_id = self._get_param("apiId")
        ttl = self._get_param("ttl")
        transit_encryption_enabled = self._get_bool_param("transitEncryptionEnabled")
        at_rest_encryption_enabled = self._get_bool_param("atRestEncryptionEnabled")
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
        result = {
            "apiCache": {
                "ttl": api_cache.ttl,
                "transitEncryptionEnabled": api_cache.transit_encryption_enabled,
                "atRestEncryptionEnabled": api_cache.at_rest_encryption_enabled,
                "apiCachingBehavior": api_cache.api_caching_behavior,
                "type": api_cache.type,
                "healthMetricsConfig": api_cache.health_metrics_config,
                "status": api_cache.status,
            }
        }
        return ActionResult(result)

    def update_api_cache(self) -> ActionResult:
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
        result = {
            "apiCache": {
                "ttl": api_cache.ttl,
                "transitEncryptionEnabled": api_cache.transit_encryption_enabled,
                "atRestEncryptionEnabled": api_cache.at_rest_encryption_enabled,
                "apiCachingBehavior": api_cache.api_caching_behavior,
                "type": api_cache.type,
                "healthMetricsConfig": api_cache.health_metrics_config,
                "status": api_cache.status,
            }
        }
        return ActionResult(result)

    def flush_api_cache(self) -> ActionResult:
        api_id = self._get_param("apiId")
        self.appsync_backend.flush_api_cache(
            api_id=api_id,
        )
        return EmptyResult()

    def create_api(self) -> ActionResult:
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
        api_dict: dict[str, Any] = {
            "apiId": api.api_id,
            "name": api.name,
            "tags": self.appsync_backend.list_tags_for_resource(api.api_arn),
            "dns": api.dns,
            "apiArn": api.api_arn,
            "created": api.created,
            "eventConfig": api.event_config or {},  # Default to empty dict if None
        }
        if api.owner_contact:
            api_dict["ownerContact"] = api.owner_contact
        result = {"api": api_dict}
        return ActionResult(result)

    def list_apis(self) -> ActionResult:
        apis = self.appsync_backend.list_apis()
        api_list = []
        for api in apis:
            api_dict: dict[str, Any] = {
                "apiId": api.api_id,
                "name": api.name,
                "tags": self.appsync_backend.list_tags_for_resource(api.api_arn),
                "dns": api.dns,
                "apiArn": api.api_arn,
                "created": api.created,
                "eventConfig": api.event_config or {},  # Default to empty dict if None
            }
            if api.owner_contact:
                api_dict["ownerContact"] = api.owner_contact
            api_list.append(api_dict)
        result = {"apis": api_list}
        return ActionResult(result)

    def delete_api(self) -> ActionResult:
        api_id = self._get_param("apiId")
        self.appsync_backend.delete_api(api_id=api_id)
        return EmptyResult()

    def create_channel_namespace(self) -> ActionResult:
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
        channel_namespace_dict: dict[str, Any] = {
            "apiId": channel_namespace.api_id,
            "name": channel_namespace.name,
            "subscribeAuthModes": channel_namespace.subscribe_auth_modes,
            "publishAuthModes": channel_namespace.publish_auth_modes,
            "channelNamespaceArn": channel_namespace.channel_namespace_arn,
            "created": channel_namespace.created,
            "lastModified": channel_namespace.last_modified,
            "handlerConfigs": channel_namespace.handler_configs,
        }
        if channel_namespace.code_handlers:
            channel_namespace_dict["codeHandlers"] = channel_namespace.code_handlers
        channel_namespace_dict["tags"] = self.appsync_backend.list_tags_for_resource(
            channel_namespace.channel_namespace_arn
        )
        result = {"channelNamespace": channel_namespace_dict}
        return ActionResult(result)

    def list_channel_namespaces(self) -> ActionResult:
        api_id = self._get_param("apiId")
        channel_namespaces = self.appsync_backend.list_channel_namespaces(api_id=api_id)
        channel_namespace_list = []
        for channel_namespace in channel_namespaces:
            channel_namespace_dict: dict[str, Any] = {
                "apiId": channel_namespace.api_id,
                "name": channel_namespace.name,
                "subscribeAuthModes": channel_namespace.subscribe_auth_modes,
                "publishAuthModes": channel_namespace.publish_auth_modes,
                "channelNamespaceArn": channel_namespace.channel_namespace_arn,
                "created": channel_namespace.created,
                "lastModified": channel_namespace.last_modified,
                "handlerConfigs": channel_namespace.handler_configs,
            }
            if channel_namespace.code_handlers:
                channel_namespace_dict["codeHandlers"] = channel_namespace.code_handlers
            channel_namespace_dict["tags"] = (
                self.appsync_backend.list_tags_for_resource(
                    channel_namespace.channel_namespace_arn
                )
            )
            channel_namespace_list.append(channel_namespace_dict)
        result = {"channelNamespaces": channel_namespace_list}
        return ActionResult(result)

    def delete_channel_namespace(self) -> ActionResult:
        api_id = self._get_param("apiId")
        name = self._get_param("name")

        self.appsync_backend.delete_channel_namespace(
            api_id=api_id,
            name=name,
        )
        return EmptyResult()

    def get_api(self) -> ActionResult:
        api_id = self._get_param("apiId")
        api = self.appsync_backend.get_api(api_id=api_id)
        api_dict: dict[str, Any] = {
            "apiId": api.api_id,
            "name": api.name,
            "tags": self.appsync_backend.list_tags_for_resource(api.api_arn),
            "dns": api.dns,
            "apiArn": api.api_arn,
            "created": api.created,
            "eventConfig": api.event_config or {},  # Default to empty dict if None
        }
        if api.owner_contact:
            api_dict["ownerContact"] = api.owner_contact
        result = {"api": api_dict}
        return ActionResult(result)
