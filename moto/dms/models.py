from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import utcnow
from moto.utilities.utils import get_partition

from .exceptions import (
    InvalidResourceStateFault,
    ResourceAlreadyExistsFault,
    ResourceNotFoundFault,
)
from .utils import filter_tasks


class DatabaseMigrationServiceBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.replication_tasks: Dict[str, "FakeReplicationTask"] = {}
        self.replication_instances: Dict[str, "FakeReplicationInstance"] = {}

    def create_replication_task(
        self,
        replication_task_identifier: str,
        source_endpoint_arn: str,
        target_endpoint_arn: str,
        replication_instance_arn: str,
        migration_type: str,
        table_mappings: str,
        replication_task_settings: str,
    ) -> "FakeReplicationTask":
        """
        The following parameters are not yet implemented:
        CDCStartTime, CDCStartPosition, CDCStopPosition, Tags, TaskData, ResourceIdentifier
        """
        replication_task = FakeReplicationTask(
            replication_task_identifier=replication_task_identifier,
            source_endpoint_arn=source_endpoint_arn,
            target_endpoint_arn=target_endpoint_arn,
            replication_instance_arn=replication_instance_arn,
            migration_type=migration_type,
            table_mappings=table_mappings,
            replication_task_settings=replication_task_settings,
            account_id=self.account_id,
            region_name=self.region_name,
        )

        if self.replication_tasks.get(replication_task.arn):
            raise ResourceAlreadyExistsFault(
                "The resource you are attempting to create already exists."
            )

        self.replication_tasks[replication_task.arn] = replication_task

        return replication_task

    def start_replication_task(
        self, replication_task_arn: str
    ) -> "FakeReplicationTask":
        """
        The following parameters have not yet been implemented:
        StartReplicationTaskType, CDCStartTime, CDCStartPosition, CDCStopPosition
        """
        if not self.replication_tasks.get(replication_task_arn):
            raise ResourceNotFoundFault("Replication task could not be found.")

        return self.replication_tasks[replication_task_arn].start()

    def stop_replication_task(self, replication_task_arn: str) -> "FakeReplicationTask":
        if not self.replication_tasks.get(replication_task_arn):
            raise ResourceNotFoundFault("Replication task could not be found.")

        return self.replication_tasks[replication_task_arn].stop()

    def delete_replication_task(
        self, replication_task_arn: str
    ) -> "FakeReplicationTask":
        if not self.replication_tasks.get(replication_task_arn):
            raise ResourceNotFoundFault("Replication task could not be found.")

        task = self.replication_tasks[replication_task_arn]
        task.delete()
        self.replication_tasks.pop(replication_task_arn)

        return task

    def describe_replication_tasks(
        self, filters: List[Dict[str, Any]], max_records: int
    ) -> Iterable["FakeReplicationTask"]:
        """
        The parameter WithoutSettings has not yet been implemented
        """
        replication_tasks = filter_tasks(self.replication_tasks.values(), filters)

        if max_records and max_records > 0:
            replication_tasks = replication_tasks[:max_records]

        return replication_tasks

    def create_replication_instance(
        self,
        replication_instance_identifier: str,
        replication_instance_class: str,
        allocated_storage: Optional[int] = None,
        vpc_security_group_ids: Optional[List[str]] = None,
        availability_zone: Optional[str] = None,
        replication_subnet_group_identifier: Optional[str] = None,
        preferred_maintenance_window: Optional[str] = None,
        multi_az: Optional[bool] = False,
        engine_version: Optional[str] = None,
        auto_minor_version_upgrade: Optional[bool] = True,
        tags: Optional[List[Dict[str, str]]] = None,
        kms_key_id: Optional[str] = None,
        publicly_accessible: Optional[bool] = True,
        dns_name_servers: Optional[str] = None,
        resource_identifier: Optional[str] = None,
        network_type: Optional[str] = None,
        kerberos_authentication_settings: Optional[Dict[str, str]] = None,
    ) -> "FakeReplicationInstance":
        replication_instance = FakeReplicationInstance(
            replication_instance_identifier=replication_instance_identifier,
            replication_instance_class=replication_instance_class,
            allocated_storage=allocated_storage,
            vpc_security_group_ids=vpc_security_group_ids or [],
            availability_zone=availability_zone,
            replication_subnet_group_identifier=replication_subnet_group_identifier,
            preferred_maintenance_window=preferred_maintenance_window,
            multi_az=multi_az,
            engine_version=engine_version,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            tags=tags or [],
            kms_key_id=kms_key_id,
            publicly_accessible=publicly_accessible,
            dns_name_servers=dns_name_servers,
            resource_identifier=resource_identifier,
            network_type=network_type,
            kerberos_authentication_settings=kerberos_authentication_settings or {},
            account_id=self.account_id,
            region_name=self.region_name,
        )

        if self.replication_instances.get(replication_instance.arn):
            raise ResourceAlreadyExistsFault(
                "The resource you are attempting to create already exists."
            )

        self.replication_instances[replication_instance.arn] = replication_instance

        return replication_instance

    def describe_replication_instances(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_records: Optional[int] = None,
        marker: Optional[str] = None,
    ) -> List["FakeReplicationInstance"]:
        """Get information about replication instances with optional filtering"""
        ### TODO: Implement pagination

        replication_instances = list(self.replication_instances.values())

        if filters:
            for filter_obj in filters:
                filter_name = filter_obj.get("Name", "")
                filter_values = filter_obj.get("Values", [])

                if filter_name == "replication-instance-id":
                    replication_instances = [
                        instance
                        for instance in replication_instances
                        if instance.id in filter_values
                    ]
                elif filter_name == "replication-instance-arn":
                    replication_instances = [
                        instance
                        for instance in replication_instances
                        if instance.arn in filter_values
                    ]
                elif filter_name == "replication-instance-class":
                    replication_instances = [
                        instance
                        for instance in replication_instances
                        if instance.replication_instance_class in filter_values
                    ]
                elif filter_name == "engine-version":
                    replication_instances = [
                        instance
                        for instance in replication_instances
                        if instance.engine_version in filter_values
                    ]

        return replication_instances


