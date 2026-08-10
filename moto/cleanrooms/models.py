"""CleanRoomsBackend class with methods for supported APIs."""

from typing import Any

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import get_partition

from .exceptions import ResourceNotFoundException

DEFAULT_PAYMENT_CONFIGURATION = {"queryCompute": {"isResponsible": True}}


class Collaboration(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        name: str,
        description: str,
        creator_display_name: str,
        creator_member_abilities: list[str],
        query_log_status: str,
        members: list[dict[str, Any]],
        data_encryption_metadata: dict[str, Any] | None,
        analytics_engine: str | None,
    ):
        self.id = str(mock_random.uuid4())
        self.arn = f"arn:{get_partition(region_name)}:cleanrooms:{region_name}:{account_id}:collaboration/{self.id}"
        self.name = name
        self.description = description
        self.creator_account_id = account_id
        self.creator_display_name = creator_display_name
        self.creator_member_abilities = creator_member_abilities
        self.query_log_status = query_log_status
        self.members = members
        self.data_encryption_metadata = data_encryption_metadata
        self.analytics_engine = analytics_engine
        self.create_time = unix_time()
        self.update_time = self.create_time
        # The creator only becomes an active member once they create a
        # membership for this collaboration
        self.member_status = "INVITED"
        self.membership_id: str | None = None
        self.membership_arn: str | None = None

    def to_summary_dict(self) -> dict[str, Any]:
        summary = {
            "id": self.id,
            "arn": self.arn,
            "name": self.name,
            "creatorAccountId": self.creator_account_id,
            "creatorDisplayName": self.creator_display_name,
            "createTime": self.create_time,
            "updateTime": self.update_time,
            "memberStatus": self.member_status,
            "membershipId": self.membership_id,
            "membershipArn": self.membership_arn,
            "analyticsEngine": self.analytics_engine,
        }
        return {k: v for k, v in summary.items() if v is not None}

    def to_dict(self) -> dict[str, Any]:
        dct = {
            **self.to_summary_dict(),
            "description": self.description,
            "queryLogStatus": self.query_log_status,
            "dataEncryptionMetadata": self.data_encryption_metadata,
        }
        return {k: v for k, v in dct.items() if v is not None}

    def member_summaries(self) -> list[dict[str, Any]]:
        creator = {
            "accountId": self.creator_account_id,
            "status": self.member_status,
            "displayName": self.creator_display_name,
            "abilities": self.creator_member_abilities,
            "createTime": self.create_time,
            "updateTime": self.update_time,
            "membershipId": self.membership_id,
            "membershipArn": self.membership_arn,
            "paymentConfiguration": DEFAULT_PAYMENT_CONFIGURATION,
        }
        summaries = [{k: v for k, v in creator.items() if v is not None}]
        for member in self.members:
            summaries.append(
                {
                    "accountId": member["accountId"],
                    "status": "INVITED",
                    "displayName": member["displayName"],
                    "abilities": member["memberAbilities"],
                    "createTime": self.create_time,
                    "updateTime": self.update_time,
                    "paymentConfiguration": member.get(
                        "paymentConfiguration", DEFAULT_PAYMENT_CONFIGURATION
                    ),
                }
            )
        return summaries


class Membership(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        collaboration: Collaboration,
        query_log_status: str,
        payment_configuration: dict[str, Any] | None,
        default_result_configuration: dict[str, Any] | None,
    ):
        self.id = str(mock_random.uuid4())
        self.arn = f"arn:{get_partition(region_name)}:cleanrooms:{region_name}:{account_id}:membership/{self.id}"
        self.collaboration_arn = collaboration.arn
        self.collaboration_id = collaboration.id
        self.collaboration_creator_account_id = collaboration.creator_account_id
        self.collaboration_creator_display_name = collaboration.creator_display_name
        self.collaboration_name = collaboration.name
        self.status = "ACTIVE"
        self.member_abilities = collaboration.creator_member_abilities
        self.query_log_status = query_log_status
        self.payment_configuration = (
            payment_configuration or DEFAULT_PAYMENT_CONFIGURATION
        )
        self.default_result_configuration = default_result_configuration
        self.create_time = unix_time()
        self.update_time = self.create_time

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "arn": self.arn,
            "collaborationArn": self.collaboration_arn,
            "collaborationId": self.collaboration_id,
            "collaborationCreatorAccountId": self.collaboration_creator_account_id,
            "collaborationCreatorDisplayName": self.collaboration_creator_display_name,
            "collaborationName": self.collaboration_name,
            "createTime": self.create_time,
            "updateTime": self.update_time,
            "status": self.status,
            "memberAbilities": self.member_abilities,
            "paymentConfiguration": self.payment_configuration,
        }

    def to_dict(self) -> dict[str, Any]:
        dct = {
            **self.to_summary_dict(),
            "queryLogStatus": self.query_log_status,
            "defaultResultConfiguration": self.default_result_configuration,
        }
        return {k: v for k, v in dct.items() if v is not None}


