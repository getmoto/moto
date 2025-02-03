"""Handles incoming cloudhsmv2 requests, invokes methods, returns responses."""

import json
from datetime import datetime

from moto.core.responses import BaseResponse

from .models import cloudhsmv2_backends


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class CloudHSMV2Response(BaseResponse):
    """Handler for CloudHSMV2 requests and responses."""

    def __init__(self):
        super().__init__(service_name="cloudhsmv2")

    @property
    def cloudhsmv2_backend(self):
        """Return backend instance specific for this region."""
        return cloudhsmv2_backends[self.current_account][self.region]

    def list_tags(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        resource_id = params.get("ResourceId")
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")

        tag_list, next_token = self.cloudhsmv2_backend.list_tags(
            resource_id=resource_id,
            next_token=next_token,
            max_results=max_results,
        )

        return 200, {}, json.dumps({"TagList": tag_list, "NextToken": next_token})

    def tag_resource(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        resource_id = params.get("ResourceId")
        tag_list = params.get("TagList")

        self.cloudhsmv2_backend.tag_resource(
            resource_id=resource_id,
            tag_list=tag_list,
        )
        return json.dumps(dict())

    def untag_resource(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        resource_id = params.get("ResourceId")
        tag_key_list = params.get("TagKeyList")
        self.cloudhsmv2_backend.untag_resource(
            resource_id=resource_id,
            tag_key_list=tag_key_list,
        )
        return json.dumps(dict())

    def create_cluster(self):
        # Get raw params and print for debugging
        raw_params = self._get_params()

        # Use BaseResponse's _get_param method to get individual parameters directly
        backup_retention_policy = self._get_param("BackupRetentionPolicy")
        hsm_type = self._get_param("HsmType")
        source_backup_id = self._get_param("SourceBackupId")
        subnet_ids = self._get_param("SubnetIds", [])
        network_type = self._get_param("NetworkType", "IPV4")
        tag_list = self._get_param("TagList")
        mode = self._get_param("Mode", "FIPS")

        cluster = self.cloudhsmv2_backend.create_cluster(
            backup_retention_policy=backup_retention_policy,
            hsm_type=hsm_type,
            source_backup_id=source_backup_id,
            subnet_ids=subnet_ids,
            network_type=network_type,
            tag_list=tag_list,
            mode=mode,
        )
        return json.dumps({"Cluster": cluster}, cls=DateTimeEncoder)

    def delete_cluster(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        cluster_id = params.get("ClusterId")
        try:
            cluster = self.cloudhsmv2_backend.delete_cluster(cluster_id=cluster_id)
            return json.dumps({"Cluster": cluster})
        except ValueError as e:
            return self.error("ClusterNotFoundFault", str(e))

    def describe_clusters(self):
        raw_params = list(self._get_params().keys())[0] if self._get_params() else "{}"
        params = json.loads(raw_params)

        filters = params.get("Filters", {})
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")

        clusters, next_token = self.cloudhsmv2_backend.describe_clusters(
            filters=filters,
            next_token=next_token,
            max_results=max_results,
        )

        response = {"Clusters": clusters}
        if next_token:
            response["NextToken"] = next_token

        return json.dumps(response, cls=DateTimeEncoder)
