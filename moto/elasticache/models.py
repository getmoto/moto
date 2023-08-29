from datetime import datetime
from typing import List, Optional, Dict, Any

from moto.core import BaseBackend, BackendDict, BaseModel

from .exceptions import UserAlreadyExists, UserNotFound


class User(BaseModel):
    def __init__(
        self,
        account_id: str,
        region: str,
        user_id: str,
        user_name: str,
        access_string: str,
        engine: str,
        no_password_required: bool,
        passwords: Optional[List[str]] = None,
    ):
        self.id = user_id
        self.name = user_name
        self.engine = engine
        self.passwords = passwords or []
        self.access_string = access_string
        self.no_password_required = no_password_required
        self.status = "active"
        self.minimum_engine_version = "6.0"
        self.usergroupids: List[str] = []
        self.region = region
        self.arn = f"arn:aws:elasticache:{self.region}:{account_id}:user:{self.id}"


class CacheCluster(BaseModel):
    def __init__(
            self,
            cache_cluster_id: str,
            replication_group_id: Optional[str],
            az_mode: Optional[str],
            preferred_availability_zone: Optional[str],
            num_cache_nodes: Optional[int],
            cache_node_type: Optional[str],
            engine: Optional[str],
            engine_version: Optional[str],
            cache_parameter_group_name: Optional[str],
            cache_subnet_group_name: Optional[str],
            transit_encryption_enabled: Optional[bool],
            network_type: Optional[str],
            ip_discovery: Optional[str],
            snapshot_name: Optional[str],
            preferred_maintenance_window: Optional[str],
            port: Optional[int],
            notification_topic_arn: Optional[str],
            auto_minor_version_upgrade: Optional[bool],
            snapshot_retention_limit: Optional[int],
            snapshot_window: Optional[str],
            auth_token: Optional[str],
            outpost_mode: Optional[str],
            preferred_outpost_arn: Optional[str],
            preferred_availability_zones: Optional[List[str]],
            cache_security_group_names: Optional[List[str]],
            security_group_ids: Optional[List[str]],
            tags: Optional[Dict[str, str]],
            snapshot_arns: Optional[List[str]],
            preferred_outpost_arns: Optional[List[str]],
            log_delivery_configurations: List[Dict[str, Any]],
    ):
        if tags is None:
            tags = dict()

        self.cache_cluster_id = cache_cluster_id
        self.replication_group_id = replication_group_id
        self.az_mode = az_mode
        self.preferred_availability_zone = preferred_availability_zone
        self.preferred_availability_zones = preferred_availability_zones
        self.engine = engine or "redis"
        self.engine_version = engine_version
        if self.engine == "redis":
            self.num_cache_nodes = 1
        else:
            self.num_cache_nodes = num_cache_nodes or 1
        self.cache_node_type = cache_node_type
        self.cache_parameter_group_name = cache_parameter_group_name
        self.cache_subnet_group_name = cache_subnet_group_name
        self.cache_security_group_names = cache_security_group_names
        self.security_group_ids = security_group_ids
        self.tags = tags
        self.snapshot_arns = snapshot_arns
        self.snapshot_name = snapshot_name
        self.preferred_maintenance_window = preferred_maintenance_window
        self.port = port or 6379
        self.notification_topic_arn = notification_topic_arn
        self.auto_minor_version_upgrade = auto_minor_version_upgrade
        self.snapshot_retention_limit = snapshot_retention_limit
        self.snapshot_window = snapshot_window
        self.auth_token = auth_token
        self.outpost_mode = outpost_mode
        self.preferred_outpost_arn = preferred_outpost_arn
        self.preferred_outpost_arns = preferred_outpost_arns
        self.log_delivery_configurations = log_delivery_configurations
        self.transit_encryption_enabled = transit_encryption_enabled
        self.network_type = network_type
        self.ip_discovery = ip_discovery
        self.cache_cluster_create_time = datetime.utcnow()
        self.cache_cluster_status = "available"