class ConfiguredTable(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        name: str,
        description: str | None,
        table_reference: dict[str, Any],
        allowed_columns: list[str],
        analysis_method: str,
        selected_analysis_methods: list[str] | None,
    ):
        self.id = str(mock_random.uuid4())
        self.arn = f"arn:{get_partition(region_name)}:cleanrooms:{region_name}:{account_id}:configuredtable/{self.id}"
        self.name = name
        self.description = description
        self.table_reference = table_reference
        self.allowed_columns = allowed_columns
        self.analysis_method = analysis_method
        self.selected_analysis_methods = selected_analysis_methods
        self.analysis_rule_types: list[str] = []
        self.create_time = unix_time()
        self.update_time = self.create_time

    def to_summary_dict(self) -> dict[str, Any]:
        summary = {
            "id": self.id,
            "arn": self.arn,
            "name": self.name,
            "createTime": self.create_time,
            "updateTime": self.update_time,
            "analysisRuleTypes": self.analysis_rule_types,
            "analysisMethod": self.analysis_method,
            "selectedAnalysisMethods": self.selected_analysis_methods,
        }
        return {k: v for k, v in summary.items() if v is not None}

    def to_dict(self) -> dict[str, Any]:
        dct = {
            **self.to_summary_dict(),
            "description": self.description,
            "tableReference": self.table_reference,
            "allowedColumns": self.allowed_columns,
        }
        return {k: v for k, v in dct.items() if v is not None}


