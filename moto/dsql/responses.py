"""Handles incoming dsql requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import AuroraDSQLBackend, dsql_backends


class AuroraDSQLResponse(BaseResponse):
    """Handler for AuroraDSQL requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="dsql")
        self.automated_parameter_parsing = True

    @property
    def dsql_backend(self) -> AuroraDSQLBackend:
        """Return backend instance specific for this region."""
        return dsql_backends[self.current_account][self.region]

    def create_cluster(self) -> ActionResult:
        deletion_protection_enabled = self._get_bool_param(
            "deletionProtectionEnabled", True
        )
        tags = self._get_param("tags")
        client_token = self._get_param("clientToken")
        kms_encryption_key = self._get_param("kmsEncryptionKey")
        multi_region_properties = self._get_param("multiRegionProperties")
        policy = self._get_param("policy")
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
        identifier = self._get_param("identifier")
        cluster = self.dsql_backend.delete_cluster(identifier=identifier)
        result = {
            "identifier": cluster.identifier,
            "arn": cluster.arn,
            "status": "DELETING",
            "creationTime": cluster.creation_time,
        }
        return ActionResult(result)

    def get_cluster(self) -> ActionResult:
        identifier = self._get_param("identifier")
        cluster = self.dsql_backend.get_cluster(identifier=identifier)
        return ActionResult(cluster)

    def list_clusters(self) -> ActionResult:
        clusters, next_token = self.dsql_backend.list_clusters(
            max_results=self._get_param("maxResults"),
            next_token=self._get_param("nextToken"),
        )
        result: dict[str, Any] = {
            "clusters": [cluster.to_summary() for cluster in clusters]
        }
        if next_token:
            result["nextToken"] = next_token
        return ActionResult(result)

    def update_cluster(self) -> ActionResult:
        identifier = self._get_param("identifier")
        cluster = self.dsql_backend.update_cluster(
            identifier=identifier,
            deletion_protection_enabled=self._get_bool_param(
                "deletionProtectionEnabled"
            ),
            kms_encryption_key=self._get_param("kmsEncryptionKey"),
            multi_region_properties=self._get_param("multiRegionProperties"),
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
        identifier = self._get_param("identifier")
        result = self.dsql_backend.get_vpc_endpoint_service_name(identifier)
        return ActionResult(result)

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tags = self.dsql_backend.list_tags_for_resource(resource_arn)
        return ActionResult({"tags": tags})

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        self.dsql_backend.tag_resource(resource_arn, self._get_param("tags"))
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        self.dsql_backend.untag_resource(resource_arn, self._get_param("tagKeys", []))
        return EmptyResult()

    def put_cluster_policy(self) -> ActionResult:
        identifier = self._get_param("identifier")
        version = self.dsql_backend.put_cluster_policy(
            identifier,
            self._get_param("policy"),
            self._get_param("expectedPolicyVersion"),
        )
        return ActionResult({"policyVersion": version})

    def get_cluster_policy(self) -> ActionResult:
        identifier = self._get_param("identifier")
        policy, version = self.dsql_backend.get_cluster_policy(identifier)
        return ActionResult({"policy": policy, "policyVersion": version})

    def delete_cluster_policy(self) -> ActionResult:
        identifier = self._get_param("identifier")
        version = self.dsql_backend.delete_cluster_policy(
            identifier, self._get_param("expectedPolicyVersion")
        )
        return ActionResult({"policyVersion": version})

    def create_stream(self) -> ActionResult:
        cluster_identifier = self._get_param("clusterIdentifier")
        stream = self.dsql_backend.create_stream(
            cluster_identifier=cluster_identifier,
            target_definition=self._get_param("targetDefinition"),
            ordering=self._get_param("ordering"),
            format_=self._get_param("format"),
            tags=self._get_param("tags"),
            client_token=self._get_param("clientToken"),
        )
        return ActionResult(stream)

    def get_stream(self) -> ActionResult:
        cluster_identifier = self._get_param("clusterIdentifier")
        stream_identifier = self._get_param("streamIdentifier")
        stream = self.dsql_backend.get_stream(cluster_identifier, stream_identifier)
        return ActionResult(stream)

    def list_streams(self) -> ActionResult:
        cluster_identifier = self._get_param("clusterIdentifier")
        streams, next_token = self.dsql_backend.list_streams(
            cluster_identifier=cluster_identifier,
            max_results=self._get_param("maxResults"),
            next_token=self._get_param("nextToken"),
        )
        result: dict[str, Any] = {
            "streams": [stream.to_summary() for stream in streams]
        }
        if next_token:
            result["nextToken"] = next_token
        return ActionResult(result)

    def delete_stream(self) -> ActionResult:
        cluster_identifier = self._get_param("clusterIdentifier")
        stream_identifier = self._get_param("streamIdentifier")
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
