"""DocDBElasticBackend class with methods for supported APIs."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from typing import Any

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.resource_tagging import TaggableResourcesMixin, TaggedResource
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.moto_api._internal import mock_random
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.utilities.paginator import paginate
from moto.utilities.utils import get_partition

from .exceptions import (
    ConflictException,
    ResourceNotFoundException,
    ValidationException,
)

VALID_SHARD_CAPACITIES = [2, 4, 8, 16, 32, 64]
MAX_SHARD_COUNT = 32


class Shard(BaseModel):
    def __init__(self) -> None:
        self.shard_id = mock_random.get_random_hex(12)
        self.create_time = iso_8601_datetime_with_milliseconds()
        self.status = "ACTIVE"


class Cluster(BaseModel, ManagedState):
    """Model for an Elastic DocumentDB cluster."""

    def __init__(
        self,
        backend: DocDBElasticBackend,
        cluster_name: str,
        admin_user_name: str,
        auth_type: str,
        shard_capacity: int,
        shard_count: int,
        shard_instance_count: int | None,
        backup_retention_period: int | None,
        preferred_backup_window: str | None,
        preferred_maintenance_window: str | None,
        kms_key_id: str | None,
        subnet_ids: list[str] | None,
        vpc_security_group_ids: list[str] | None,
        tags: dict[str, str] | None,
    ):
        ManagedState.__init__(
            self,
            "docdb-elastic::cluster",
            transitions=[
                ("CREATING", "ACTIVE"),
                ("STARTING", "ACTIVE"),
                ("STOPPING", "STOPPED"),
                ("DELETING", "DELETED"),
            ],
        )
        self.backend = backend
        self.cluster_name = cluster_name
        self.admin_user_name = admin_user_name
        self.auth_type = auth_type
        self.shard_capacity = shard_capacity
        self.shard_count = shard_count
        self.shard_instance_count = shard_instance_count or 1
        self.backup_retention_period = backup_retention_period or 1
        self.preferred_backup_window = preferred_backup_window or "00:00-00:30"
        self.preferred_maintenance_window = (
            preferred_maintenance_window or "sun:00:00-sun:00:30"
        )
        self.kms_key_id = kms_key_id or "AWS_OWNED_KMS_KEY"
        self.subnet_ids = subnet_ids or []
        self.vpc_security_group_ids = vpc_security_group_ids or []
        self.tags = tags or {}
        self.cluster_id = str(mock_random.uuid4())
        self.cluster_arn = f"arn:{backend.partition}:docdb-elastic:{backend.region_name}:{backend.account_id}:cluster/{self.cluster_id}"
        self.cluster_endpoint = f"{cluster_name}-{mock_random.get_random_hex(6)}.{backend.region_name}.docdb-elastic.amazonaws.com"
        self.create_time = iso_8601_datetime_with_milliseconds()
        self.shards = [Shard() for _ in range(shard_count)]

    def update_shard_count(self, shard_count: int) -> None:
        if shard_count > len(self.shards):
            self.shards.extend(Shard() for _ in range(shard_count - len(self.shards)))
        else:
            self.shards = self.shards[:shard_count]
        self.shard_count = shard_count


class ClusterSnapshot(BaseModel, ManagedState):
    """Model for an Elastic DocumentDB cluster snapshot."""

    def __init__(
        self,
        backend: DocDBElasticBackend,
        snapshot_name: str,
        cluster_arn: str,
        cluster_creation_time: str,
        admin_user_name: str,
        auth_type: str,
        kms_key_id: str,
        subnet_ids: list[str],
        vpc_security_group_ids: list[str],
        shard_capacity: int,
        shard_count: int,
        shard_instance_count: int,
        tags: dict[str, str] | None,
    ):
        ManagedState.__init__(
            self,
            "docdb-elastic::cluster-snapshot",
            transitions=[("CREATING", "ACTIVE"), ("DELETING", "DELETED")],
        )
        self.backend = backend
        self.snapshot_name = snapshot_name
        self.snapshot_type = "MANUAL"
        self.snapshot_id = str(mock_random.uuid4())
        self.snapshot_arn = f"arn:{backend.partition}:docdb-elastic:{backend.region_name}:{backend.account_id}:cluster-snapshot/{self.snapshot_id}"
        self.snapshot_creation_time = iso_8601_datetime_with_milliseconds()
        self.cluster_arn = cluster_arn
        self.cluster_creation_time = cluster_creation_time
        self.admin_user_name = admin_user_name
        self.auth_type = auth_type
        self.kms_key_id = kms_key_id
        self.subnet_ids = list(subnet_ids)
        self.vpc_security_group_ids = list(vpc_security_group_ids)
        self.shard_capacity = shard_capacity
        self.shard_count = shard_count
        self.shard_instance_count = shard_instance_count
        self.tags = tags or {}

    @classmethod
    def from_cluster(
        cls,
        backend: DocDBElasticBackend,
        cluster: Cluster,
        snapshot_name: str,
        tags: dict[str, str] | None,
    ) -> ClusterSnapshot:
        return cls(
            backend=backend,
            snapshot_name=snapshot_name,
            cluster_arn=cluster.cluster_arn,
            cluster_creation_time=cluster.create_time,
            admin_user_name=cluster.admin_user_name,
            auth_type=cluster.auth_type,
            kms_key_id=cluster.kms_key_id,
            subnet_ids=cluster.subnet_ids,
            vpc_security_group_ids=cluster.vpc_security_group_ids,
            shard_capacity=cluster.shard_capacity,
            shard_count=cluster.shard_count,
            shard_instance_count=cluster.shard_instance_count,
            tags=tags,
        )

    def copy(
        self,
        target_snapshot_name: str,
        kms_key_id: str | None,
        tags: dict[str, str],
    ) -> ClusterSnapshot:
        return ClusterSnapshot(
            backend=self.backend,
            snapshot_name=target_snapshot_name,
            cluster_arn=self.cluster_arn,
            cluster_creation_time=self.cluster_creation_time,
            admin_user_name=self.admin_user_name,
            auth_type=self.auth_type,
            kms_key_id=kms_key_id or self.kms_key_id,
            subnet_ids=self.subnet_ids,
            vpc_security_group_ids=self.vpc_security_group_ids,
            shard_capacity=self.shard_capacity,
            shard_count=self.shard_count,
            shard_instance_count=self.shard_instance_count,
            tags=tags,
        )


class DocDBElasticBackend(BaseBackend, TaggableResourcesMixin):
    """Implementation of DocDBElastic APIs."""

    SERVICE_NAMESPACE = "docdb-elastic"

    PAGINATION_MODEL = {
        "list_clusters": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "cluster_arn",
        },
        "list_cluster_snapshots": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "snapshot_arn",
        },
    }

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.partition = get_partition(region_name)
        self.clusters: dict[str, Cluster] = OrderedDict()
        self.snapshots: dict[str, ClusterSnapshot] = OrderedDict()

    @staticmethod
    def _validate_shard_settings(
        shard_capacity: int | None, shard_count: int | None
    ) -> None:
        if shard_capacity is not None and shard_capacity not in VALID_SHARD_CAPACITIES:
            raise ValidationException(
                f"shardCapacity must be one of {VALID_SHARD_CAPACITIES}",
                reason="fieldValidationFailed",
            )
        if shard_count is not None and not 1 <= shard_count <= MAX_SHARD_COUNT:
            raise ValidationException(
                f"shardCount must be between 1 and {MAX_SHARD_COUNT}",
                reason="fieldValidationFailed",
            )

    def create_cluster(
        self,
        cluster_name: str,
        admin_user_name: str,
        admin_user_password: str | None,
        auth_type: str,
        shard_capacity: int,
        shard_count: int,
        shard_instance_count: int | None,
        backup_retention_period: int | None,
        preferred_backup_window: str | None,
        preferred_maintenance_window: str | None,
        kms_key_id: str | None,
        subnet_ids: list[str] | None,
        vpc_security_group_ids: list[str] | None,
        tags: dict[str, str] | None,
    ) -> Cluster:
        self._validate_shard_settings(shard_capacity, shard_count)
        if auth_type == "PLAIN_TEXT" and not admin_user_password:
            raise ValidationException(
                "adminUserPassword is required when authType is PLAIN_TEXT",
                reason="fieldValidationFailed",
            )
        return self._add_cluster(
            cluster_name=cluster_name,
            admin_user_name=admin_user_name,
            auth_type=auth_type,
            shard_capacity=shard_capacity,
            shard_count=shard_count,
            shard_instance_count=shard_instance_count,
            backup_retention_period=backup_retention_period,
            preferred_backup_window=preferred_backup_window,
            preferred_maintenance_window=preferred_maintenance_window,
            kms_key_id=kms_key_id,
            subnet_ids=subnet_ids,
            vpc_security_group_ids=vpc_security_group_ids,
            tags=tags,
        )

    def _add_cluster(
        self,
        cluster_name: str,
        admin_user_name: str,
        auth_type: str,
        shard_capacity: int,
        shard_count: int,
        shard_instance_count: int | None,
        backup_retention_period: int | None,
        preferred_backup_window: str | None,
        preferred_maintenance_window: str | None,
        kms_key_id: str | None,
        subnet_ids: list[str] | None,
        vpc_security_group_ids: list[str] | None,
        tags: dict[str, str] | None,
    ) -> Cluster:
        for existing in self.clusters.values():
            if existing.cluster_name == cluster_name:
                raise ConflictException(
                    f"Cluster {cluster_name} already exists",
                    existing.cluster_arn,
                    "cluster",
                )
        cluster = Cluster(
            backend=self,
            cluster_name=cluster_name,
            admin_user_name=admin_user_name,
            auth_type=auth_type,
            shard_capacity=shard_capacity,
            shard_count=shard_count,
            shard_instance_count=shard_instance_count,
            backup_retention_period=backup_retention_period,
            preferred_backup_window=preferred_backup_window,
            preferred_maintenance_window=preferred_maintenance_window,
            kms_key_id=kms_key_id,
            subnet_ids=subnet_ids,
            vpc_security_group_ids=vpc_security_group_ids,
            tags=tags,
        )
        self.clusters[cluster.cluster_arn] = cluster
        return cluster

    def get_cluster(self, cluster_arn: str) -> Cluster:
        if cluster_arn not in self.clusters:
            raise ResourceNotFoundException(cluster_arn, "cluster")
        cluster = self.clusters[cluster_arn]
        cluster.advance()
        if cluster.status == "DELETED":
            self.clusters.pop(cluster_arn)
            raise ResourceNotFoundException(cluster_arn, "cluster")
        return cluster

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_clusters(self) -> list[Cluster]:
        return [
            cluster
            for cluster in list(self.clusters.values())
            if cluster.status != "DELETED"
        ]

    def update_cluster(
        self,
        cluster_arn: str,
        admin_user_password: str | None,
        auth_type: str | None,
        shard_capacity: int | None,
        shard_count: int | None,
        shard_instance_count: int | None,
        backup_retention_period: int | None,
        preferred_backup_window: str | None,
        preferred_maintenance_window: str | None,
        subnet_ids: list[str] | None,
        vpc_security_group_ids: list[str] | None,
    ) -> Cluster:
        cluster = self.get_cluster(cluster_arn)
        self._validate_shard_settings(shard_capacity, shard_count)
        if auth_type is not None:
            cluster.auth_type = auth_type
        if shard_capacity is not None:
            cluster.shard_capacity = shard_capacity
        if shard_count is not None:
            cluster.update_shard_count(shard_count)
        if shard_instance_count is not None:
            cluster.shard_instance_count = shard_instance_count
        if backup_retention_period is not None:
            cluster.backup_retention_period = backup_retention_period
        if preferred_backup_window is not None:
            cluster.preferred_backup_window = preferred_backup_window
        if preferred_maintenance_window is not None:
            cluster.preferred_maintenance_window = preferred_maintenance_window
        if subnet_ids is not None:
            cluster.subnet_ids = subnet_ids
        if vpc_security_group_ids is not None:
            cluster.vpc_security_group_ids = vpc_security_group_ids
        return cluster

    def delete_cluster(self, cluster_arn: str) -> Cluster:
        cluster = self.get_cluster(cluster_arn)
        cluster.status = "DELETING"
        cluster._tick = 0
        return cluster

    def start_cluster(self, cluster_arn: str) -> Cluster:
        cluster = self.get_cluster(cluster_arn)
        if cluster.status != "STOPPED":
            raise ConflictException(
                f"Cluster {cluster_arn} is not in a stopped state",
                cluster_arn,
                "cluster",
            )
        cluster.status = "STARTING"
        cluster._tick = 0
        return cluster

    def stop_cluster(self, cluster_arn: str) -> Cluster:
        cluster = self.get_cluster(cluster_arn)
        if cluster.status != "ACTIVE":
            raise ConflictException(
                f"Cluster {cluster_arn} is not in an active state",
                cluster_arn,
                "cluster",
            )
        cluster.status = "STOPPING"
        cluster._tick = 0
        return cluster

    def create_cluster_snapshot(
        self, cluster_arn: str, snapshot_name: str, tags: dict[str, str] | None
    ) -> ClusterSnapshot:
        cluster = self.get_cluster(cluster_arn)
        for existing in self.snapshots.values():
            if existing.snapshot_name == snapshot_name:
                raise ConflictException(
                    f"Snapshot {snapshot_name} already exists",
                    existing.snapshot_arn,
                    "cluster-snapshot",
                )
        snapshot = ClusterSnapshot.from_cluster(
            backend=self, cluster=cluster, snapshot_name=snapshot_name, tags=tags
        )
        self.snapshots[snapshot.snapshot_arn] = snapshot
        return snapshot

    def get_cluster_snapshot(self, snapshot_arn: str) -> ClusterSnapshot:
        if snapshot_arn not in self.snapshots:
            raise ResourceNotFoundException(snapshot_arn, "cluster-snapshot")
        snapshot = self.snapshots[snapshot_arn]
        snapshot.advance()
        if snapshot.status == "DELETED":
            self.snapshots.pop(snapshot_arn)
            raise ResourceNotFoundException(snapshot_arn, "cluster-snapshot")
        return snapshot

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_cluster_snapshots(
        self, cluster_arn: str | None, snapshot_type: str | None
    ) -> list[ClusterSnapshot]:
        snapshots = [
            snapshot
            for snapshot in list(self.snapshots.values())
            if snapshot.status != "DELETED"
        ]
        if cluster_arn:
            snapshots = [s for s in snapshots if s.cluster_arn == cluster_arn]
        if snapshot_type:
            snapshots = [s for s in snapshots if s.snapshot_type == snapshot_type]
        return snapshots

    def copy_cluster_snapshot(
        self,
        snapshot_arn: str,
        target_snapshot_name: str,
        kms_key_id: str | None,
        copy_tags: bool | None,
        tags: dict[str, str] | None,
    ) -> ClusterSnapshot:
        source = self.get_cluster_snapshot(snapshot_arn)
        for existing in self.snapshots.values():
            if existing.snapshot_name == target_snapshot_name:
                raise ConflictException(
                    f"Snapshot {target_snapshot_name} already exists",
                    existing.snapshot_arn,
                    "cluster-snapshot",
                )
        new_tags = dict(source.tags) if copy_tags else {}
        new_tags.update(tags or {})
        snapshot = source.copy(target_snapshot_name, kms_key_id, new_tags)
        self.snapshots[snapshot.snapshot_arn] = snapshot
        return snapshot

    def delete_cluster_snapshot(self, snapshot_arn: str) -> ClusterSnapshot:
        snapshot = self.get_cluster_snapshot(snapshot_arn)
        snapshot.status = "DELETING"
        snapshot._tick = 0
        return snapshot

    def restore_cluster_from_snapshot(
        self,
        snapshot_arn: str,
        cluster_name: str,
        kms_key_id: str | None,
        shard_capacity: int | None,
        shard_instance_count: int | None,
        subnet_ids: list[str] | None,
        vpc_security_group_ids: list[str] | None,
        tags: dict[str, str] | None,
    ) -> Cluster:
        snapshot = self.get_cluster_snapshot(snapshot_arn)
        self._validate_shard_settings(shard_capacity, None)
        return self._add_cluster(
            cluster_name=cluster_name,
            admin_user_name=snapshot.admin_user_name,
            auth_type=snapshot.auth_type,
            shard_capacity=shard_capacity or snapshot.shard_capacity,
            shard_count=snapshot.shard_count,
            shard_instance_count=shard_instance_count or snapshot.shard_instance_count,
            backup_retention_period=None,
            preferred_backup_window=None,
            preferred_maintenance_window=None,
            kms_key_id=kms_key_id or snapshot.kms_key_id,
            subnet_ids=subnet_ids or snapshot.subnet_ids,
            vpc_security_group_ids=vpc_security_group_ids
            or snapshot.vpc_security_group_ids,
            tags=tags,
        )

    def _get_resource(self, resource_arn: str) -> Cluster | ClusterSnapshot:
        if ":cluster-snapshot/" in resource_arn:
            return self.get_cluster_snapshot(resource_arn)
        return self.get_cluster(resource_arn)

    def get_pending_maintenance_action(self, resource_arn: str) -> dict[str, Any]:
        """
        Pending maintenance actions are never scheduled by Moto, so this
        always returns an empty list of actions for an existing resource.
        """
        self._get_resource(resource_arn)
        return {"resourceArn": resource_arn, "pendingMaintenanceActionDetails": []}

    def list_pending_maintenance_actions(self) -> list[dict[str, Any]]:
        """
        Pending maintenance actions are never scheduled by Moto, so this
        always returns an empty list. Pagination is not yet implemented.
        """
        return []

    def apply_pending_maintenance_action(
        self, resource_arn: str, apply_action: str, opt_in_type: str
    ) -> dict[str, Any]:
        """
        Pending maintenance actions are never scheduled by Moto, so this
        is a no-op that validates the resource exists.
        """
        return self.get_pending_maintenance_action(resource_arn)

    def list_tags_for_resource(self, resource_arn: str) -> dict[str, str]:
        return self._get_resource(resource_arn).tags

    def tag_resource(self, resource_arn: str, tags: dict[str, str]) -> None:
        resource = self._get_resource(resource_arn)
        resource.tags = {**resource.tags, **tags}

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        resource = self._get_resource(resource_arn)
        resource.tags = {k: v for k, v in resource.tags.items() if k not in tag_keys}

    def iter_tagged_resources(self) -> Iterator[TaggedResource]:
        for cluster in self.clusters.values():
            yield TaggedResource(
                arn=cluster.cluster_arn,
                tags=cluster.tags,
                resource_type="docdb-elastic:cluster",
                extra={"include_untagged": True},
            )
        for snapshot in self.snapshots.values():
            yield TaggedResource(
                arn=snapshot.snapshot_arn,
                tags=snapshot.tags,
                resource_type="docdb-elastic:cluster-snapshot",
                extra={"include_untagged": True},
            )


docdbelastic_backends = BackendDict(
    DocDBElasticBackend,
    "docdb-elastic",
    # botocore's endpoint data does not list any regions for docdb-elastic,
    # so the regions where Elastic Clusters are available are listed here
    use_boto3_regions=False,
    additional_regions=[
        "us-east-1",
        "us-east-2",
        "us-west-2",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "sa-east-1",
    ],
)
