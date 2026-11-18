"""Handles incoming docdb-elastic requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import DocDBElasticBackend, docdbelastic_backends


class DeletingView:
    """
    Serializes a resource as it looked when the delete request was accepted.

    The default state progression is immediate, so by the time the response
    is serialized the resource has already transitioned past DELETING.
    """

    def __init__(self, resource: Any):
        self._resource = resource

    @property
    def status(self) -> str:
        return "DELETING"

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resource, name)


class DocDBElasticResponse(BaseResponse):
    """Handler for DocDBElastic requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="docdb-elastic")
        self.automated_parameter_parsing = True

    @property
    def docdbelastic_backend(self) -> DocDBElasticBackend:
        """Return backend instance specific for this region."""
        return docdbelastic_backends[self.current_account][self.region]

    def create_cluster(self) -> ActionResult:
        cluster = self.docdbelastic_backend.create_cluster(
            cluster_name=self._get_param("clusterName"),
            admin_user_name=self._get_param("adminUserName"),
            admin_user_password=self._get_param("adminUserPassword"),
            auth_type=self._get_param("authType"),
            shard_capacity=self._get_int_param("shardCapacity"),
            shard_count=self._get_int_param("shardCount"),
            shard_instance_count=self._get_int_param("shardInstanceCount"),
            backup_retention_period=self._get_int_param("backupRetentionPeriod"),
            preferred_backup_window=self._get_param("preferredBackupWindow"),
            preferred_maintenance_window=self._get_param("preferredMaintenanceWindow"),
            kms_key_id=self._get_param("kmsKeyId"),
            subnet_ids=self._get_param("subnetIds"),
            vpc_security_group_ids=self._get_param("vpcSecurityGroupIds"),
            tags=self._get_param("tags"),
        )
        return ActionResult({"cluster": cluster})

    def get_cluster(self) -> ActionResult:
        cluster = self.docdbelastic_backend.get_cluster(self._get_param("clusterArn"))
        return ActionResult({"cluster": cluster})

    def list_clusters(self) -> ActionResult:
        clusters, next_token = self.docdbelastic_backend.list_clusters(
            max_results=self._get_int_param("maxResults"),
            next_token=self._get_param("nextToken"),
        )
        result: dict[str, Any] = {"clusters": clusters}
        if next_token:
            result["nextToken"] = next_token
        return ActionResult(result)

    def update_cluster(self) -> ActionResult:
        cluster = self.docdbelastic_backend.update_cluster(
            cluster_arn=self._get_param("clusterArn"),
            admin_user_password=self._get_param("adminUserPassword"),
            auth_type=self._get_param("authType"),
            shard_capacity=self._get_int_param("shardCapacity"),
            shard_count=self._get_int_param("shardCount"),
            shard_instance_count=self._get_int_param("shardInstanceCount"),
            backup_retention_period=self._get_int_param("backupRetentionPeriod"),
            preferred_backup_window=self._get_param("preferredBackupWindow"),
            preferred_maintenance_window=self._get_param("preferredMaintenanceWindow"),
            subnet_ids=self._get_param("subnetIds"),
            vpc_security_group_ids=self._get_param("vpcSecurityGroupIds"),
        )
        return ActionResult({"cluster": cluster})

    def delete_cluster(self) -> ActionResult:
        cluster = self.docdbelastic_backend.delete_cluster(
            self._get_param("clusterArn")
        )
        return ActionResult({"cluster": DeletingView(cluster)})

    def start_cluster(self) -> ActionResult:
        cluster = self.docdbelastic_backend.start_cluster(self._get_param("clusterArn"))
        return ActionResult({"cluster": cluster})

    def stop_cluster(self) -> ActionResult:
        cluster = self.docdbelastic_backend.stop_cluster(self._get_param("clusterArn"))
        return ActionResult({"cluster": cluster})

    def create_cluster_snapshot(self) -> ActionResult:
        snapshot = self.docdbelastic_backend.create_cluster_snapshot(
            cluster_arn=self._get_param("clusterArn"),
            snapshot_name=self._get_param("snapshotName"),
            tags=self._get_param("tags"),
        )
        return ActionResult({"snapshot": snapshot})

    def get_cluster_snapshot(self) -> ActionResult:
        snapshot = self.docdbelastic_backend.get_cluster_snapshot(
            self._get_param("snapshotArn")
        )
        return ActionResult({"snapshot": snapshot})

    def list_cluster_snapshots(self) -> ActionResult:
        snapshots, next_token = self.docdbelastic_backend.list_cluster_snapshots(
            cluster_arn=self._get_param("clusterArn"),
            snapshot_type=self._get_param("snapshotType"),
            max_results=self._get_int_param("maxResults"),
            next_token=self._get_param("nextToken"),
        )
        result: dict[str, Any] = {"snapshots": snapshots}
        if next_token:
            result["nextToken"] = next_token
        return ActionResult(result)

    def copy_cluster_snapshot(self) -> ActionResult:
        snapshot = self.docdbelastic_backend.copy_cluster_snapshot(
            snapshot_arn=self._get_param("snapshotArn"),
            target_snapshot_name=self._get_param("targetSnapshotName"),
            kms_key_id=self._get_param("kmsKeyId"),
            copy_tags=self._get_bool_param("copyTags"),
            tags=self._get_param("tags"),
        )
        return ActionResult({"snapshot": snapshot})

    def delete_cluster_snapshot(self) -> ActionResult:
        snapshot = self.docdbelastic_backend.delete_cluster_snapshot(
            self._get_param("snapshotArn")
        )
        return ActionResult({"snapshot": DeletingView(snapshot)})

    def restore_cluster_from_snapshot(self) -> ActionResult:
        cluster = self.docdbelastic_backend.restore_cluster_from_snapshot(
            snapshot_arn=self._get_param("snapshotArn"),
            cluster_name=self._get_param("clusterName"),
            kms_key_id=self._get_param("kmsKeyId"),
            shard_capacity=self._get_int_param("shardCapacity"),
            shard_instance_count=self._get_int_param("shardInstanceCount"),
            subnet_ids=self._get_param("subnetIds"),
            vpc_security_group_ids=self._get_param("vpcSecurityGroupIds"),
            tags=self._get_param("tags"),
        )
        return ActionResult({"cluster": cluster})

    def get_pending_maintenance_action(self) -> ActionResult:
        action = self.docdbelastic_backend.get_pending_maintenance_action(
            self._get_param("resourceArn")
        )
        return ActionResult({"resourcePendingMaintenanceAction": action})

    def list_pending_maintenance_actions(self) -> ActionResult:
        actions = self.docdbelastic_backend.list_pending_maintenance_actions()
        return ActionResult({"resourcePendingMaintenanceActions": actions})

    def apply_pending_maintenance_action(self) -> ActionResult:
        action = self.docdbelastic_backend.apply_pending_maintenance_action(
            resource_arn=self._get_param("resourceArn"),
            apply_action=self._get_param("applyAction"),
            opt_in_type=self._get_param("optInType"),
        )
        return ActionResult({"resourcePendingMaintenanceAction": action})

    def list_tags_for_resource(self) -> ActionResult:
        tags = self.docdbelastic_backend.list_tags_for_resource(
            self._get_param("resourceArn")
        )
        return ActionResult({"tags": tags})

    def tag_resource(self) -> ActionResult:
        self.docdbelastic_backend.tag_resource(
            self._get_param("resourceArn"), self._get_param("tags")
        )
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        self.docdbelastic_backend.untag_resource(
            self._get_param("resourceArn"), self._get_param("tagKeys", [])
        )
        return EmptyResult()
