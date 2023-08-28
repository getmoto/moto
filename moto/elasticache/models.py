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
        cache_cluster_id: Dict[str, Any],
        replication_group_id: Optional[str] = None,
        az_mode: Optional[str] = None,
        preferred_availability_zone: Optional[str] = None,
        preferred_availability_zones: List[str] = None,
        num_cache_nodes: Optional[int] = None,
        cache_node_type: Optional[str] = None,
        engine: Optional[str] = "Redis",
        engine_version: Optional[str] = None,
        cache_parameter_group_name: Optional[str] = None,
        cache_subnet_group_name: Optional[str] = None,
        cache_security_group_names: Optional[List[str]] = None,
        security_group_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        snapshot_arns: Optional[List[str]] = None,
        snapshot_name: Optional[str] = None,
        preferred_maintenance_window: Optional[str] = None,
        port: Optional[int] = None,
        notification_topic_arn: Optional[str] = None,
        auto_minor_version_upgrade: Optional[bool] = True,
        snapshot_retention_limit: Optional[int] = None,
        snapshot_window: Optional[str] = None,
        auth_token: Optional[str] = None,
        outpost_mode: Optional[str] = None,
        preferred_outpost_arn: Optional[str] = None,
        preferred_outpost_arns: Optional[List[str]] = None,
        log_delivery_configurations: Optional[List[str]] = None,
        transit_encryption_enabled: Optional[bool] = True,
        network_type: Optional[str] = None,
        ip_discovery: Optional[str] = None,
    ):
        cache_cluster = {
            cache_cluster_id,
            replication_group_id,
            az_mode,
            preferred_availability_zone,
            preferred_availability_zones,
            num_cache_nodes,
            cache_node_type,
            engine,
            engine_version,
            cache_parameter_group_name,
            cache_subnet_group_name,
            cache_security_group_names,
            security_group_ids,
            tags,
            snapshot_arns,
            snapshot_name,
            preferred_maintenance_window,
            port,
            notification_topic_arn,
            auto_minor_version_upgrade,
            snapshot_retention_limit,
            snapshot_window,
            auth_token,
            outpost_mode,
            preferred_outpost_arn,
            preferred_outpost_arns,
            log_delivery_configurations,
            transit_encryption_enabled,
            network_type,
            ip_discovery,
        }

        return cache_cluster


elasticache_backends = BackendDict(ElastiCacheBackend, "elasticache")
