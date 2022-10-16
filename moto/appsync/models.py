import base64
from datetime import timedelta, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService

from .exceptions import GraphqlAPINotFound


class GraphqlSchema(BaseModel):
    def __init__(self, definition: Any):
        self.definition = definition
        # [graphql.language.ast.ObjectTypeDefinitionNode, ..]
        self.types: List[Any] = []

        self.status = "PROCESSING"
        self.parse_error: Optional[str] = None
        self._parse_graphql_definition()

    def get_type(self, name: str) -> Optional[Dict[str, Any]]:  # type: ignore[return]
        for graphql_type in self.types:
            if graphql_type.name.value == name:
                return {
                    "name": name,
                    "description": graphql_type.description.value
                    if graphql_type.description
                    else None,
                    "arn": f"arn:aws:appsync:graphql_type/{name}",
                    "definition": "NotYetImplemented",
                }

    def get_status(self) -> Tuple[str, Optional[str]]:
        return self.status, self.parse_error

    def _parse_graphql_definition(self) -> None:
        try:
            from graphql import parse
            from graphql.language.ast import ObjectTypeDefinitionNode
            from graphql.error.graphql_error import GraphQLError

            res = parse(self.definition)
            for definition in res.definitions:
                if isinstance(definition, ObjectTypeDefinitionNode):
                    self.types.append(definition)
            self.status = "SUCCESS"
        except GraphQLError as e:
            self.status = "FAILED"
            self.parse_error = str(e)


class GraphqlAPIKey(BaseModel):
    def __init__(self, description: str, expires: Optional[datetime]):
        self.key_id = str(mock_random.uuid4())[0:6]
        self.description = description
        self.expires = expires
        if not self.expires:
            default_expiry = datetime.now(timezone.utc)
            default_expiry = default_expiry.replace(
                minute=0, second=0, microsecond=0, tzinfo=None
            )
            default_expiry = default_expiry + timedelta(days=7)
            self.expires = unix_time(default_expiry)

    def update(self, description: Optional[str], expires: Optional[datetime]) -> None:
        if description:
            self.description = description
        if expires:
            self.expires = expires

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.key_id,
            "description": self.description,
            "expires": self.expires,
            "deletes": self.expires,
        }


class GraphqlAPI(BaseModel):
    def __init__(
        self,
        account_id: str,
        region: str,
        name: str,
        authentication_type: str,
        additional_authentication_providers: Optional[List[str]],
        log_config: str,
        xray_enabled: str,
        user_pool_config: str,
        open_id_connect_config: str,
        lambda_authorizer_config: str,
    ):
        self.region = region
        self.name = name
        self.api_id = str(mock_random.uuid4())
        self.authentication_type = authentication_type
        self.additional_authentication_providers = additional_authentication_providers
        self.lambda_authorizer_config = lambda_authorizer_config
        self.log_config = log_config
        self.open_id_connect_config = open_id_connect_config
        self.user_pool_config = user_pool_config
        self.xray_enabled = xray_enabled

        self.arn = f"arn:aws:appsync:{self.region}:{account_id}:apis/{self.api_id}"
        self.graphql_schema: Optional[GraphqlSchema] = None

        self.api_keys: Dict[str, GraphqlAPIKey] = dict()

    def update(
        self,
        name: str,
        additional_authentication_providers: Optional[List[str]],
        authentication_type: str,
        lambda_authorizer_config: str,
        log_config: str,
        open_id_connect_config: str,
        user_pool_config: str,
        xray_enabled: str,
    ) -> None:
        if name:
            self.name = name
        if additional_authentication_providers:
            self.additional_authentication_providers = (
                additional_authentication_providers
            )
        if authentication_type:
            self.authentication_type = authentication_type
        if lambda_authorizer_config:
            self.lambda_authorizer_config = lambda_authorizer_config
        if log_config:
            self.log_config = log_config
        if open_id_connect_config:
            self.open_id_connect_config = open_id_connect_config
        if user_pool_config:
            self.user_pool_config = user_pool_config
        if xray_enabled is not None:
            self.xray_enabled = xray_enabled

    def create_api_key(
        self, description: str, expires: Optional[datetime]
    ) -> GraphqlAPIKey:
        api_key = GraphqlAPIKey(description, expires)
        self.api_keys[api_key.key_id] = api_key
        return api_key

    def list_api_keys(self) -> Iterable[GraphqlAPIKey]:
        return self.api_keys.values()

    def delete_api_key(self, api_key_id: str) -> None:
        self.api_keys.pop(api_key_id)

    def update_api_key(
        self, api_key_id: str, description: str, expires: Optional[datetime]
    ) -> GraphqlAPIKey:
        api_key = self.api_keys[api_key_id]
        api_key.update(description, expires)
        return api_key

    def start_schema_creation(self, definition: str) -> None:
        graphql_definition = base64.b64decode(definition).decode("utf-8")

        self.graphql_schema = GraphqlSchema(graphql_definition)

    def get_schema_status(self) -> Any:
        return self.graphql_schema.get_status()  # type: ignore[union-attr]

    def get_type(self, type_name: str, type_format: str) -> Any:
        graphql_type = self.graphql_schema.get_type(type_name)  # type: ignore[union-attr]
        graphql_type["format"] = type_format  # type: ignore[index]
        return graphql_type

    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "apiId": self.api_id,
            "authenticationType": self.authentication_type,
            "arn": self.arn,
            "uris": {"GRAPHQL": "http://graphql.uri"},
            "additionalAuthenticationProviders": self.additional_authentication_providers,
            "lambdaAuthorizerConfig": self.lambda_authorizer_config,
            "logConfig": self.log_config,
            "openIDConnectConfig": self.open_id_connect_config,
            "userPoolConfig": self.user_pool_config,
            "xrayEnabled": self.xray_enabled,
        }


