from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from botocore.awsrequest import AWSPreparedRequest
from werkzeug.wrappers import Request

from moto import settings
from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backends

from .exceptions import DBParameterGroupNotFoundError, RDSClientError
from .models import RDSBackend, rds_backends


def normalize_request(request: AWSPreparedRequest) -> Request:
    from urllib.parse import urlparse

    parsed_url = urlparse(request.url)
    normalized_request = Request.from_values(
        method=request.method,
        base_url=f"{parsed_url.scheme}://{parsed_url.netloc}",
        path=parsed_url.path,
        query_string=parsed_url.query,
        data=request.body,
        headers=[(k, v) for k, v in request.headers.items()],
    )
    return normalized_request


class RDSResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="rds")

    @property
    def backend(self) -> RDSBackend:
        return rds_backends[self.current_account][self.region]

    @property
    def global_backend(self) -> RDSBackend:
        """Return backend instance of the region that stores Global Clusters"""
        return rds_backends[self.current_account]["us-east-1"]

    def _dispatch(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:
        # return super()._dispatch(request, full_url, headers)
        self.setup_class(request, full_url, headers)

        if isinstance(request, AWSPreparedRequest):
            request = normalize_request(request)

        from .serialize import QuerySerializer
        from .utils import get_service_model

        self.action = request.values["Action"]

        service_model = get_service_model(self.service_name)
        self.operation_model = service_model.operation_model(self.action)

        # parser = QueryParser()
        # parsed = parser.get_parameters(
        #     {"query_params": request.values}, self.operation_model
        # )
        # self.parameters = xform_dict(parsed)

        self.serializer = QuerySerializer(
            self.operation_model,
            {"request-id": "request-id"},
            pretty_print=settings.PRETTIFY_RESPONSES,
        )
        try:
            response = self.call_action()
        except RDSClientError as e:
            response = self.serialize(e)
        return response

    def serialize(self, result: Any) -> TYPE_RESPONSE:
        serialized = self.serializer.serialize_to_response(result)
        return serialized["status_code"], serialized["headers"], serialized["body"]

    def _get_db_kwargs(self) -> Dict[str, Any]:
        args = {
            "auto_minor_version_upgrade": self._get_param("AutoMinorVersionUpgrade"),
            "allocated_storage": self._get_int_param("AllocatedStorage"),
            "availability_zone": self._get_param("AvailabilityZone"),
            "backup_retention_period": self._get_param("BackupRetentionPeriod"),
            "copy_tags_to_snapshot": self._get_bool_param("CopyTagsToSnapshot"),
            "db_instance_class": self._get_param("DBInstanceClass"),
            "db_cluster_identifier": self._get_param("DBClusterIdentifier"),
            "db_instance_identifier": self._get_param("DBInstanceIdentifier"),
            "db_name": self._get_param("DBName"),
            "db_parameter_group_name": self._get_param("DBParameterGroupName"),
            "db_snapshot_identifier": self._get_param("DBSnapshotIdentifier"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "engine": self._get_param("Engine"),
            "engine_version": self._get_param("EngineVersion"),
            "enable_cloudwatch_logs_exports": self._get_params().get(
                "EnableCloudwatchLogsExports"
            ),
            "cloudwatch_logs_exports_config": self._get_params().get(
                "CloudwatchLogsExportConfiguration"
            ),
            "enable_iam_database_authentication": self._get_bool_param(
                "EnableIAMDatabaseAuthentication"
            ),
            "license_model": self._get_param("LicenseModel"),
            "iops": self._get_int_param("Iops"),
            "kms_key_id": self._get_param("KmsKeyId"),
            "master_user_password": self._get_param("MasterUserPassword"),
            "master_username": self._get_param("MasterUsername"),
            "manage_master_user_password": self._get_bool_param(
                "ManageMasterUserPassword"
            ),
            "master_user_secret_kms_key_id": self._get_param(
                "MasterUserSecretKmsKeyId"
            ),
            "rotate_master_user_password": self._get_param("RotateMasterUserPassword"),
            "multi_az": self._get_bool_param("MultiAZ"),
            "option_group_name": self._get_param("OptionGroupName"),
            "port": self._get_param("Port"),
            "preferred_backup_window": self._get_param(
                "PreferredBackupWindow", "13:14-13:44"
            ),
            "preferred_maintenance_window": self._get_param(
                "PreferredMaintenanceWindow", "wed:06:38-wed:07:08"
            ).lower(),
            "publicly_accessible": self._get_bool_param("PubliclyAccessible"),
            "security_groups": self._get_multi_param(
                "DBSecurityGroups.DBSecurityGroupName"
            ),
            "storage_encrypted": self._get_bool_param("StorageEncrypted"),
            "storage_type": self._get_param("StorageType", None),
            "vpc_security_group_ids": self._get_multi_param(
                "VpcSecurityGroupIds.VpcSecurityGroupId"
            ),
            "tags": list(),
            "deletion_protection": self._get_bool_param("DeletionProtection"),
            "apply_immediately": self._get_bool_param("ApplyImmediately"),
        }
        args["tags"] = self.unpack_list_params("Tags", "Tag")
        return args

    def _get_modify_db_cluster_kwargs(self) -> Dict[str, Any]:
        args = {
            "auto_minor_version_upgrade": self._get_param("AutoMinorVersionUpgrade"),
            "allocated_storage": self._get_int_param("AllocatedStorage"),
            "availability_zone": self._get_param("AvailabilityZone"),
            "backup_retention_period": self._get_param("BackupRetentionPeriod"),
            "backtrack_window": self._get_param("BacktrackWindow"),
            "copy_tags_to_snapshot": self._get_bool_param("CopyTagsToSnapshot"),
            "db_instance_class": self._get_param("DBInstanceClass"),
            "db_cluster_identifier": self._get_param("DBClusterIdentifier"),
            "new_db_cluster_identifier": self._get_param("NewDBClusterIdentifier"),
            "db_instance_identifier": self._get_param("DBInstanceIdentifier"),
            "db_name": self._get_param("DBName"),
            "db_parameter_group_name": self._get_param("DBParameterGroupName"),
            "db_cluster_parameter_group_name": self._get_param(
                "DBClusterParameterGroupName"
            ),
            "db_snapshot_identifier": self._get_param("DBSnapshotIdentifier"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "engine": self._get_param("Engine"),
            "engine_version": self._get_param("EngineVersion"),
            "enable_cloudwatch_logs_exports": self._get_params().get(
                "CloudwatchLogsExportConfiguration"
            ),
            "enable_iam_database_authentication": self._get_bool_param(
                "EnableIAMDatabaseAuthentication"
            ),
            "enable_http_endpoint": self._get_bool_param("EnableHttpEndpoint"),
            "license_model": self._get_param("LicenseModel"),
            "iops": self._get_int_param("Iops"),
            "kms_key_id": self._get_param("KmsKeyId"),
            "master_user_password": self._get_param("MasterUserPassword"),
            "master_username": self._get_param("MasterUsername"),
            "manage_master_user_password": self._get_bool_param(
                "ManageMasterUserPassword"
            ),
            "master_user_secret_kms_key_id": self._get_param(
                "MasterUserSecretKmsKeyId"
            ),
            "rotate_master_user_password": self._get_param("RotateMasterUserPassword"),
            "multi_az": self._get_bool_param("MultiAZ"),
            "option_group_name": self._get_param("OptionGroupName"),
            "port": self._get_param("Port"),
            "preferred_backup_window": self._get_param("PreferredBackupWindow"),
            "preferred_maintenance_window": self._get_param(
                "PreferredMaintenanceWindow"
            ),
            "publicly_accessible": self._get_bool_param("PubliclyAccessible"),
            "security_groups": self._get_multi_param(
                "DBSecurityGroups.DBSecurityGroupName"
            ),
            "storage_encrypted": self._get_bool_param("StorageEncrypted"),
            "storage_type": self._get_param("StorageType", None),
            "vpc_security_group_ids": self._get_multi_param(
                "VpcSecurityGroupIds.VpcSecurityGroupId"
            ),
            "tags": list(),
            "deletion_protection": self._get_bool_param("DeletionProtection"),
            "apply_immediately": self._get_bool_param("ApplyImmediately"),
        }
        args["tags"] = self.unpack_list_params("Tags", "Tag")
        return args

    def _get_db_replica_kwargs(self) -> Dict[str, Any]:
        return {
            "auto_minor_version_upgrade": self._get_param("AutoMinorVersionUpgrade"),
            "availability_zone": self._get_param("AvailabilityZone"),
            "db_instance_class": self._get_param("DBInstanceClass"),
            "db_instance_identifier": self._get_param("DBInstanceIdentifier"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "iops": self._get_int_param("Iops"),
            # OptionGroupName
            "port": self._get_param("Port"),
            "publicly_accessible": self._get_bool_param("PubliclyAccessible"),
            "source_db_identifier": self._get_param("SourceDBInstanceIdentifier"),
            "storage_type": self._get_param("StorageType"),
        }

    def _get_option_group_kwargs(self) -> Dict[str, Any]:
        return {
            "major_engine_version": self._get_param("MajorEngineVersion"),
            "description": self._get_param("OptionGroupDescription"),
            "engine_name": self._get_param("EngineName"),
            "name": self._get_param("OptionGroupName"),
        }

    def _get_db_parameter_group_kwargs(self) -> Dict[str, Any]:
        return {
            "description": self._get_param("Description"),
            "family": self._get_param("DBParameterGroupFamily"),
            "name": self._get_param("DBParameterGroupName"),
            "tags": self.unpack_list_params("Tags", "Tag"),
        }

    def _get_db_cluster_kwargs(self) -> Dict[str, Any]:
        params = self._get_params()
        return {
            "availability_zones": self._get_multi_param(
                "AvailabilityZones.AvailabilityZone"
            ),
            "backtrack_window": self._get_int_param("BacktrackWindow"),
            "enable_cloudwatch_logs_exports": params.get("EnableCloudwatchLogsExports"),
            "enable_iam_database_authentication": self._get_bool_param(
                "EnableIAMDatabaseAuthentication"
            ),
            "db_name": self._get_param("DatabaseName"),
            "db_cluster_identifier": self._get_param("DBClusterIdentifier"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "deletion_protection": self._get_bool_param("DeletionProtection"),
            "engine": self._get_param("Engine"),
            "engine_version": self._get_param("EngineVersion"),
            "engine_mode": self._get_param("EngineMode"),
            "allocated_storage": self._get_param("AllocatedStorage"),
            "global_cluster_identifier": self._get_param("GlobalClusterIdentifier"),
            "iops": self._get_param("Iops"),
            "storage_encrypted": self._get_bool_param("StorageEncrypted"),
            "enable_global_write_forwarding": self._get_param(
                "EnableGlobalWriteForwarding"
            ),
            "storage_type": self._get_param("StorageType"),
            "kms_key_id": self._get_param("KmsKeyId"),
            "master_username": self._get_param("MasterUsername"),
            "manage_master_user_password": self._get_bool_param(
                "ManageMasterUserPassword"
            ),
            "master_user_secret_kms_key_id": self._get_param(
                "MasterUserSecretKmsKeyId"
            ),
            "master_user_password": self._get_param("MasterUserPassword"),
            "network_type": self._get_param("NetworkType"),
            "port": self._get_param("Port"),
            "parameter_group": self._get_param("DBClusterParameterGroupName"),
            "db_cluster_instance_class": self._get_param("DBClusterInstanceClass"),
            "enable_http_endpoint": self._get_bool_param("EnableHttpEndpoint"),
            "copy_tags_to_snapshot": self._get_bool_param("CopyTagsToSnapshot"),
            "tags": self.unpack_list_params("Tags", "Tag"),
            "scaling_configuration": self._get_dict_param("ScalingConfiguration."),
            "serverless_v2_scaling_configuration": params.get(
                "ServerlessV2ScalingConfiguration"
            ),
            "replication_source_identifier": self._get_param(
                "ReplicationSourceIdentifier"
            ),
            "vpc_security_group_ids": self.unpack_list_params(
                "VpcSecurityGroupIds", "VpcSecurityGroupId"
            ),
            "preferred_backup_window": self._get_param("PreferredBackupWindow"),
            "backup_retention_period": self._get_param("BackupRetentionPeriod"),
        }

    def _get_export_task_kwargs(self) -> Dict[str, Any]:
        return {
            "export_task_identifier": self._get_param("ExportTaskIdentifier"),
            "source_arn": self._get_param("SourceArn"),
            "s3_bucket_name": self._get_param("S3BucketName"),
            "iam_role_arn": self._get_param("IamRoleArn"),
            "kms_key_id": self._get_param("KmsKeyId"),
            "s3_prefix": self._get_param("S3Prefix"),
            "export_only": self.unpack_list_params("ExportOnly", "member"),
        }

    def _get_event_subscription_kwargs(self) -> Dict[str, Any]:
        return {
            "subscription_name": self._get_param("SubscriptionName"),
            "sns_topic_arn": self._get_param("SnsTopicArn"),
            "source_type": self._get_param("SourceType"),
            "event_categories": self.unpack_list_params(
                "EventCategories", "EventCategory"
            ),
            "source_ids": self.unpack_list_params("SourceIds", "SourceId"),
            "enabled": self._get_bool_param("Enabled"),
            "tags": self.unpack_list_params("Tags", "Tag"),
        }

    def unpack_list_params(self, label: str, child_label: str) -> List[Dict[str, Any]]:
        root = self._get_multi_param_dict(label) or {}
        return root.get(child_label, [])

    def create_db_instance(self) -> TYPE_RESPONSE:
        db_kwargs = self._get_db_kwargs()
        database = self.backend.create_db_instance(db_kwargs)
        result = {"DBInstance": database}
        return self.serialize(result)

    def create_db_instance_read_replica(self) -> TYPE_RESPONSE:
        db_kwargs = self._get_db_replica_kwargs()
        database = self.backend.create_db_instance_read_replica(db_kwargs)
        result = {"DBInstance": database}
        return self.serialize(result)

    def describe_db_instances(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        filters = self._get_multi_param("Filters.Filter.")
        filter_dict = {f["Name"]: f["Values"] for f in filters}
        all_instances = list(
            self.backend.describe_db_instances(
                db_instance_identifier, filters=filter_dict
            )
        )
        instances_resp, next_marker = self._paginate(all_instances)
        result = {
            "DBInstances": instances_resp,
            "Marker": next_marker,
        }
        return self.serialize(result)

    def modify_db_instance(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        db_kwargs = self._get_db_kwargs()
        # NOTE modify_db_instance does not support tags
        del db_kwargs["tags"]
        new_db_instance_identifier = self._get_param("NewDBInstanceIdentifier")
        if new_db_instance_identifier:
            db_kwargs["new_db_instance_identifier"] = new_db_instance_identifier
        database = self.backend.modify_db_instance(db_instance_identifier, db_kwargs)
        result = {"DBInstance": database}
        return self.serialize(result)

    def delete_db_instance(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        db_snapshot_name = self._get_param("FinalDBSnapshotIdentifier")
        if db_snapshot_name is not None:
            self.backend.validate_db_snapshot_identifier(
                db_snapshot_name, parameter_name="FinalDBSnapshotIdentifier"
            )

        database = self.backend.delete_db_instance(
            db_instance_identifier, db_snapshot_name
        )
        result = {"DBInstance": database}
        return self.serialize(result)

    def reboot_db_instance(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        database = self.backend.reboot_db_instance(db_instance_identifier)
        result = {"DBInstance": database}
        return self.serialize(result)

    def create_db_snapshot(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        db_snapshot_identifier = self._get_param("DBSnapshotIdentifier")
        tags = self.unpack_list_params("Tags", "Tag")
        self.backend.validate_db_snapshot_identifier(
            db_snapshot_identifier, parameter_name="DBSnapshotIdentifier"
        )
        snapshot = self.backend.create_db_snapshot(
            db_instance_identifier,
            db_snapshot_identifier,
            tags=tags,
        )
        result = {"DBSnapshot": snapshot}
        return self.serialize(result)

    def copy_db_snapshot(self) -> TYPE_RESPONSE:
        source_snapshot_identifier = self._get_param("SourceDBSnapshotIdentifier")
        target_snapshot_identifier = self._get_param("TargetDBSnapshotIdentifier")
        tags = self.unpack_list_params("Tags", "Tag")
        copy_tags = self._get_param("CopyTags")
        self.backend.validate_db_snapshot_identifier(
            target_snapshot_identifier, parameter_name="TargetDBSnapshotIdentifier"
        )

        snapshot = self.backend.copy_db_snapshot(
            source_snapshot_identifier, target_snapshot_identifier, tags, copy_tags
        )
        result = {"DBSnapshot": snapshot}
        return self.serialize(result)

    def describe_db_snapshots(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        db_snapshot_identifier = self._get_param("DBSnapshotIdentifier")
        filters = self._get_multi_param("Filters.Filter.")
        filter_dict = {f["Name"]: f["Values"] for f in filters}
        snapshots = self.backend.describe_db_snapshots(
            db_instance_identifier, db_snapshot_identifier, filter_dict
        )
        result = {"DBSnapshots": snapshots}
        return self.serialize(result)

    def promote_read_replica(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        db_kwargs = self._get_db_kwargs()
        database = self.backend.promote_read_replica(db_kwargs)
        database = self.backend.modify_db_instance(db_instance_identifier, db_kwargs)
        result = {"DBInstance": database}
        return self.serialize(result)

    def delete_db_snapshot(self) -> TYPE_RESPONSE:
        db_snapshot_identifier = self._get_param("DBSnapshotIdentifier")
        snapshot = self.backend.delete_db_snapshot(db_snapshot_identifier)
        result = {"DBSnapshot": snapshot}
        return self.serialize(result)

    def restore_db_instance_from_db_snapshot(self) -> TYPE_RESPONSE:
        db_snapshot_identifier = self._get_param("DBSnapshotIdentifier")
        db_kwargs = self._get_db_kwargs()
        new_instance = self.backend.restore_db_instance_from_db_snapshot(
            db_snapshot_identifier, db_kwargs
        )
        result = {"DBInstance": new_instance}
        return self.serialize(result)

    def restore_db_instance_to_point_in_time(self) -> TYPE_RESPONSE:
        source_db_identifier = self._get_param("SourceDBInstanceIdentifier")
        target_db_identifier = self._get_param("TargetDBInstanceIdentifier")

        db_kwargs = self._get_db_kwargs()
        new_instance = self.backend.restore_db_instance_to_point_in_time(
            source_db_identifier, target_db_identifier, db_kwargs
        )
        result = {"DBInstance": new_instance}
        return self.serialize(result)

    def list_tags_for_resource(self) -> TYPE_RESPONSE:
        arn = self._get_param("ResourceName")
        tags = self.backend.list_tags_for_resource(arn)
        result = {"TagList": tags}
        return self.serialize(result)

    def add_tags_to_resource(self) -> TYPE_RESPONSE:
        arn = self._get_param("ResourceName")
        tags = self.unpack_list_params("Tags", "Tag")
        self.backend.add_tags_to_resource(arn, tags)
        return self.serialize({})

    def remove_tags_from_resource(self) -> TYPE_RESPONSE:
        arn = self._get_param("ResourceName")
        tag_keys = self.unpack_list_params("TagKeys", "member")
        self.backend.remove_tags_from_resource(arn, tag_keys)  # type: ignore
        return self.serialize({})

    def stop_db_instance(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        db_snapshot_identifier = self._get_param("DBSnapshotIdentifier")
        if db_snapshot_identifier is not None:
            self.backend.validate_db_snapshot_identifier(
                db_snapshot_identifier, parameter_name="DBSnapshotIdentifier"
            )

        database = self.backend.stop_db_instance(
            db_instance_identifier, db_snapshot_identifier
        )
        result = {"DBInstance": database}
        return self.serialize(result)

    def start_db_instance(self) -> TYPE_RESPONSE:
        db_instance_identifier = self._get_param("DBInstanceIdentifier")
        database = self.backend.start_db_instance(db_instance_identifier)
        result = {"DBInstance": database}
        return self.serialize(result)

    def create_db_security_group(self) -> TYPE_RESPONSE:
        group_name = self._get_param("DBSecurityGroupName")
        description = self._get_param("DBSecurityGroupDescription")
        tags = self.unpack_list_params("Tags", "Tag")
        security_group = self.backend.create_db_security_group(
            group_name, description, tags
        )
        result = {"DBSecurityGroup": security_group}
        return self.serialize(result)

    def describe_db_security_groups(self) -> TYPE_RESPONSE:
        security_group_name = self._get_param("DBSecurityGroupName")
        security_groups = self.backend.describe_security_groups(security_group_name)
        result = {"DBSecurityGroups": security_groups}
        return self.serialize(result)

    def delete_db_security_group(self) -> TYPE_RESPONSE:
        security_group_name = self._get_param("DBSecurityGroupName")
        security_group = self.backend.delete_security_group(security_group_name)
        result = {"DBSecurityGroup": security_group}
        return self.serialize(result)

    def authorize_db_security_group_ingress(self) -> TYPE_RESPONSE:
        security_group_name = self._get_param("DBSecurityGroupName")
        cidr_ip = self._get_param("CIDRIP")
        security_group = self.backend.authorize_security_group(
            security_group_name, cidr_ip
        )
        result = {"DBSecurityGroup": security_group}
        return self.serialize(result)

    def create_db_subnet_group(self) -> TYPE_RESPONSE:
        subnet_name = self._get_param("DBSubnetGroupName")
        description = self._get_param("DBSubnetGroupDescription")
        subnet_ids = self._get_multi_param("SubnetIds.SubnetIdentifier")
        tags = self.unpack_list_params("Tags", "Tag")
        subnets = [
            ec2_backends[self.current_account][self.region].get_subnet(subnet_id)
            for subnet_id in subnet_ids
        ]
        subnet_group = self.backend.create_subnet_group(
            subnet_name, description, subnets, tags
        )
        result = {"DBSubnetGroup": subnet_group}
        return self.serialize(result)

    def describe_db_subnet_groups(self) -> TYPE_RESPONSE:
        subnet_name = self._get_param("DBSubnetGroupName")
        subnet_groups = self.backend.describe_db_subnet_groups(subnet_name)
        result = {"DBSubnetGroups": subnet_groups}
        return self.serialize(result)

    def modify_db_subnet_group(self) -> TYPE_RESPONSE:
        subnet_name = self._get_param("DBSubnetGroupName")
        description = self._get_param("DBSubnetGroupDescription")
        subnet_ids = self._get_multi_param("SubnetIds.SubnetIdentifier")
        subnets = [
            ec2_backends[self.current_account][self.region].get_subnet(subnet_id)
            for subnet_id in subnet_ids
        ]
        subnet_group = self.backend.modify_db_subnet_group(
            subnet_name, description, subnets
        )
        result = {"DBSubnetGroup": subnet_group}
        return self.serialize(result)

    def delete_db_subnet_group(self) -> TYPE_RESPONSE:
        subnet_name = self._get_param("DBSubnetGroupName")
        subnet_group = self.backend.delete_subnet_group(subnet_name)
        result = {"DBSubnetGroup": subnet_group}
        return self.serialize(result)

    def create_option_group(self) -> TYPE_RESPONSE:
        kwargs = self._get_option_group_kwargs()
        option_group = self.backend.create_option_group(kwargs)
        result = {"OptionGroup": option_group}
        return self.serialize(result)

    def delete_option_group(self) -> TYPE_RESPONSE:
        kwargs = self._get_option_group_kwargs()
        option_group = self.backend.delete_option_group(kwargs["name"])
        result = {"OptionGroup": option_group}
        return self.serialize(result)

    def describe_option_groups(self) -> TYPE_RESPONSE:
        kwargs = self._get_option_group_kwargs()
        option_groups = self.backend.describe_option_groups(kwargs)
        option_groups, marker = self._paginate(option_groups)
        result = {
            "OptionGroupsList": option_groups,
            "Marker": marker,
        }
        return self.serialize(result)

    def describe_option_group_options(self) -> str:
        engine_name = self._get_param("EngineName")
        major_engine_version = self._get_param("MajorEngineVersion")
        return self.backend.describe_option_group_options(
            engine_name, major_engine_version
        )

    def modify_option_group(self) -> TYPE_RESPONSE:
        option_group_name = self._get_param("OptionGroupName")
        options_to_include = (self._get_multi_param_dict("OptionsToInclude") or {}).get(
            "OptionConfiguration", []
        )
        options_to_remove = self._get_params().get("OptionsToRemove", [])

        option_group = self.backend.modify_option_group(
            option_group_name, options_to_include, options_to_remove
        )
        result = {"OptionGroup": option_group}
        return self.serialize(result)

    def create_db_parameter_group(self) -> TYPE_RESPONSE:
        kwargs = self._get_db_parameter_group_kwargs()
        db_parameter_group = self.backend.create_db_parameter_group(kwargs)
        result = {"DBParameterGroup": db_parameter_group}
        return self.serialize(result)

    def describe_db_parameter_groups(self) -> TYPE_RESPONSE:
        kwargs = self._get_db_parameter_group_kwargs()
        db_parameter_groups = self.backend.describe_db_parameter_groups(kwargs)
        db_parameter_groups, _ = self._paginate(db_parameter_groups)
        result = {"DBParameterGroups": db_parameter_groups}
        return self.serialize(result)

    def modify_db_parameter_group(self) -> TYPE_RESPONSE:
        db_parameter_group_name = self._get_param("DBParameterGroupName")
        db_parameter_group_parameters = self._get_db_parameter_group_parameters()
        db_parameter_group = self.backend.modify_db_parameter_group(
            db_parameter_group_name, db_parameter_group_parameters
        )
        result = {"DBParameterGroupName": db_parameter_group.name}
        return self.serialize(result)

    def _get_db_parameter_group_parameters(self) -> Iterable[Dict[str, Any]]:
        parameter_group_parameters: Dict[str, Any] = defaultdict(dict)
        for param_name, value in self.querystring.items():
            if not param_name.startswith("Parameters.Parameter"):
                continue

            split_param_name = param_name.split(".")
            param_id = split_param_name[2]
            param_setting = split_param_name[3]

            parameter_group_parameters[param_id][param_setting] = value[0]

        return parameter_group_parameters.values()

    def describe_db_parameters(self) -> TYPE_RESPONSE:
        db_parameter_group_name = self._get_param("DBParameterGroupName")
        db_parameter_groups = self.backend.describe_db_parameter_groups(
            {"name": db_parameter_group_name}
        )
        if not db_parameter_groups:
            raise DBParameterGroupNotFoundError(db_parameter_group_name)
        parameters = db_parameter_groups[0].parameters.values()
        result = {"Parameters": parameters}
        return self.serialize(result)

    def delete_db_parameter_group(self) -> TYPE_RESPONSE:
        kwargs = self._get_db_parameter_group_kwargs()
        db_parameter_group = self.backend.delete_db_parameter_group(kwargs["name"])
        return self.serialize(db_parameter_group)

    def describe_db_cluster_parameters(self) -> TYPE_RESPONSE:
        # TODO: This never worked at all...
        db_parameter_group_name = self._get_param("DBParameterGroupName")
        db_parameter_groups = self.backend.describe_db_cluster_parameters()
        if db_parameter_groups is None:
            raise DBParameterGroupNotFoundError(db_parameter_group_name)
        result = {"Parameters": db_parameter_groups}
        return self.serialize(result)

    def create_db_cluster(self) -> TYPE_RESPONSE:
        kwargs = self._get_db_cluster_kwargs()
        cluster = self.backend.create_db_cluster(kwargs)
        result = {"DBCluster": cluster}
        return self.serialize(result)

    def modify_db_cluster(self) -> TYPE_RESPONSE:
        kwargs = self._get_modify_db_cluster_kwargs()
        cluster = self.backend.modify_db_cluster(kwargs)
        result = {"DBCluster": cluster}
        return self.serialize(result)

    def describe_db_clusters(self) -> TYPE_RESPONSE:
        _id = self._get_param("DBClusterIdentifier")
        filters = self._get_multi_param("Filters.Filter.")
        filter_dict = {f["Name"]: f["Values"] for f in filters}
        clusters = self.backend.describe_db_clusters(
            cluster_identifier=_id, filters=filter_dict
        )
        result = {"DBClusters": clusters}
        return self.serialize(result)

    def delete_db_cluster(self) -> TYPE_RESPONSE:
        _id = self._get_param("DBClusterIdentifier")
        snapshot_name = self._get_param("FinalDBSnapshotIdentifier")
        cluster = self.backend.delete_db_cluster(
            cluster_identifier=_id, snapshot_name=snapshot_name
        )
        result = {"DBCluster": cluster}
        return self.serialize(result)

    def start_db_cluster(self) -> TYPE_RESPONSE:
        _id = self._get_param("DBClusterIdentifier")
        cluster = self.backend.start_db_cluster(cluster_identifier=_id)
        result = {"DBCluster": cluster}
        return self.serialize(result)

    def stop_db_cluster(self) -> TYPE_RESPONSE:
        _id = self._get_param("DBClusterIdentifier")
        cluster = self.backend.stop_db_cluster(cluster_identifier=_id)
        result = {"DBCluster": cluster}
        return self.serialize(result)

    def create_db_cluster_snapshot(self) -> TYPE_RESPONSE:
        db_cluster_identifier = self._get_param("DBClusterIdentifier")
        db_snapshot_identifier = self._get_param("DBClusterSnapshotIdentifier")
        tags = self.unpack_list_params("Tags", "Tag")
        snapshot = self.backend.create_db_cluster_snapshot(
            db_cluster_identifier, db_snapshot_identifier, tags=tags
        )
        result = {"DBClusterSnapshot": snapshot}
        return self.serialize(result)

    def copy_db_cluster_snapshot(self) -> TYPE_RESPONSE:
        source_snapshot_identifier = self._get_param(
            "SourceDBClusterSnapshotIdentifier"
        )
        target_snapshot_identifier = self._get_param(
            "TargetDBClusterSnapshotIdentifier"
        )
        tags = self.unpack_list_params("Tags", "Tag")
        snapshot = self.backend.copy_db_cluster_snapshot(
            source_snapshot_identifier, target_snapshot_identifier, tags
        )
        result = {"DBClusterSnapshot": snapshot}
        return self.serialize(result)

    def describe_db_cluster_snapshots(self) -> TYPE_RESPONSE:
        db_cluster_identifier = self._get_param("DBClusterIdentifier")
        db_snapshot_identifier = self._get_param("DBClusterSnapshotIdentifier")
        filters = self._get_multi_param("Filters.Filter.")
        filter_dict = {f["Name"]: f["Values"] for f in filters}
        snapshots = self.backend.describe_db_cluster_snapshots(
            db_cluster_identifier, db_snapshot_identifier, filter_dict
        )
        results = {"DBClusterSnapshots": snapshots}
        return self.serialize(results)

    def delete_db_cluster_snapshot(self) -> TYPE_RESPONSE:
        db_snapshot_identifier = self._get_param("DBClusterSnapshotIdentifier")
        snapshot = self.backend.delete_db_cluster_snapshot(db_snapshot_identifier)
        result = {"DBClusterSnapshot": snapshot}
        return self.serialize(result)

    def restore_db_cluster_from_snapshot(self) -> TYPE_RESPONSE:
        db_snapshot_identifier = self._get_param("SnapshotIdentifier")
        db_kwargs = self._get_db_cluster_kwargs()
        new_cluster = self.backend.restore_db_cluster_from_snapshot(
            db_snapshot_identifier, db_kwargs
        )
        result = {"DBCluster": new_cluster}
        return self.serialize(result)

    def start_export_task(self) -> TYPE_RESPONSE:
        kwargs = self._get_export_task_kwargs()
        export_task = self.backend.start_export_task(kwargs)
        return self.serialize(export_task)

    def cancel_export_task(self) -> TYPE_RESPONSE:
        export_task_identifier = self._get_param("ExportTaskIdentifier")
        export_task = self.backend.cancel_export_task(export_task_identifier)
        return self.serialize(export_task)

    def describe_export_tasks(self) -> TYPE_RESPONSE:
        export_task_identifier = self._get_param("ExportTaskIdentifier")
        tasks = self.backend.describe_export_tasks(export_task_identifier)
        result = {"ExportTasks": tasks}
        return self.serialize(result)

    def create_event_subscription(self) -> TYPE_RESPONSE:
        kwargs = self._get_event_subscription_kwargs()
        subscription = self.backend.create_event_subscription(kwargs)
        result = {"EventSubscription": subscription}
        return self.serialize(result)

    def delete_event_subscription(self) -> TYPE_RESPONSE:
        subscription_name = self._get_param("SubscriptionName")
        subscription = self.backend.delete_event_subscription(subscription_name)
        result = {"EventSubscription": subscription}
        return self.serialize(result)

    def describe_event_subscriptions(self) -> TYPE_RESPONSE:
        subscription_name = self._get_param("SubscriptionName")
        subscriptions = self.backend.describe_event_subscriptions(subscription_name)
        result = {"EventSubscriptionsList": subscriptions}
        return self.serialize(result)

    def describe_orderable_db_instance_options(self) -> TYPE_RESPONSE:
        engine = self._get_param("Engine")
        engine_version = self._get_param("EngineVersion")
        options = self.backend.describe_orderable_db_instance_options(
            engine, engine_version
        )
        result = {"OrderableDBInstanceOptions": options}
        return self.serialize(result)

    def describe_global_clusters(self) -> TYPE_RESPONSE:
        clusters = self.global_backend.describe_global_clusters()
        result = {"GlobalClusters": clusters}
        return self.serialize(result)

    def create_global_cluster(self) -> TYPE_RESPONSE:
        params = self._get_params()
        cluster = self.global_backend.create_global_cluster(
            global_cluster_identifier=params["GlobalClusterIdentifier"],
            source_db_cluster_identifier=params.get("SourceDBClusterIdentifier"),
            engine=params.get("Engine"),
            engine_version=params.get("EngineVersion"),
            storage_encrypted=params.get("StorageEncrypted"),
            deletion_protection=params.get("DeletionProtection"),
        )
        result = {"GlobalCluster": cluster}
        return self.serialize(result)

    def delete_global_cluster(self) -> TYPE_RESPONSE:
        params = self._get_params()
        cluster = self.global_backend.delete_global_cluster(
            global_cluster_identifier=params["GlobalClusterIdentifier"],
        )
        result = {"GlobalCluster": cluster}
        return self.serialize(result)

    def remove_from_global_cluster(self) -> TYPE_RESPONSE:
        params = self._get_params()
        global_cluster = self.backend.remove_from_global_cluster(
            global_cluster_identifier=params["GlobalClusterIdentifier"],
            db_cluster_identifier=params["DbClusterIdentifier"],
        )
        result = {"GlobalCluster": global_cluster}
        return self.serialize(result)

    def create_db_cluster_parameter_group(self) -> TYPE_RESPONSE:
        group_name = self._get_param("DBClusterParameterGroupName")
        family = self._get_param("DBParameterGroupFamily")
        desc = self._get_param("Description")
        db_cluster_parameter_group = self.backend.create_db_cluster_parameter_group(
            group_name=group_name,
            family=family,
            description=desc,
        )
        result = {"DBClusterParameterGroup": db_cluster_parameter_group}
        return self.serialize(result)

    def describe_db_cluster_parameter_groups(self) -> TYPE_RESPONSE:
        group_name = self._get_param("DBClusterParameterGroupName")
        db_parameter_groups = self.backend.describe_db_cluster_parameter_groups(
            group_name=group_name,
        )
        result = {"DBClusterParameterGroups": db_parameter_groups}
        return self.serialize(result)

    def delete_db_cluster_parameter_group(self) -> TYPE_RESPONSE:
        group_name = self._get_param("DBClusterParameterGroupName")
        self.backend.delete_db_cluster_parameter_group(
            group_name=group_name,
        )
        return self.serialize({})

    def promote_read_replica_db_cluster(self) -> TYPE_RESPONSE:
        db_cluster_identifier = self._get_param("DBClusterIdentifier")
        cluster = self.backend.promote_read_replica_db_cluster(db_cluster_identifier)
        result = {"DBCluster": cluster}
        return self.serialize(result)

    def describe_db_snapshot_attributes(self) -> TYPE_RESPONSE:
        params = self._get_params()
        db_snapshot_identifier = params["DBSnapshotIdentifier"]
        db_snapshot_attributes_result = self.backend.describe_db_snapshot_attributes(
            db_snapshot_identifier=db_snapshot_identifier,
        )
        result = {
            "DBSnapshotAttributesResult": {
                "DBSnapshotIdentifier": db_snapshot_identifier,
                "DBSnapshotAttributes": db_snapshot_attributes_result,
            }
        }
        return self.serialize(result)

    def modify_db_snapshot_attribute(self) -> TYPE_RESPONSE:
        params = self._get_params()
        db_snapshot_identifier = params["DBSnapshotIdentifier"]
        db_snapshot_attributes_result = self.backend.modify_db_snapshot_attribute(
            db_snapshot_identifier=db_snapshot_identifier,
            attribute_name=params["AttributeName"],
            values_to_add=params.get("ValuesToAdd"),
            values_to_remove=params.get("ValuesToRemove"),
        )
        result = {
            "DBSnapshotAttributesResult": {
                "DBSnapshotIdentifier": db_snapshot_identifier,
                "DBSnapshotAttributes": db_snapshot_attributes_result,
            }
        }
        return self.serialize(result)

    def describe_db_cluster_snapshot_attributes(self) -> TYPE_RESPONSE:
        params = self._get_params()
        db_cluster_snapshot_identifier = params["DBClusterSnapshotIdentifier"]
        db_cluster_snapshot_attributes_result = (
            self.backend.describe_db_cluster_snapshot_attributes(
                db_cluster_snapshot_identifier=db_cluster_snapshot_identifier,
            )
        )
        result = {
            "DBClusterSnapshotAttributesResult": {
                "DBClusterSnapshotIdentifier": db_cluster_snapshot_identifier,
                "DBClusterSnapshotAttributes": db_cluster_snapshot_attributes_result,
            }
        }
        return self.serialize(result)

    def modify_db_cluster_snapshot_attribute(self) -> TYPE_RESPONSE:
        params = self._get_params()
        db_cluster_snapshot_identifier = params["DBClusterSnapshotIdentifier"]
        db_cluster_snapshot_attributes_result = (
            self.backend.modify_db_cluster_snapshot_attribute(
                db_cluster_snapshot_identifier=db_cluster_snapshot_identifier,
                attribute_name=params["AttributeName"],
                values_to_add=params.get("ValuesToAdd"),
                values_to_remove=params.get("ValuesToRemove"),
            )
        )
        result = {
            "DBClusterSnapshotAttributesResult": {
                "DBClusterSnapshotIdentifier": db_cluster_snapshot_identifier,
                "DBClusterSnapshotAttributes": db_cluster_snapshot_attributes_result,
            }
        }
        return self.serialize(result)

    def describe_db_proxies(self) -> TYPE_RESPONSE:
        params = self._get_params()
        db_proxy_name = params.get("DBProxyName")
        # filters = params.get("Filters")
        marker = params.get("Marker")
        db_proxies = self.backend.describe_db_proxies(
            db_proxy_name=db_proxy_name,
            # filters=filters,
        )
        result = {
            "DBProxies": db_proxies,
            "Marker": marker,
        }
        return self.serialize(result)

    def create_db_proxy(self) -> TYPE_RESPONSE:
        params = self._get_params()
        db_proxy_name = params["DBProxyName"]
        engine_family = params["EngineFamily"]
        auth = params["Auth"]
        role_arn = params["RoleArn"]
        vpc_subnet_ids = params["VpcSubnetIds"]
        vpc_security_group_ids = params.get("VpcSecurityGroupIds")
        require_tls = params.get("RequireTLS")
        idle_client_timeout = params.get("IdleClientTimeout")
        debug_logging = params.get("DebugLogging")
        tags = self.unpack_list_params("Tags", "Tag")
        db_proxy = self.backend.create_db_proxy(
            db_proxy_name=db_proxy_name,
            engine_family=engine_family,
            auth=auth,
            role_arn=role_arn,
            vpc_subnet_ids=vpc_subnet_ids,
            vpc_security_group_ids=vpc_security_group_ids,
            require_tls=require_tls,
            idle_client_timeout=idle_client_timeout,
            debug_logging=debug_logging,
            tags=tags,
        )
        result = {"DBProxy": db_proxy}
        return self.serialize(result)

    def register_db_proxy_targets(self) -> TYPE_RESPONSE:
        db_proxy_name = self._get_param("DBProxyName")
        target_group_name = self._get_param("TargetGroupName")
        db_cluster_identifiers = self._get_params().get("DBClusterIdentifiers", [])
        db_instance_identifiers = self._get_params().get("DBInstanceIdentifiers", [])
        targets = self.backend.register_db_proxy_targets(
            db_proxy_name=db_proxy_name,
            target_group_name=target_group_name,
            db_cluster_identifiers=db_cluster_identifiers,
            db_instance_identifiers=db_instance_identifiers,
        )
        result = {"DBProxyTargets": targets}
        return self.serialize(result)

    def deregister_db_proxy_targets(self) -> TYPE_RESPONSE:
        db_proxy_name = self._get_param("DBProxyName")
        target_group_name = self._get_param("TargetGroupName")
        db_cluster_identifiers = self._get_params().get("DBClusterIdentifiers", [])
        db_instance_identifiers = self._get_params().get("DBInstanceIdentifiers", [])
        self.backend.deregister_db_proxy_targets(
            db_proxy_name=db_proxy_name,
            target_group_name=target_group_name,
            db_cluster_identifiers=db_cluster_identifiers,
            db_instance_identifiers=db_instance_identifiers,
        )
        return self.serialize({})

    def describe_db_proxy_targets(self) -> TYPE_RESPONSE:
        proxy_name = self._get_param("DBProxyName")
        targets = self.backend.describe_db_proxy_targets(proxy_name=proxy_name)
        result = {"Targets": targets}
        return self.serialize(result)

    def delete_db_proxy(self) -> TYPE_RESPONSE:
        proxy_name = self._get_param("DBProxyName")
        proxy = self.backend.delete_db_proxy(proxy_name=proxy_name)
        result = {"DBProxy": proxy}
        return self.serialize(result)

    def describe_db_proxy_target_groups(self) -> TYPE_RESPONSE:
        proxy_name = self._get_param("DBProxyName")
        groups = self.backend.describe_db_proxy_target_groups(proxy_name=proxy_name)
        result = {"TargetGroups": groups}
        return self.serialize(result)

    def modify_db_proxy_target_group(self) -> TYPE_RESPONSE:
        proxy_name = self._get_param("DBProxyName")
        config = self._get_params().get("ConnectionPoolConfig", {})
        group = self.backend.modify_db_proxy_target_group(
            proxy_name=proxy_name, config=config
        )
        result = {"DBProxyTargetGroup": group}
        return self.serialize(result)

    def _paginate(self, resources: List[Any]) -> Tuple[List[Any], Optional[str]]:
        from moto.rds.exceptions import InvalidParameterValue

        marker = self._get_param("Marker")
        # Default was originally set to 50 instead of 100 for ease of testing.  Should fix.
        page_size = self._get_int_param("MaxRecords", 50)
        if page_size < 20 or page_size > 100:
            msg = (
                f"Invalid value {page_size} for MaxRecords. Must be between 20 and 100"
            )
            raise InvalidParameterValue(msg)
        all_resources = list(resources)
        all_ids = [resource.name for resource in all_resources]
        if marker:
            start = all_ids.index(marker) + 1
        else:
            start = 0
        paginated_resources = all_resources[start : start + page_size]
        next_marker = None
        if len(all_resources) > start + page_size:
            next_marker = paginated_resources[-1].name
        return paginated_resources, next_marker
