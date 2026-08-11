"""Handles incoming cleanrooms requests, invokes methods, returns responses."""

import json
from typing import Any
from urllib.parse import unquote

from moto.core.responses import BaseResponse

from .models import CleanRoomsBackend, cleanrooms_backends


class CleanRoomsResponse(BaseResponse):
    """Handler for CleanRoomsService requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="cleanrooms")

    @property
    def cleanrooms_backend(self) -> CleanRoomsBackend:
        return cleanrooms_backends[self.current_account][self.region]

    def create_collaboration(self) -> str:
        params = json.loads(self.body)
        collaboration = self.cleanrooms_backend.create_collaboration(
            name=params.get("name"),
            description=params.get("description"),
            creator_display_name=params.get("creatorDisplayName"),
            creator_member_abilities=params.get("creatorMemberAbilities"),
            query_log_status=params.get("queryLogStatus"),
            members=params.get("members") or [],
            data_encryption_metadata=params.get("dataEncryptionMetadata"),
            analytics_engine=params.get("analyticsEngine"),
            tags=params.get("tags"),
        )
        return json.dumps({"collaboration": collaboration.to_dict()})

    def get_collaboration(self) -> str:
        collaboration_identifier = self._get_param("collaborationIdentifier")
        collaboration = self.cleanrooms_backend.get_collaboration(
            collaboration_identifier
        )
        return json.dumps({"collaboration": collaboration.to_dict()})

    def list_collaborations(self) -> str:
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        collaborations, next_token = self.cleanrooms_backend.list_collaborations(
            max_results=max_results, next_token=next_token
        )
        response: dict[str, Any] = {
            "collaborationList": [c.to_summary_dict() for c in collaborations]
        }
        if next_token:
            response["nextToken"] = next_token
        return json.dumps(response)

    def update_collaboration(self) -> str:
        params = json.loads(self.body)
        collaboration = self.cleanrooms_backend.update_collaboration(
            collaboration_identifier=self._get_param("collaborationIdentifier"),
            name=params.get("name"),
            description=params.get("description"),
        )
        return json.dumps({"collaboration": collaboration.to_dict()})

    def delete_collaboration(self) -> str:
        collaboration_identifier = self._get_param("collaborationIdentifier")
        self.cleanrooms_backend.delete_collaboration(collaboration_identifier)
        return json.dumps({})

    def list_members(self) -> str:
        collaboration_identifier = self._get_param("collaborationIdentifier")
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        members, next_token = self.cleanrooms_backend.list_members(
            collaboration_identifier=collaboration_identifier,
            max_results=max_results,
            next_token=next_token,
        )
        response: dict[str, Any] = {"memberSummaries": members}
        if next_token:
            response["nextToken"] = next_token
        return json.dumps(response)

    def create_membership(self) -> str:
        params = json.loads(self.body)
        membership = self.cleanrooms_backend.create_membership(
            collaboration_identifier=params.get("collaborationIdentifier"),
            query_log_status=params.get("queryLogStatus"),
            payment_configuration=params.get("paymentConfiguration"),
            default_result_configuration=params.get("defaultResultConfiguration"),
            tags=params.get("tags"),
        )
        return json.dumps({"membership": membership.to_dict()})

    def get_membership(self) -> str:
        membership_identifier = self._get_param("membershipIdentifier")
        membership = self.cleanrooms_backend.get_membership(membership_identifier)
        return json.dumps({"membership": membership.to_dict()})

    def list_memberships(self) -> str:
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        memberships, next_token = self.cleanrooms_backend.list_memberships(
            max_results=max_results, next_token=next_token
        )
        response: dict[str, Any] = {
            "membershipSummaries": [m.to_summary_dict() for m in memberships]
        }
        if next_token:
            response["nextToken"] = next_token
        return json.dumps(response)

    def update_membership(self) -> str:
        params = json.loads(self.body)
        membership = self.cleanrooms_backend.update_membership(
            membership_identifier=self._get_param("membershipIdentifier"),
            query_log_status=params.get("queryLogStatus"),
        )
        return json.dumps({"membership": membership.to_dict()})

    def delete_membership(self) -> str:
        membership_identifier = self._get_param("membershipIdentifier")
        self.cleanrooms_backend.delete_membership(membership_identifier)
        return json.dumps({})

    def create_configured_table(self) -> str:
        params = json.loads(self.body)
        configured_table = self.cleanrooms_backend.create_configured_table(
            name=params.get("name"),
            description=params.get("description"),
            table_reference=params.get("tableReference"),
            allowed_columns=params.get("allowedColumns"),
            analysis_method=params.get("analysisMethod"),
            selected_analysis_methods=params.get("selectedAnalysisMethods"),
            tags=params.get("tags"),
        )
        return json.dumps({"configuredTable": configured_table.to_dict()})

    def get_configured_table(self) -> str:
        configured_table_identifier = self._get_param("configuredTableIdentifier")
        configured_table = self.cleanrooms_backend.get_configured_table(
            configured_table_identifier
        )
        return json.dumps({"configuredTable": configured_table.to_dict()})

    def list_configured_tables(self) -> str:
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        configured_tables, next_token = self.cleanrooms_backend.list_configured_tables(
            max_results=max_results, next_token=next_token
        )
        response: dict[str, Any] = {
            "configuredTableSummaries": [t.to_summary_dict() for t in configured_tables]
        }
        if next_token:
            response["nextToken"] = next_token
        return json.dumps(response)

    def update_configured_table(self) -> str:
        params = json.loads(self.body)
        configured_table = self.cleanrooms_backend.update_configured_table(
            configured_table_identifier=self._get_param("configuredTableIdentifier"),
            name=params.get("name"),
            description=params.get("description"),
            analysis_method=params.get("analysisMethod"),
            selected_analysis_methods=params.get("selectedAnalysisMethods"),
        )
        return json.dumps({"configuredTable": configured_table.to_dict()})

    def delete_configured_table(self) -> str:
        configured_table_identifier = self._get_param("configuredTableIdentifier")
        self.cleanrooms_backend.delete_configured_table(configured_table_identifier)
        return json.dumps({})

    def tag_resource(self) -> str:
        resource_arn = unquote(self._get_param("resourceArn"))
        tags = json.loads(self.body).get("tags") or {}
        self.cleanrooms_backend.tag_resource(resource_arn, tags)
        return json.dumps({})

    def untag_resource(self) -> str:
        resource_arn = unquote(self._get_param("resourceArn"))
        tag_keys = self.querystring.get("tagKeys", [])
        self.cleanrooms_backend.untag_resource(resource_arn, tag_keys)
        return json.dumps({})

    def list_tags_for_resource(self) -> str:
        resource_arn = unquote(self._get_param("resourceArn"))
        tags = self.cleanrooms_backend.list_tags_for_resource(resource_arn)
        return json.dumps({"tags": tags})
