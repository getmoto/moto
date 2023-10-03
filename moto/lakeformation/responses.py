"""Handles incoming lakeformation requests, invokes methods, returns responses."""
import json
from typing import Any, Dict

from moto.core.responses import BaseResponse
from .models import lakeformation_backends, LakeFormationBackend


class LakeFormationResponse(BaseResponse):
    """Handler for LakeFormation requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="lakeformation")

    @property
    def lakeformation_backend(self) -> LakeFormationBackend:
        """Return backend instance specific for this region."""
        return lakeformation_backends[self.current_account][self.region]

    def describe_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        resource = self.lakeformation_backend.describe_resource(
            resource_arn=resource_arn
        )
        return json.dumps({"ResourceInfo": resource.to_dict()})

    def deregister_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        self.lakeformation_backend.deregister_resource(resource_arn=resource_arn)
        return "{}"

    def register_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        role_arn = self._get_param("RoleArn")
        self.lakeformation_backend.register_resource(
            resource_arn=resource_arn,
            role_arn=role_arn,
        )
        return "{}"

    def list_resources(self) -> str:
        resources = self.lakeformation_backend.list_resources()
        return json.dumps({"ResourceInfoList": [res.to_dict() for res in resources]})

    def get_data_lake_settings(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        settings = self.lakeformation_backend.get_data_lake_settings(catalog_id)
        return json.dumps({"DataLakeSettings": settings})

    def put_data_lake_settings(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        settings = self._get_param("DataLakeSettings")
        self.lakeformation_backend.put_data_lake_settings(catalog_id, settings)
        return "{}"

    def grant_permissions(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        principal = self._get_param("Principal")
        resource = self._get_param("Resource")
        permissions = self._get_param("Permissions")
        permissions_with_grant_options = self._get_param("PermissionsWithGrantOption")
        self.lakeformation_backend.grant_permissions(
            catalog_id=catalog_id,
            principal=principal,
            resource=resource,
            permissions=permissions,
            permissions_with_grant_options=permissions_with_grant_options,
        )
        return "{}"

    def revoke_permissions(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        principal = self._get_param("Principal")
        resource = self._get_param("Resource")
        permissions = self._get_param("Permissions")
        permissions_with_grant_options = (
            self._get_param("PermissionsWithGrantOption") or []
        )
        self.lakeformation_backend.revoke_permissions(
            catalog_id=catalog_id,
            principal=principal,
            resource=resource,
            permissions_to_revoke=permissions,
            permissions_with_grant_options_to_revoke=permissions_with_grant_options,
        )
        return "{}"

    def list_permissions(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        permissions = self.lakeformation_backend.list_permissions(catalog_id)
        return json.dumps({"PrincipalResourcePermissions": permissions})

    def create_lf_tag(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        key = self._get_param("TagKey")
        values = self._get_param("TagValues")
        self.lakeformation_backend.create_lf_tag(catalog_id, key, values)
        return "{}"

    def get_lf_tag(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        key = self._get_param("TagKey")
        tag_values = self.lakeformation_backend.get_lf_tag(catalog_id, key)
        return json.dumps(
            {"CatalogId": catalog_id, "TagKey": key, "TagValues": tag_values}
        )

    def delete_lf_tag(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        key = self._get_param("TagKey")
        self.lakeformation_backend.delete_lf_tag(catalog_id, key)
        return "{}"

    def list_lf_tags(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        tags = self.lakeformation_backend.list_lf_tags(catalog_id)
        return json.dumps(
            {
                "LFTags": [
                    {"CatalogId": catalog_id, "TagKey": tag, "TagValues": value}
                    for tag, value in tags.items()
                ]
            }
        )

    def update_lf_tag(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        tag_key = self._get_param("TagKey")
        to_delete = self._get_param("TagValuesToDelete")
        to_add = self._get_param("TagValuesToAdd")
        self.lakeformation_backend.update_lf_tag(catalog_id, tag_key, to_delete, to_add)
        return "{}"

    def list_data_cells_filter(self) -> str:
        data_cells = self.lakeformation_backend.list_data_cells_filter()
        return json.dumps({"DataCellsFilters": data_cells})

    def batch_grant_permissions(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        entries = self._get_param("Entries")
        self.lakeformation_backend.batch_grant_permissions(catalog_id, entries)
        return json.dumps({"Failures": []})

    def batch_revoke_permissions(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        entries = self._get_param("Entries")
        self.lakeformation_backend.batch_revoke_permissions(catalog_id, entries)
        return json.dumps({"Failures": []})

    def add_lf_tags_to_resource(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        resource = self._get_param("Resource")
        tags = self._get_param("LFTags")
        failures = self.lakeformation_backend.add_lf_tags_to_resource(
            catalog_id, resource, tags
        )
        return json.dumps({"Failures": failures})

    def get_resource_lf_tags(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        resource = self._get_param("Resource")
        db, table, columns = self.lakeformation_backend.get_resource_lf_tags(
            catalog_id, resource
        )
        resp: Dict[str, Any] = {}
        if db:
            resp["LFTagOnDatabase"] = db
        if table:
            resp["LFTagsOnTable"] = table
        if columns:
            resp["LFTagsOnColumns"] = columns
        return json.dumps(resp)

    def remove_lf_tags_from_resource(self) -> str:
        catalog_id = self._get_param("CatalogId") or self.current_account
        resource = self._get_param("Resource")
        tags = self._get_param("LFTags")
        self.lakeformation_backend.remove_lf_tags_from_resource(
            catalog_id, resource, tags
        )
        return "{}"