class FakeReplicationTask(BaseModel):
    def __init__(
        self,
        replication_task_identifier: str,
        migration_type: str,
        replication_instance_arn: str,
        source_endpoint_arn: str,
        target_endpoint_arn: str,
        table_mappings: str,
        replication_task_settings: str,
        account_id: str,
        region_name: str,
    ):
        self.id = replication_task_identifier
        self.region = region_name
        self.migration_type = migration_type
        self.replication_instance_arn = replication_instance_arn
        self.source_endpoint_arn = source_endpoint_arn
        self.target_endpoint_arn = target_endpoint_arn
        self.table_mappings = table_mappings
        self.replication_task_settings = replication_task_settings

        self.arn = f"arn:{get_partition(region_name)}:dms:{region_name}:{account_id}:task:{self.id}"
        self.status = "creating"

        self.creation_date = utcnow()
        self.start_date: Optional[datetime] = None
        self.stop_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        start_date = self.start_date.isoformat() if self.start_date else None
        stop_date = self.stop_date.isoformat() if self.stop_date else None

        return {
            "ReplicationTaskIdentifier": self.id,
            "SourceEndpointArn": self.source_endpoint_arn,
            "TargetEndpointArn": self.target_endpoint_arn,
            "ReplicationInstanceArn": self.replication_instance_arn,
            "MigrationType": self.migration_type,
            "TableMappings": self.table_mappings,
            "ReplicationTaskSettings": self.replication_task_settings,
            "Status": self.status,
            "ReplicationTaskCreationDate": self.creation_date.isoformat(),
            "ReplicationTaskStartDate": start_date,
            "ReplicationTaskArn": self.arn,
            "ReplicationTaskStats": {
                "FullLoadProgressPercent": 100,
                "ElapsedTimeMillis": 100,
                "TablesLoaded": 1,
                "TablesLoading": 0,
                "TablesQueued": 0,
                "TablesErrored": 0,
                "FreshStartDate": start_date,
                "StartDate": start_date,
                "StopDate": stop_date,
                "FullLoadStartDate": start_date,
                "FullLoadFinishDate": stop_date,
            },
        }

    def ready(self) -> "FakeReplicationTask":
        self.status = "ready"
        return self

    def start(self) -> "FakeReplicationTask":
        self.status = "starting"
        self.start_date = utcnow()
        self.run()
        return self

    def stop(self) -> "FakeReplicationTask":
        if self.status != "running":
            raise InvalidResourceStateFault("Replication task is not running")

        self.status = "stopped"
        self.stop_date = utcnow()
        return self

    def delete(self) -> "FakeReplicationTask":
        self.status = "deleting"
        return self

    def run(self) -> "FakeReplicationTask":
        self.status = "running"
        return self


