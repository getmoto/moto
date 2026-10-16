"""Handles incoming memorydb requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse

from .models import MemoryDBBackend, memorydb_backends


class MemoryDBResponse(BaseResponse):
    """Handler for MemoryDB requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="memorydb")
        self.automated_parameter_parsing = True

    @property
    def memorydb_backend(self) -> MemoryDBBackend:
        """Return backend instance specific for this region."""
        return memorydb_backends[self.current_account][self.region]

    def create_cluster(self) -> ActionResult:
        cluster_name = self._get_param("ClusterName")
        node_type = self._get_param("NodeType")
        parameter_group_name = self._get_param("ParameterGroupName")
        description = self._get_param("Description")
        num_shards = self._get_param("NumShards")
        num_replicas_per_shard = self._get_param("NumReplicasPerShard")
        subnet_group_name = self._get_param("SubnetGroupName")
        security_group_ids = self._get_param("SecurityGroupIds")
        maintenance_window = self._get_param("MaintenanceWindow")
        port = self._get_param("Port")
        sns_topic_arn = self._get_param("SnsTopicArn")
        tls_enabled = self._get_param("TLSEnabled")
        kms_key_id = self._get_param("KmsKeyId")
        snapshot_arns = self._get_param("SnapshotArns")
        snapshot_name = self._get_param("SnapshotName")
        snapshot_retention_limit = self._get_param("SnapshotRetentionLimit")
        tags = self._get_param("Tags")
        snapshot_window = self._get_param("SnapshotWindow")
        acl_name = self._get_param("ACLName")
        engine_version = self._get_param("EngineVersion")
        auto_minor_version_upgrade = self._get_param("AutoMinorVersionUpgrade")
        data_tiering = self._get_param("DataTiering")
        cluster = self.memorydb_backend.create_cluster(
            cluster_name=cluster_name,
            node_type=node_type,
            parameter_group_name=parameter_group_name,
            description=description,
            num_shards=num_shards,
            num_replicas_per_shard=num_replicas_per_shard,
            subnet_group_name=subnet_group_name,
            security_group_ids=security_group_ids,
            maintenance_window=maintenance_window,
            port=port,
            sns_topic_arn=sns_topic_arn,
            tls_enabled=tls_enabled,
            kms_key_id=kms_key_id,
            snapshot_arns=snapshot_arns,
            snapshot_name=snapshot_name,
            snapshot_retention_limit=snapshot_retention_limit,
            tags=tags,
            snapshot_window=snapshot_window,
            acl_name=acl_name,
            engine_version=engine_version,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            data_tiering=data_tiering,
        )
        return ActionResult({"Cluster": cluster.to_dict()})

    def create_subnet_group(self) -> ActionResult:
        subnet_group_name = self._get_param("SubnetGroupName")
        description = self._get_param("Description")
        subnet_ids = self._get_param("SubnetIds")
        tags = self._get_param("Tags")
        subnet_group = self.memorydb_backend.create_subnet_group(
            subnet_group_name=subnet_group_name,
            description=description,
            subnet_ids=subnet_ids,
            tags=tags,
        )
        return ActionResult({"SubnetGroup": subnet_group.to_dict()})

    def create_snapshot(self) -> ActionResult:
        cluster_name = self._get_param("ClusterName")
        snapshot_name = self._get_param("SnapshotName")
        kms_key_id = self._get_param("KmsKeyId")
        tags = self._get_param("Tags")
        snapshot = self.memorydb_backend.create_snapshot(
            cluster_name=cluster_name,
            snapshot_name=snapshot_name,
            kms_key_id=kms_key_id,
            tags=tags,
        )
        return ActionResult({"Snapshot": snapshot.to_dict()})

    def describe_clusters(self) -> ActionResult:
        cluster_name = self._get_param("ClusterName")
        show_shard_details = self._get_param("ShowShardDetails")
        clusters = self.memorydb_backend.describe_clusters(
            cluster_name=cluster_name,
        )
        return ActionResult(
            {
                "Clusters": [
                    cluster.to_desc_dict() if show_shard_details else cluster.to_dict()
                    for cluster in clusters
                ]
            }
        )

    def describe_snapshots(self) -> ActionResult:
        cluster_name = self._get_param("ClusterName")
        snapshot_name = self._get_param("SnapshotName")
        source = self._get_param("Source")
        show_detail = self._get_param("ShowDetail")
        snapshots = self.memorydb_backend.describe_snapshots(
            cluster_name=cluster_name,
            snapshot_name=snapshot_name,
            source=source,
        )
        return ActionResult(
            {
                "Snapshots": [
                    snapshot.to_desc_dict() if show_detail else snapshot.to_dict()
                    for snapshot in snapshots
                ]
            }
        )

    def describe_subnet_groups(self) -> ActionResult:
        subnet_group_name = self._get_param("SubnetGroupName")
        subnet_groups = self.memorydb_backend.describe_subnet_groups(
            subnet_group_name=subnet_group_name,
        )
        return ActionResult({"SubnetGroups": [sg.to_dict() for sg in subnet_groups]})

    def list_tags(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tag_list = self.memorydb_backend.list_tags(
            resource_arn=resource_arn,
        )
        return ActionResult({"TagList": tag_list})

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        tag_list = self.memorydb_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return ActionResult({"TagList": tag_list})

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        tag_list = self.memorydb_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return ActionResult({"TagList": tag_list})

    def update_cluster(self) -> ActionResult:
        cluster_name = self._get_param("ClusterName")
        description = self._get_param("Description")
        security_group_ids = self._get_param("SecurityGroupIds")
        maintenance_window = self._get_param("MaintenanceWindow")
        sns_topic_arn = self._get_param("SnsTopicArn")
        sns_topic_status = self._get_param("SnsTopicStatus")
        parameter_group_name = self._get_param("ParameterGroupName")
        snapshot_window = self._get_param("SnapshotWindow")
        snapshot_retention_limit = self._get_param("SnapshotRetentionLimit")
        node_type = self._get_param("NodeType")
        engine_version = self._get_param("EngineVersion")
        replica_configuration = self._get_param("ReplicaConfiguration")
        shard_configuration = self._get_param("ShardConfiguration")
        acl_name = self._get_param("ACLName")
        cluster = self.memorydb_backend.update_cluster(
            cluster_name=cluster_name,
            description=description,
            security_group_ids=security_group_ids,
            maintenance_window=maintenance_window,
            sns_topic_arn=sns_topic_arn,
            sns_topic_status=sns_topic_status,
            parameter_group_name=parameter_group_name,
            snapshot_window=snapshot_window,
            snapshot_retention_limit=snapshot_retention_limit,
            node_type=node_type,
            engine_version=engine_version,
            replica_configuration=replica_configuration,
            shard_configuration=shard_configuration,
            acl_name=acl_name,
        )
        return ActionResult({"Cluster": cluster.to_dict()})

    def delete_cluster(self) -> ActionResult:
        cluster_name = self._get_param("ClusterName")
        final_snapshot_name = self._get_param("FinalSnapshotName")
        cluster = self.memorydb_backend.delete_cluster(
            cluster_name=cluster_name,
            final_snapshot_name=final_snapshot_name,
        )
        return ActionResult({"Cluster": cluster.to_dict()})

    def delete_snapshot(self) -> ActionResult:
        snapshot_name = self._get_param("SnapshotName")
        snapshot = self.memorydb_backend.delete_snapshot(
            snapshot_name=snapshot_name,
        )
        return ActionResult({"Snapshot": snapshot.to_dict()})

    def delete_subnet_group(self) -> ActionResult:
        subnet_group_name = self._get_param("SubnetGroupName")
        subnet_group = self.memorydb_backend.delete_subnet_group(
            subnet_group_name=subnet_group_name,
        )
        return ActionResult({"SubnetGroup": subnet_group.to_dict()})

    def create_user(self) -> ActionResult:
        user_name = self._get_param("UserName")
        authentication_mode = self._get_param("AuthenticationMode")
        access_string = self._get_param("AccessString")
        tags = self._get_param("Tags")
        user = self.memorydb_backend.create_user(
            user_name=user_name,
            authentication_mode=authentication_mode,
            access_string=access_string,
            tags=tags,
        )
        return ActionResult({"User": user.to_dict()})

    def describe_users(self) -> ActionResult:
        user_name = self._get_param("UserName")
        filters = self._get_param("Filters")
        users = self.memorydb_backend.describe_users(
            user_name=user_name,
            filters=filters,
        )
        return ActionResult({"Users": [user.to_dict() for user in users]})

    def update_user(self) -> ActionResult:
        user_name = self._get_param("UserName")
        authentication_mode = self._get_param("AuthenticationMode")
        access_string = self._get_param("AccessString")
        user = self.memorydb_backend.update_user(
            user_name=user_name,
            authentication_mode=authentication_mode,
            access_string=access_string,
        )
        return ActionResult({"User": user.to_dict()})

    def delete_user(self) -> ActionResult:
        user_name = self._get_param("UserName")
        user = self.memorydb_backend.delete_user(
            user_name=user_name,
        )
        return ActionResult({"User": user.to_dict()})
