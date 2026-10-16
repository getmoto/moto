"""Handles incoming cloudhsmv2 requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import CloudHSMV2Backend, cloudhsmv2_backends


class CloudHSMV2Response(BaseResponse):
    """Handler for CloudHSMV2 requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="cloudhsmv2")
        self.automated_parameter_parsing = True

    @property
    def cloudhsmv2_backend(self) -> CloudHSMV2Backend:
        """Return backend instance specific for this region."""
        return cloudhsmv2_backends[self.current_account][self.region]

    def list_tags(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")

        tag_list, next_token = self.cloudhsmv2_backend.list_tags(
            resource_id=resource_id,
            next_token=next_token,
            max_results=max_results,
        )

        return ActionResult({"TagList": tag_list, "NextToken": next_token})

    def tag_resource(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        tag_list = self._get_param("TagList")

        self.cloudhsmv2_backend.tag_resource(
            resource_id=resource_id,
            tag_list=tag_list,
        )
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_id = self._get_param("ResourceId")
        tag_key_list = self._get_param("TagKeyList")
        self.cloudhsmv2_backend.untag_resource(
            resource_id=resource_id,
            tag_key_list=tag_key_list,
        )
        return EmptyResult()

    def create_cluster(self) -> ActionResult:
        backup_retention_policy = self._get_param("BackupRetentionPolicy", {})
        hsm_type = self._get_param("HsmType")
        source_backup_id = self._get_param("SourceBackupId")
        subnet_ids = self._get_param("SubnetIds", [])
        network_type = self._get_param("NetworkType")
        tag_list = self._get_param("TagList")
        mode = self._get_param("Mode")

        cluster = self.cloudhsmv2_backend.create_cluster(
            backup_retention_policy=backup_retention_policy,
            hsm_type=hsm_type,
            source_backup_id=source_backup_id,
            subnet_ids=subnet_ids,
            network_type=network_type,
            tag_list=tag_list,
            mode=mode,
        )
        return ActionResult({"Cluster": cluster})

    def delete_cluster(self) -> ActionResult:
        cluster_id = self._get_param("ClusterId")

        cluster = self.cloudhsmv2_backend.delete_cluster(cluster_id=cluster_id)
        return ActionResult({"Cluster": cluster})

    def describe_clusters(self) -> ActionResult:
        filters = self._get_param("Filters", {})
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")

        clusters, next_token = self.cloudhsmv2_backend.describe_clusters(
            filters=filters,
            next_token=next_token,
            max_results=max_results,
        )

        return ActionResult({"Clusters": clusters, "NextToken": next_token})

    def get_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy = self.cloudhsmv2_backend.get_resource_policy(
            resource_arn=resource_arn,
        )
        return ActionResult({"Policy": policy})

    def describe_backups(self) -> ActionResult:
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        filters = self._get_param("Filters", {})
        shared = self._get_bool_param("Shared")
        sort_ascending = self._get_bool_param("SortAscending")

        backups, next_token = self.cloudhsmv2_backend.describe_backups(
            next_token=next_token,
            max_results=max_results,
            filters=filters,
            shared=shared,
            sort_ascending=sort_ascending,
        )

        return ActionResult(
            {"Backups": [b.to_dict() for b in backups], "NextToken": next_token}
        )

    def put_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy = self._get_param("Policy")

        result = self.cloudhsmv2_backend.put_resource_policy(
            resource_arn=resource_arn,
            policy=policy,
        )
        return ActionResult(result)
