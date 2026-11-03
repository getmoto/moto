"""Handles incoming backup requests, invokes methods, returns responses."""

import json

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import BackupBackend, backup_backends


class BackupResponse(BaseResponse):
    """Handler for Backup requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="backup")
        self.automated_parameter_parsing = True

    @property
    def backup_backend(self) -> BackupBackend:
        """Return backend instance specific for this region."""
        return backup_backends[self.current_account][self.region]

    def create_backup_plan(self) -> str:
        backup_plan = self._get_param("BackupPlan")
        backup_plan_tags = self._get_param("BackupPlanTags")
        creator_request_id = self._get_param("CreatorRequestId")
        plan = self.backup_backend.create_backup_plan(
            backup_plan=backup_plan,
            backup_plan_tags=backup_plan_tags,
            creator_request_id=creator_request_id,
        )
        return json.dumps(dict(plan.to_dict()))

    def get_backup_plan(self) -> str:
        backup_plan_id = self._get_param("BackupPlanId")
        version_id = self._get_param("VersionId")
        plan = self.backup_backend.get_backup_plan(
            backup_plan_id=backup_plan_id, version_id=version_id
        )
        return json.dumps(dict(plan.to_get_dict()))

    def delete_backup_plan(self) -> str:
        backup_plan_id = self._get_param("BackupPlanId")
        (
            backup_plan_id,
            backup_plan_arn,
            deletion_date,
            version_id,
        ) = self.backup_backend.delete_backup_plan(
            backup_plan_id=backup_plan_id,
        )
        return json.dumps(
            {
                "BackupPlanId": backup_plan_id,
                "BackupPlanArn": backup_plan_arn,
                "DeletionDate": deletion_date,
                "VersionId": version_id,
            }
        )

    def list_backup_plans(self) -> str:
        include_deleted = self._get_bool_param("IncludeDeleted")
        backup_plans_list = self.backup_backend.list_backup_plans(
            include_deleted=include_deleted
        )
        return json.dumps(
            {"BackupPlansList": [p.to_list_dict() for p in backup_plans_list]}
        )

    def create_backup_vault(self) -> str:
        backup_vault_name = self._get_param("BackupVaultName")
        backup_vault_tags = self._get_param("BackupVaultTags")
        encryption_key_arn = self._get_param("EncryptionKeyArn")
        creator_request_id = self._get_param("CreatorRequestId")
        backup_vault = self.backup_backend.create_backup_vault(
            backup_vault_name=backup_vault_name,
            backup_vault_tags=backup_vault_tags,
            encryption_key_arn=encryption_key_arn,
            creator_request_id=creator_request_id,
        )
        return json.dumps(dict(backup_vault.to_dict()))

    def delete_backup_vault(self) -> EmptyResult:
        backup_vault_name = self._get_param("BackupVaultName")
        self.backup_backend.delete_backup_vault(backup_vault_name)
        return EmptyResult()

    def describe_backup_vault(self) -> ActionResult:
        backup_vault_name = self._get_param("BackupVaultName")
        vault = self.backup_backend.describe_backup_vault(backup_vault_name)
        return ActionResult(result=vault)

    def list_backup_vaults(self) -> str:
        backup_vault_list = self.backup_backend.list_backup_vaults()
        return json.dumps(
            {"BackupVaultList": [v.to_list_dict() for v in backup_vault_list]}
        )

    def list_tags(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tags = self.backup_backend.list_tags(
            resource_arn=resource_arn,
        )
        return json.dumps({"Tags": tags})

    def tag_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.backup_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return "{}"

    def untag_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tag_key_list = self._get_param("TagKeyList")
        self.backup_backend.untag_resource(
            resource_arn=resource_arn,
            tag_key_list=tag_key_list,
        )
        return "{}"

    def put_backup_vault_lock_configuration(self) -> str:
        backup_vault_name = self._get_param("BackupVaultName")
        min_retention_days = self._get_param("MinRetentionDays")
        max_retention_days = self._get_param("MaxRetentionDays")
        changeable_for_days = self._get_param("ChangeableForDays")

        self.backup_backend.put_backup_vault_lock_configuration(
            backup_vault_name=backup_vault_name,
            min_retention_days=min_retention_days,
            max_retention_days=max_retention_days,
            changeable_for_days=changeable_for_days,
        )

        return "{}"

    def delete_backup_vault_lock_configuration(self) -> str:
        backup_vault_name = self._get_param("BackupVaultName")

        self.backup_backend.delete_backup_vault_lock_configuration(
            backup_vault_name=backup_vault_name,
        )

        return "{}"

    def list_report_plans(self) -> ActionResult:
        report_plans = self.backup_backend.list_report_plans()
        return ActionResult(result={"ReportPlans": report_plans})

    def create_report_plan(self) -> ActionResult:
        report_plan_name = self._get_param("ReportPlanName")
        report_plan_description = self._get_param("ReportPlanDescription")
        report_delivery_channel = self._get_param("ReportDeliveryChannel")
        report_setting = self._get_param("ReportSetting")
        report_plan = self.backup_backend.create_report_plan(
            report_plan_name=report_plan_name,
            report_plan_description=report_plan_description,
            report_delivery_channel=report_delivery_channel,
            report_setting=report_setting,
        )
        return ActionResult(result=report_plan)

    def describe_report_plan(self) -> ActionResult:
        report_plan_name = self._get_param("ReportPlanName")
        report_plan = self.backup_backend.describe_report_plan(
            report_plan_name=report_plan_name
        )
        return ActionResult(result={"ReportPlan": report_plan})

    def delete_report_plan(self) -> EmptyResult:
        report_plan_name = self._get_param("ReportPlanName")
        self.backup_backend.delete_report_plan(report_plan_name=report_plan_name)
        return EmptyResult()