class ElastiCacheBackend(BaseBackend):
    """Implementation of ElastiCache APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.users = dict()
        self.users["default"] = User(
            account_id=self.account_id,
            region=self.region_name,
            user_id="default",
            user_name="default",
            engine="redis",
            access_string="on ~* +@all",
            no_password_required=True,
        )

    def create_user(
        self,
        user_id: str,
        user_name: str,
        engine: str,
        passwords: List[str],
        access_string: str,
        no_password_required: bool,
    ) -> User:
        if user_id in self.users:
            raise UserAlreadyExists
        user = User(
            account_id=self.account_id,
            region=self.region_name,
            user_id=user_id,
            user_name=user_name,
            engine=engine,
            passwords=passwords,
            access_string=access_string,
            no_password_required=no_password_required,
        )
        self.users[user_id] = user
        return user

    def delete_user(self, user_id: str) -> User:
        if user_id in self.users:
            user = self.users[user_id]
            if user.status == "active":
                user.status = "deleting"
            return user
        raise UserNotFound(user_id)

    def describe_users(self, user_id: Optional[str]) -> List[User]:
        """
        Only the `user_id` parameter is currently supported.
        Pagination is not yet implemented.
        """
        if user_id:
            if user_id in self.users:
                user = self.users[user_id]
                if user.status == "deleting":
                    self.users.pop(user_id)
                return [user]
            else:
                raise UserNotFound(user_id)
        return list(self.users.values())

    def create_cache_cluster(
            self,
            cache_cluster_id: str,
            replication_group_id: str,
            az_mode: str,
            preferred_availability_zone: str,
            num_cache_nodes: int,
            cache_node_type: str,
            engine: str,
            engine_version: str,
            cache_parameter_group_name: str,
            cache_subnet_group_name: str,
            transit_encryption_enabled: bool,
            network_type: str,
            ip_discovery: str,
            snapshot_name: str,
            preferred_maintenance_window: str,
            port: int,
            notification_topic_arn: str,
            auto_minor_version_upgrade: bool,
            snapshot_retention_limit: int,
            snapshot_window: str,
            auth_token: str,
            outpost_mode: str,
            preferred_outpost_arn: str,
            preferred_availability_zones: List[str],
            cache_security_group_names: List[str],
            security_group_ids: List[str],
            tags: List[Dict[str, str]],
            snapshot_arns: List[str],
            preferred_outpost_arns: List[str],
            log_delivery_configurations: List[Dict[str, Any]],
    ) -> CacheCluster:
        cache_cluster = CacheCluster(
            cache_cluster_id=cache_cluster_id,
            replication_group_id=replication_group_id,
            az_mode=az_mode,
            preferred_availability_zone=preferred_availability_zone,
            preferred_availability_zones=preferred_availability_zones,
            num_cache_nodes=num_cache_nodes,
            cache_node_type=cache_node_type,
            engine=engine,
            engine_version=engine_version,
            cache_parameter_group_name=cache_parameter_group_name,
            cache_subnet_group_name=cache_subnet_group_name,
            cache_security_group_names=cache_security_group_names,
            security_group_ids=security_group_ids,
            tags=tags,
            snapshot_arns=snapshot_arns,
            snapshot_name=snapshot_name,
            preferred_maintenance_window=preferred_maintenance_window,
            port=port,
            notification_topic_arn=notification_topic_arn,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            snapshot_retention_limit=snapshot_retention_limit,
            snapshot_window=snapshot_window,
            auth_token=auth_token,
            outpost_mode=outpost_mode,
            preferred_outpost_arn=preferred_outpost_arn,
            preferred_outpost_arns=preferred_outpost_arns,
            log_delivery_configurations=log_delivery_configurations,
            transit_encryption_enabled=transit_encryption_enabled,
            network_type=network_type,
            ip_discovery=ip_discovery
        )

        return cache_cluster


elasticache_backends = BackendDict(ElastiCacheBackend, "elasticache")
