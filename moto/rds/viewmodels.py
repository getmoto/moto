# mypy: disable-error-code="misc"
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import (
    DBCluster,
    DBClusterSnapshot,
    DBInstance,
    DBSecurityGroup,
    DBSnapshot,
    DBSubnetGroup,
    GlobalCluster,
    OptionGroup,
    ProxyTarget,
    ProxyTargetGroup,
)

# We use this dict to alias AWS model attributes to Moto RDS model attributes
# This is just temporary.  Eventually we will update the RDS model attributes
# to match AWS.
SERIALIZATION_ALIASES = {
    "CustSubscriptionId": ["subscription_name"],
    "DatabaseName": ["db_name"],
    "DbClusterResourceId": ["resource_id"],
    "DBClusterSnapshotArn": ["snapshot_arn"],
    "DBClusterSnapshotIdentifier": ["snapshot_id"],
    "DBInstanceDTO": ["DBInstance"],
    "DbInstancePort": ["port"],
    "DBParameterGroupDTO": ["DBParameterGroup"],
    "DBParameterGroupFamily": ["family"],
    "DBProxyName": ["proxy_name"],
    "DBSecurityGroupDTO": ["DBSecurityGroup"],
    "DBSnapshotArn": ["snapshot_arn"],
    "DBSnapshotDTO": ["DBSnapshot"],
    "DBSnapshotIdentifier": ["snapshot_id"],
    "DBSubnetGroup": ["subnet_group"],
    "DBSubnetGroupName": ["subnet_name"],
    "DBSubnetGroupDTO": ["DBSubnetGroup"],
    "EC2SecurityGroupId": ["id"],
    "EC2SecurityGroupName": ["name"],
    "EC2SubnetGroupOwnerId": ["owner_id"],
    "EventCategoriesList": ["event_categories"],
    "HttpEndpointEnabled": ["enable_http_endpoint"],
    "IAMDatabaseAuthenticationEnabled": [
        "enable_iam_database_authentication",
        "iam_auth",
    ],
    "MultiAZ": ["is_multi_az"],
    "OptionGroupDTO": ["OptionGroup"],
    "OriginalSnapshotCreateTime": ["original_created_at"],
    "ReadReplicaSourceDBInstanceIdentifier": ["source_db_identifier"],
    "S3Bucket": ["s3_bucket_name"],
    "SourceIdsList": ["source_ids"],
    "SnapshotCreateTime": ["created_at"],
    "TagList": ["tags"],
    "TargetGroupArn": ["arn"],
    "TargetGroupName": ["group_name"],
}


class Engine:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version

    def __str__(self) -> str:
        return self.name


class DBInstanceDTO:
    def __init__(self, instance: DBInstance) -> None:
        self.db_instance = instance

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        return self.db_instance.__getattribute__(name)

    @property
    def engine(self) -> Engine:
        return Engine(self.db_instance.engine, self.db_instance.engine_version)

    @property
    def master_user_secret(self) -> Optional[Dict[str, Any]]:
        secret_dict = self.db_instance.master_user_secret()
        manage_master_user_password = self.db_instance.manage_master_user_password
        return secret_dict if manage_master_user_password else None

    @property
    def vpc_security_group_membership_list(self) -> List[Dict[str, Any]]:
        groups = [
            {
                "Status": "active",
                "VpcSecurityGroupId": id_,
            }
            for id_ in self.db_instance.vpc_security_group_ids
        ]
        return groups

    @property
    def db_parameter_group_status_list(self) -> Any:
        groups = self.db_instance.db_parameter_groups()
        for group in groups:
            # this is hideous
            setattr(group, "ParameterApplyStatus", "in-sync")
        return groups

    @property
    def db_security_group_membership_list(self) -> List[Dict[str, Any]]:
        groups = [
            {
                "Status": "active",
                "DBSecurityGroupName": group,
            }
            for group in self.db_instance.security_groups
        ]
        return groups

    @property
    def endpoint(self) -> Dict[str, Any]:
        return {
            "Address": self.db_instance.address,
            "Port": self.db_instance.port,
        }

    @property
    def option_group_memberships(self) -> List[Dict[str, Any]]:
        groups = [
            {
                "OptionGroupName": self.db_instance.option_group_name,
                "Status": "in-sync",
            }
        ]
        return groups

    @property
    def read_replica_db_instance_identifiers(self) -> List[str]:
        return [replica for replica in self.db_instance.replicas]


class DBProxyTargetGroupDTO:
    def __init__(self, group: ProxyTargetGroup) -> None:
        self.group = group

    @property
    def is_default(self) -> bool:
        return True

    @property
    def status(self) -> str:
        return "available"

    @property
    def connection_pool_config(self) -> Dict[str, Any]:
        return {
            "MaxConnectionsPercent": self.group.max_connections,
            "MaxIdleConnectionsPercent": self.group.max_idle_connections,
            "ConnectionBorrowTimeout": self.group.borrow_timeout,
            "SessionPinningFilters": [
                filter_ for filter_ in self.group.session_pinning_filters
            ],
        }

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        return self.group.__getattribute__(name)


class DBProxyTargetDTO:
    def __init__(self, target: ProxyTarget, registering: bool = False) -> None:
        self.target = target
        self.registering = registering

    # terrible hack because get_value tries to pull arn and calls .name which isn't there
    @property
    def target_arn(self) -> str | None:
        return None

    @property
    def role(self) -> None:
        # We do this because the model right now sets it to "",
        # which does get serialized...
        return None

    @property
    def port(self) -> int:
        return 5432

    @property
    def target_health(self) -> Dict[str, Any]:
        return {
            "State": "REGISTERING" if self.registering else "AVAILABLE",
        }

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        return self.target.__getattribute__(name)