class AppSyncBackend(BaseBackend):
    """Implementation of AppSync APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.graphql_apis: Dict[str, GraphqlAPI] = dict()
        self.tagger = TaggingService()

    def create_graphql_api(
        self,
        name: str,
        log_config: str,
        authentication_type: str,
        user_pool_config: str,
        open_id_connect_config: str,
        additional_authentication_providers: Optional[List[str]],
        xray_enabled: str,
        lambda_authorizer_config: str,
        tags: Dict[str, str],
    ) -> GraphqlAPI:
        graphql_api = GraphqlAPI(
            account_id=self.account_id,
            region=self.region_name,
            name=name,
            authentication_type=authentication_type,
            additional_authentication_providers=additional_authentication_providers,
            log_config=log_config,
            xray_enabled=xray_enabled,
            user_pool_config=user_pool_config,
            open_id_connect_config=open_id_connect_config,
            lambda_authorizer_config=lambda_authorizer_config,
        )
        self.graphql_apis[graphql_api.api_id] = graphql_api
        self.tagger.tag_resource(
            graphql_api.arn, TaggingService.convert_dict_to_tags_input(tags)
        )
        return graphql_api

    def update_graphql_api(
        self,
        api_id: str,
        name: str,
        log_config: str,
        authentication_type: str,
        user_pool_config: str,
        open_id_connect_config: str,
        additional_authentication_providers: Optional[List[str]],
        xray_enabled: str,
        lambda_authorizer_config: str,
    ) -> GraphqlAPI:
        graphql_api = self.graphql_apis[api_id]
        graphql_api.update(
            name,
            additional_authentication_providers,
            authentication_type,
            lambda_authorizer_config,
            log_config,
            open_id_connect_config,
            user_pool_config,
            xray_enabled,
        )
        return graphql_api

    def get_graphql_api(self, api_id: str) -> GraphqlAPI:
        if api_id not in self.graphql_apis:
            raise GraphqlAPINotFound(api_id)
        return self.graphql_apis[api_id]

    def delete_graphql_api(self, api_id: str) -> None:
        self.graphql_apis.pop(api_id)

    def list_graphql_apis(self) -> Iterable[GraphqlAPI]:
        """
        Pagination or the maxResults-parameter have not yet been implemented.
        """
        return self.graphql_apis.values()

    def create_api_key(
        self, api_id: str, description: str, expires: Optional[datetime]
    ) -> GraphqlAPIKey:
        return self.graphql_apis[api_id].create_api_key(description, expires)

    def delete_api_key(self, api_id: str, api_key_id: str) -> None:
        self.graphql_apis[api_id].delete_api_key(api_key_id)

    def list_api_keys(self, api_id: str) -> Iterable[GraphqlAPIKey]:
        """
        Pagination or the maxResults-parameter have not yet been implemented.
        """
        if api_id in self.graphql_apis:
            return self.graphql_apis[api_id].list_api_keys()
        else:
            return []

    def update_api_key(
        self,
        api_id: str,
        api_key_id: str,
        description: str,
        expires: Optional[datetime],
    ) -> GraphqlAPIKey:
        return self.graphql_apis[api_id].update_api_key(
            api_key_id, description, expires
        )

    def start_schema_creation(self, api_id: str, definition: str) -> str:
        self.graphql_apis[api_id].start_schema_creation(definition)
        return "PROCESSING"

    def get_schema_creation_status(self, api_id: str) -> Any:
        return self.graphql_apis[api_id].get_schema_status()

    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        self.tagger.tag_resource(
            resource_arn, TaggingService.convert_dict_to_tags_input(tags)
        )

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> Dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)

    def get_type(self, api_id: str, type_name: str, type_format: str) -> Any:
        return self.graphql_apis[api_id].get_type(type_name, type_format)


appsync_backends = BackendDict(AppSyncBackend, "appsync")