class CleanRoomsBackend(BaseBackend):
    """Implementation of CleanRoomsService APIs."""

    PAGINATION_MODEL = {
        "list_collaborations": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "id",
        },
        "list_members": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "accountId",
        },
        "list_memberships": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "id",
        },
        "list_configured_tables": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "id",
        },
    }

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.collaborations: dict[str, Collaboration] = {}
        self.memberships: dict[str, Membership] = {}
        self.configured_tables: dict[str, ConfiguredTable] = {}
        self.tagger = TaggingService()

    def create_collaboration(
        self,
        name: str,
        description: str,
        creator_display_name: str,
        creator_member_abilities: list[str],
        query_log_status: str,
        members: list[dict[str, Any]],
        data_encryption_metadata: dict[str, Any] | None,
        analytics_engine: str | None,
        tags: dict[str, str] | None,
    ) -> Collaboration:
        collaboration = Collaboration(
            account_id=self.account_id,
            region_name=self.region_name,
            name=name,
            description=description,
            creator_display_name=creator_display_name,
            creator_member_abilities=creator_member_abilities,
            query_log_status=query_log_status,
            members=members,
            data_encryption_metadata=data_encryption_metadata,
            analytics_engine=analytics_engine,
        )
        self.collaborations[collaboration.id] = collaboration
        if tags:
            self.tag_resource(collaboration.arn, tags)
        return collaboration

    def get_collaboration(self, collaboration_identifier: str) -> Collaboration:
        if collaboration_identifier not in self.collaborations:
            raise ResourceNotFoundException("collaboration", collaboration_identifier)
        return self.collaborations[collaboration_identifier]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_collaborations(self) -> list[Collaboration]:
        return list(self.collaborations.values())

    def update_collaboration(
        self,
        collaboration_identifier: str,
        name: str | None,
        description: str | None,
    ) -> Collaboration:
        collaboration = self.get_collaboration(collaboration_identifier)
        if name is not None:
            collaboration.name = name
        if description is not None:
            collaboration.description = description
        collaboration.update_time = unix_time()
        return collaboration

    def delete_collaboration(self, collaboration_identifier: str) -> None:
        self.get_collaboration(collaboration_identifier)
        del self.collaborations[collaboration_identifier]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_members(  # type: ignore[misc]
        self, collaboration_identifier: str
    ) -> list[dict[str, Any]]:
        collaboration = self.get_collaboration(collaboration_identifier)
        return collaboration.member_summaries()

    def create_membership(
        self,
        collaboration_identifier: str,
        query_log_status: str,
        payment_configuration: dict[str, Any] | None,
        default_result_configuration: dict[str, Any] | None,
        tags: dict[str, str] | None,
    ) -> Membership:
        collaboration = self.get_collaboration(collaboration_identifier)
        membership = Membership(
            account_id=self.account_id,
            region_name=self.region_name,
            collaboration=collaboration,
            query_log_status=query_log_status,
            payment_configuration=payment_configuration,
            default_result_configuration=default_result_configuration,
        )
        self.memberships[membership.id] = membership
        collaboration.member_status = "ACTIVE"
        collaboration.membership_id = membership.id
        collaboration.membership_arn = membership.arn
        if tags:
            self.tag_resource(membership.arn, tags)
        return membership

    def get_membership(self, membership_identifier: str) -> Membership:
        if membership_identifier not in self.memberships:
            raise ResourceNotFoundException("membership", membership_identifier)
        return self.memberships[membership_identifier]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_memberships(self) -> list[Membership]:
        return list(self.memberships.values())

    def update_membership(
        self, membership_identifier: str, query_log_status: str | None
    ) -> Membership:
        membership = self.get_membership(membership_identifier)
        if query_log_status is not None:
            membership.query_log_status = query_log_status
        membership.update_time = unix_time()
        return membership

    def delete_membership(self, membership_identifier: str) -> None:
        membership = self.get_membership(membership_identifier)
        collaboration = self.collaborations.get(membership.collaboration_id)
        if collaboration and collaboration.membership_id == membership.id:
            collaboration.member_status = "LEFT"
            collaboration.membership_id = None
            collaboration.membership_arn = None
        del self.memberships[membership_identifier]

    def create_configured_table(
        self,
        name: str,
        description: str | None,
        table_reference: dict[str, Any],
        allowed_columns: list[str],
        analysis_method: str,
        selected_analysis_methods: list[str] | None,
        tags: dict[str, str] | None,
    ) -> ConfiguredTable:
        configured_table = ConfiguredTable(
            account_id=self.account_id,
            region_name=self.region_name,
            name=name,
            description=description,
            table_reference=table_reference,
            allowed_columns=allowed_columns,
            analysis_method=analysis_method,
            selected_analysis_methods=selected_analysis_methods,
        )
        self.configured_tables[configured_table.id] = configured_table
        if tags:
            self.tag_resource(configured_table.arn, tags)
        return configured_table

    def get_configured_table(self, configured_table_identifier: str) -> ConfiguredTable:
        if configured_table_identifier not in self.configured_tables:
            raise ResourceNotFoundException(
                "configured table", configured_table_identifier
            )
        return self.configured_tables[configured_table_identifier]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_configured_tables(self) -> list[ConfiguredTable]:
        return list(self.configured_tables.values())

    def update_configured_table(
        self,
        configured_table_identifier: str,
        name: str | None,
        description: str | None,
        analysis_method: str | None,
        selected_analysis_methods: list[str] | None,
    ) -> ConfiguredTable:
        configured_table = self.get_configured_table(configured_table_identifier)
        if name is not None:
            configured_table.name = name
        if description is not None:
            configured_table.description = description
        if analysis_method is not None:
            configured_table.analysis_method = analysis_method
        if selected_analysis_methods is not None:
            configured_table.selected_analysis_methods = selected_analysis_methods
        configured_table.update_time = unix_time()
        return configured_table

    def delete_configured_table(self, configured_table_identifier: str) -> None:
        self.get_configured_table(configured_table_identifier)
        del self.configured_tables[configured_table_identifier]

    def tag_resource(self, resource_arn: str, tags: dict[str, str]) -> None:
        self.tagger.tag_resource(
            resource_arn, TaggingService.convert_dict_to_tags_input(tags)
        )

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)


cleanrooms_backends = BackendDict(CleanRoomsBackend, "cleanrooms")
