import json

from moto.core.responses import BaseResponse

from .models import DatabaseMigrationServiceBackend, dms_backends


class DatabaseMigrationServiceResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="dms")

    @property
    def dms_backend(self) -> DatabaseMigrationServiceBackend:
        return dms_backends[self.current_account][self.region]

    def create_replication_task(self) -> str:
        replication_task_identifier = self._get_param("ReplicationTaskIdentifier")
        source_endpoint_arn = self._get_param("SourceEndpointArn")
        target_endpoint_arn = self._get_param("TargetEndpointArn")
        replication_instance_arn = self._get_param("ReplicationInstanceArn")
        migration_type = self._get_param("MigrationType")
        table_mappings = self._get_param("TableMappings")
        replication_task_settings = self._get_param("ReplicationTaskSettings")
        replication_task = self.dms_backend.create_replication_task(
            replication_task_identifier=replication_task_identifier,
            source_endpoint_arn=source_endpoint_arn,
            target_endpoint_arn=target_endpoint_arn,
            replication_instance_arn=replication_instance_arn,
            migration_type=migration_type,
            table_mappings=table_mappings,
            replication_task_settings=replication_task_settings,
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def start_replication_task(self) -> str:
        replication_task_arn = self._get_param("ReplicationTaskArn")
        replication_task = self.dms_backend.start_replication_task(
            replication_task_arn=replication_task_arn
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def stop_replication_task(self) -> str:
        replication_task_arn = self._get_param("ReplicationTaskArn")
        replication_task = self.dms_backend.stop_replication_task(
            replication_task_arn=replication_task_arn
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def delete_replication_task(self) -> str:
        replication_task_arn = self._get_param("ReplicationTaskArn")
        replication_task = self.dms_backend.delete_replication_task(
            replication_task_arn=replication_task_arn
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def describe_replication_tasks(self) -> str:
        filters = self._get_list_prefix("Filters.member")
        max_records = self._get_int_param("MaxRecords")
        replication_tasks = self.dms_backend.describe_replication_tasks(
            filters=filters, max_records=max_records
        )

        return json.dumps(
            dict(ReplicationTasks=[t.to_dict() for t in replication_tasks])
        )

    def create_replication_instance(self) -> str:
        params = json.loads(self.body)
        replication_instance_identifier = params.get("ReplicationInstanceIdentifier")
        allocated_storage = params.get("AllocatedStorage")
        replication_instance_class = params.get("ReplicationInstanceClass")
        vpc_security_group_ids = self._get_param("VpcSecurityGroupIds")
        if vpc_security_group_ids:
            # If the parameter is directly available, use it
            vpc_security_group_ids = (
                vpc_security_group_ids.split(",")
                if isinstance(vpc_security_group_ids, str)
                else [vpc_security_group_ids]
            )
        else:
            # If we need to extract from list prefix, get string values
            vpc_security_group_list = self._get_list_prefix(
                "VpcSecurityGroupIds.member"
            )
            vpc_security_group_ids = (
                [
                    sg_id.get("VpcSecurityGroupId", "")
                    for sg_id in vpc_security_group_list
                ]
                if vpc_security_group_list
                else None
            )

        availability_zone = params.get("AvailabilityZone")
        replication_subnet_group_identifier = params.get(
            "ReplicationSubnetGroupIdentifier"
        )
        preferred_maintenance_window = params.get("PreferredMaintenanceWindow")
        multi_az = params.get("MultiAZ")
        engine_version = params.get("EngineVersion")
        auto_minor_version_upgrade = params.get("AutoMinorVersionUpgrade")
        tags = self._get_list_prefix("Tags.member")
        kms_key_id = params.get("KmsKeyId")
        publicly_accessible = params.get("PubliclyAccessible")
        dns_name_servers = params.get("DnsNameServers")
        resource_identifier = params.get("ResourceIdentifier")
        network_type = params.get("NetworkType")
        kerberos_authentication_settings = params.get("KerberosAuthenticationSettings")
        replication_instance = self.dms_backend.create_replication_instance(
            replication_instance_identifier=replication_instance_identifier,
            allocated_storage=allocated_storage,
            replication_instance_class=replication_instance_class,
            vpc_security_group_ids=vpc_security_group_ids,
            availability_zone=availability_zone,
            replication_subnet_group_identifier=replication_subnet_group_identifier,
            preferred_maintenance_window=preferred_maintenance_window,
            multi_az=multi_az,
            engine_version=engine_version,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            tags=tags,
            kms_key_id=kms_key_id,
            publicly_accessible=publicly_accessible,
            dns_name_servers=dns_name_servers,
            resource_identifier=resource_identifier,
            network_type=network_type,
            kerberos_authentication_settings=kerberos_authentication_settings,
        )
        return json.dumps({"ReplicationInstance": replication_instance.to_dict()})

    def describe_replication_instances(self) -> str:
        data = json.loads(self.body)
        filters = data.get("Filters", [])
        max_records = data.get("MaxRecords")
        marker = data.get("Marker")

        replication_instances = self.dms_backend.describe_replication_instances(
            filters=filters,
            max_records=max_records,
            marker=marker,
        )

        instances_dict = [i.to_dict() for i in replication_instances]

        # TODO: Add Marker (optional) to the response
        return json.dumps({"ReplicationInstances": instances_dict})