class FakeReplicationInstance(BaseModel):
    def __init__(
        self,
        replication_instance_identifier: str,
        replication_instance_class: str,
        account_id: str,
        region_name: str,
        allocated_storage: Optional[int] = None,
        vpc_security_group_ids: Optional[List[str]] = None,
        availability_zone: Optional[str] = None,
        replication_subnet_group_identifier: Optional[str] = None,
        preferred_maintenance_window: Optional[str] = None,
        multi_az: Optional[bool] = False,
        engine_version: Optional[str] = None,
        auto_minor_version_upgrade: Optional[bool] = True,
        tags: Optional[List[Dict[str, str]]] = None,
        kms_key_id: Optional[str] = None,
        publicly_accessible: Optional[bool] = True,
        dns_name_servers: Optional[str] = None,
        resource_identifier: Optional[str] = None,
        network_type: Optional[str] = None,
        kerberos_authentication_settings: Optional[Dict[str, str]] = None,
    ):
        self.id = replication_instance_identifier
        self.replication_instance_class = replication_instance_class
        self.region = region_name
        self.allocated_storage = allocated_storage or 50
        self.vpc_security_groups = [
            {"VpcSecurityGroupId": sg_id, "Status": "active"}
            for sg_id in (vpc_security_group_ids or [])
        ]
        self.availability_zone = availability_zone
        self.replication_subnet_group_identifier = replication_subnet_group_identifier
        self.preferred_maintenance_window = preferred_maintenance_window
        self.multi_az = multi_az
        self.engine_version = engine_version
        self.auto_minor_version_upgrade = auto_minor_version_upgrade
        self.tags = tags or []
        self.kms_key_id = kms_key_id
        self.publicly_accessible = publicly_accessible
        self.dns_name_servers = dns_name_servers
        self.resource_identifier = resource_identifier
        self.network_type = network_type
        self.kerberos_authentication_settings = kerberos_authentication_settings or {}
        self.arn = f"arn:{get_partition(region_name)}:dms:{region_name}:{account_id}:rep:{self.id}"
        self.status = "creating"
        self.creation_date = utcnow()
        self.private_ip_addresses = ["10.0.0.1"]
        self.public_ip_addresses = ["54.0.0.1"] if publicly_accessible else []
        self.ipv6_addresses: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        kerberos_settings = None
        if self.kerberos_authentication_settings:
            kerberos_settings = {
                "KeyCacheSecretId": self.kerberos_authentication_settings.get(
                    "KeyCacheSecretId"
                ),
                "KeyCacheSecretIamArn": self.kerberos_authentication_settings.get(
                    "KeyCacheSecretIamArn"
                ),
                "Krb5FileContents": self.kerberos_authentication_settings.get(
                    "Krb5FileContents"
                ),
            }

        subnet_group = None
        if self.replication_subnet_group_identifier:
            subnet_group = {
                "ReplicationSubnetGroupIdentifier": self.replication_subnet_group_identifier,
                "ReplicationSubnetGroupDescription": f"Subnet group for {self.id}",
                "VpcId": "vpc-12345",
                "SubnetGroupStatus": "Complete",
                "Subnets": [
                    {
                        "SubnetIdentifier": "subnet-12345",
                        "SubnetAvailabilityZone": {
                            "Name": self.availability_zone or "us-east-1a"
                        },
                        "SubnetStatus": "Active",
                    }
                ],
                "SupportedNetworkTypes": [self.network_type]
                if self.network_type
                else ["IPV4"],
            }

        return {
            "ReplicationInstanceIdentifier": self.id,
            "ReplicationInstanceClass": self.replication_instance_class,
            "ReplicationInstanceStatus": self.status,
            "AllocatedStorage": self.allocated_storage,
            "InstanceCreateTime": self.creation_date.isoformat(),
            "VpcSecurityGroups": self.vpc_security_groups,
            "AvailabilityZone": self.availability_zone,
            "ReplicationSubnetGroup": subnet_group,
            "PreferredMaintenanceWindow": self.preferred_maintenance_window,
            "PendingModifiedValues": {},
            "MultiAZ": self.multi_az,
            "EngineVersion": self.engine_version,
            "AutoMinorVersionUpgrade": self.auto_minor_version_upgrade,
            "KmsKeyId": self.kms_key_id,
            "ReplicationInstanceArn": self.arn,
            "ReplicationInstancePublicIpAddress": self.public_ip_addresses[0]
            if self.public_ip_addresses
            else None,
            "ReplicationInstancePrivateIpAddress": self.private_ip_addresses[0]
            if self.private_ip_addresses
            else None,
            "ReplicationInstancePublicIpAddresses": self.public_ip_addresses,
            "ReplicationInstancePrivateIpAddresses": self.private_ip_addresses,
            "ReplicationInstanceIpv6Addresses": self.ipv6_addresses,
            "PubliclyAccessible": self.publicly_accessible,
            "SecondaryAvailabilityZone": f"{self.availability_zone}b"
            if self.multi_az
            else None,
            "FreeUntil": None,
            "DnsNameServers": self.dns_name_servers,
            "NetworkType": self.network_type,
            "KerberosAuthenticationSettings": kerberos_settings,
        }


dms_backends = BackendDict(DatabaseMigrationServiceBackend, "dms")
