"""Handles incoming dsql requests, invokes methods, returns responses."""

import json
from typing import Any
from urllib.parse import unquote

from moto.core.responses import ActionResult, BaseResponse

from .models import AuroraDSQLBackend, dsql_backends


class AuroraDSQLResponse(BaseResponse):
    """Handler for AuroraDSQL requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="dsql")

    @property
    def dsql_backend(self) -> AuroraDSQLBackend:
        """Return backend instance specific for this region."""
        return dsql_backends[self.current_account][self.region]

    def create_cluster(self) -> ActionResult:
        params = json.loads(self.body)
        deletion_protection_enabled = params.get("deletionProtectionEnabled", True)
        tags = params.get("tags")
        client_token = params.get("clientToken")
        kms_encryption_key = params.get("kmsEncryptionKey")
        multi_region_properties = params.get("multiRegionProperties")
        policy = params.get("policy")
        cluster = self.dsql_backend.create_cluster(
            deletion_protection_enabled=deletion_protection_enabled,
            tags=tags,
            client_token=client_token,
            kms_encryption_key=kms_encryption_key,
            multi_region_properties=multi_region_properties,
            policy=policy,
        )
        return ActionResult(cluster)

    def delete_cluster(self) -> ActionResult:
        identifier = self.path.split("/")[-1]
        cluster = self.dsql_backend.delete_cluster(identifier=identifier)
        result = {
            "identifier": cluster.identifier,
            "arn": cluster.arn,
            "status": "DELETING",
            "creationTime": cluster.creation_time,
        }
        return ActionResult(result)

    def get_cluster(self) -> ActionResult:
        identifier = self.path.split("/")[-1]
        cluster = self.dsql_backend.get_cluster(identifier=identifier)
        return ActionResult(cluster)

    def list_clusters(self) -> ActionResult:
        clusters, next_token = self.dsql_backend.list_clusters(
            max_results=self._get_int_param("max-results"),
            next_token=self._get_param("next-token"),
        )
        result: dict[str, Any] = {
            "clusters": [cluster.to_summary() for cluster in clusters]
        }
        if next_token:
            result["nextToken"] = next_token
        return ActionResult(result)

    def update_cluster(self) -> ActionResult:
        params = json.loads(self.body)
        identifier = self.path.split("/")[-1]
        cluster = self.dsql_backend.update_cluster(
            identifier=identifier,
            deletion_protection_enabled=params.get("deletionProtectionEnabled"),
            kms_encryption_key=params.get("kmsEncryptionKey"),
            multi_region_properties=params.get("multiRegionProperties"),
        )
        return ActionResult(
            {
                "identifier": cluster.identifier,
                "arn": cluster.arn,
                "status": cluster.status,
                "creationTime": cluster.creation_time,
            }
        )

    def get_vpc_endpoint_service_name(self) -> ActionResult:
        identifier = self.path.split("/")[-2]
        result = self.dsql_backend.get_vpc_endpoint_service_name(identifier)
        return ActionResult(result)

    def list_tags_for_resource(self) -> ActionResult:
        arn = unquote(self.path.split("/tags/", 1)[-1])
        identifier = arn.split("cluster/")[-1]
        tags = self.dsql_backend.list_tags_for_resource(identifier)
        return ActionResult({"tags": tags})

    def tag_resource(self) -> ActionResult:
        params = json.loads(self.body)
        arn = unquote(self.path.split("/tags/", 1)[-1])
        identifier = arn.split("cluster/")[-1]
        self.dsql_backend.tag_resource(identifier, params["tags"])
        return ActionResult({})

    def untag_resource(self) -> ActionResult:
        arn = unquote(self.path.split("/tags/", 1)[-1])
        identifier = arn.split("cluster/")[-1]
        self.dsql_backend.untag_resource(
            identifier, self.querystring.get("tagKeys", [])
        )
        return ActionResult({})

    def put_cluster_policy(self) -> ActionResult:
        params = json.loads(self.body)
        identifier = self.path.split("/")[-2]
        version = self.dsql_backend.put_cluster_policy(
            identifier, params["policy"], params.get("expectedPolicyVersion")
        )
        return ActionResult({"policyVersion": version})

    def get_cluster_policy(self) -> ActionResult:
        identifier = self.path.split("/")[-2]
        policy, version = self.dsql_backend.get_cluster_policy(identifier)
        return ActionResult({"policy": policy, "policyVersion": version})

    def delete_cluster_policy(self) -> ActionResult:
        identifier = self.path.split("/")[-2]
        version = self.dsql_backend.delete_cluster_policy(
            identifier, self._get_param("expected-policy-version")
        )
        return ActionResult({"policyVersion": version})

    def create_stream(self) -> ActionResult:
        params = json.loads(self.body)
        cluster_identifier = self.path.split("/")[-1]
        stream = self.dsql_backend.create_stream(
            cluster_identifier=cluster_identifier,
            target_definition=params["targetDefinition"],
            ordering=params["ordering"],
            format_=params["format"],
            tags=params.get("tags"),
            client_token=params.get("clientToken"),
        )
        return ActionResult(stream)

    def get_stream(self) -> ActionResult:
        cluster_identifier, stream_identifier = self.path.split("/")[-2:]
        stream = self.dsql_backend.get_stream(cluster_identifier, stream_identifier)
        return ActionResult(stream)

    def list_streams(self) -> ActionResult:
        cluster_identifier = self.path.split("/")[-1]
        streams, next_token = self.dsql_backend.list_streams(
            cluster_identifier=cluster_identifier,
            max_results=self._get_int_param("max-results"),
            next_token=self._get_param("next-token"),
        )
        result: dict[str, Any] = {
            "streams": [stream.to_summary() for stream in streams]
        }
        if next_token:
            result["nextToken"] = next_token
        return ActionResult(result)

    def delete_stream(self) -> ActionResult:
        cluster_identifier, stream_identifier = self.path.split("/")[-2:]
        stream = self.dsql_backend.delete_stream(cluster_identifier, stream_identifier)
        return ActionResult(
            {
                "clusterIdentifier": stream.cluster_identifier,
                "streamIdentifier": stream.stream_identifier,
                "arn": stream.arn,
                "status": "DELETING",
                "creationTime": stream.creation_time,
            }
        )