class OptionGroupDTO:
    def __init__(self, group: OptionGroup) -> None:
        self.group = group

    @property
    def options(self) -> List[Dict[str, Any]]:
        return [
            {
                "OptionName": name,
                "OptionSettings": [
                    {
                        "Name": setting.get("Name"),
                        "Value": setting.get("Value"),
                    }
                    for setting in option_settings
                ],
            }
            for name, option_settings in self.group.options.items()
        ]

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        return self.group.__getattribute__(name)


class DBSubnetGroupDTO:
    def __init__(self, subnet_group: DBSubnetGroup) -> None:
        self.subnet_group = subnet_group

    @property
    def subnets(self) -> List[Dict[str, Any]]:
        subnets = [
            {
                "SubnetStatus": "Active",
                "SubnetIdentifier": subnet.id,
                "SubnetAvailabilityZone": {
                    "Name": subnet.availability_zone,
                    "ProvisionedIopsCapable": False,
                },
            }
            for subnet in self.subnet_group.subnets
        ]
        return subnets

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        return self.subnet_group.__getattribute__(name)


class DBSecurityGroupDTO:
    def __init__(self, security_group: DBSecurityGroup) -> None:
        self.security_group = security_group

    @property
    def ip_ranges(self) -> List[Dict[str, Any]]:
        ranges = [
            {
                "CIDRIP": ip_range,
                "Status": "authorized",
            }
            for ip_range in self.security_group.ip_ranges
        ]
        return ranges

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        return self.security_group.__getattribute__(name)


class DBSnapshotDTO:
    def __init__(self, snapshot: DBSnapshot) -> None:
        self.db_snapshot = snapshot
        self.db_instance = snapshot.database

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        try:
            return self.db_snapshot.__getattribute__(name)
        except AttributeError:
            pass
        return self.db_instance.__getattribute__(name)

    @property
    def dbi_resource_id(self) -> str:
        return self.db_instance.dbi_resource_id

    @property
    def engine(self) -> str:
        return self.db_instance.engine


class GlobalClusterDTO:
    def __init__(self, cluster: GlobalCluster) -> None:
        self.cluster = cluster

    @property
    def status(self) -> str:
        return "available"  # this is hardcoded in GlobalCluster.to_xml

    @property
    def global_cluster_members(self) -> List[Dict[str, Any]]:
        readers = [
            reader.db_cluster_arn
            for reader in self.cluster.members
            if not reader.is_writer
        ]
        members = [
            {
                "DBClusterArn": member.db_cluster_arn,
                "IsWriter": True if member.is_writer else False,
                "DBClusterParameterGroupStatus": "in-sync",
                "PromotionTier": 1,
                # I don't think this is correct, but current test assert on it being empty for non writers
                "Readers": [],
            }
            for member in self.members
        ]
        for member in members:
            if member["IsWriter"]:
                member["Readers"] = readers
            else:
                member["GlobalWriteForwardingStatus"] = "disabled"
        return members

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.cluster.__getattribute__(name)


class DBClusterDTO:
    def __init__(self, cluster: DBCluster, creating: bool = False) -> None:
        self.cluster = cluster
        self.creating = creating

    def master_user_secret(self) -> Optional[Dict[str, Any]]:
        secret_dict = self.cluster.master_user_secret()
        manage_master_user_password = self.cluster.manage_master_user_password
        return secret_dict if manage_master_user_password else None

    @property
    def db_cluster_parameter_group(self) -> str:
        return self.cluster.parameter_group

    @property
    def status(self) -> str:
        return "creating" if self.creating else self.cluster.status

    @property
    def associated_roles(self) -> List[Dict[str, Any]]:
        return []

    @property
    def scaling_configuration_info(self) -> Dict[str, Any]:
        configuration = self.cluster.scaling_configuration or {}
        info = {
            "MinCapacity": configuration.get("min_capacity"),
            "MaxCapacity": configuration.get("max_capacity"),
            "AutoPause": configuration.get("auto_pause"),
            "SecondsUntilAutoPause": configuration.get("seconds_until_auto_pause"),
            "TimeoutAction": configuration.get("timeout_action"),
            "SecondsBeforeTimeout": configuration.get("seconds_before_timeout"),
        }
        return info

    @property
    def vpc_security_groups(self) -> List[Dict[str, Any]]:
        groups = [
            {"VpcSecurityGroupId": sg_id, "Status": "active"}
            for sg_id in self.cluster.vpc_security_group_ids
        ]
        return groups

    @property
    def domain_memberships(self) -> List[str]:
        return []

    @property
    def cross_account_clone(self) -> bool:
        return False

    @property
    def global_write_forwarding_requested(self) -> bool:
        # This does not appear to be in the standard response for any clusters
        # Docs say it's only for a secondary cluster in aurora global database...
        return True if self.cluster.global_write_forwarding_requested else False

    @property
    def db_cluster_members(self) -> List[Dict[str, Any]]:
        members = [
            {
                "DBInstanceIdentifier": member,
                "IsClusterWriter": True,
                "DBClusterParameterGroupStatus": "in-sync",
                "PromotionTier": 1,
            }
            for member in self.cluster_members
        ]
        return members

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.cluster.__getattribute__(name)


class DBClusterSnapshotDTO:
    def __init__(self, snapshot: DBClusterSnapshot) -> None:
        self.snapshot = snapshot
        self.cluster = DBClusterDTO(snapshot.cluster)

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        try:
            return self.snapshot.__getattribute__(name)
        except AttributeError:
            pass
        return self.cluster.__getattribute__(name)
