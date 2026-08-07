"""AuroraDSQLBackend class with methods for supported APIs."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import utcnow
from moto.moto_api._internal import mock_random
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.utilities.utils import get_partition

from .exceptions import ConflictException, ResourceNotFoundException


class Cluster(BaseModel, ManagedState):
    """Model for an AuroraDSQL cluster."""

    def __init__(
        self,
        region_name: str,
        account_id: str,
        deletion_protection_enabled: bool | None,
        tags: dict[str, str] | None,
        client_token: str | None,
        kms_encryption_key: str | None = None,
        multi_region_properties: dict[str, Any] | None = None,
        policy: str | None = None,
    ):
        ManagedState.__init__(
            self, "dsql::cluster", transitions=[("CREATING", "ACTIVE")]
        )
        self.region_name = region_name
        self.account_id = account_id
        self.identifier = mock_random.get_random_hex(26)
        self.arn = f"arn:{get_partition(self.region_name)}:dsql:{self.region_name}:{self.account_id}:cluster/{self.identifier}"
        self.creation_time = utcnow()
        self.deletion_protection_enabled = deletion_protection_enabled
        self.tags = tags
        self.client_token = client_token
        self.multi_region_properties = multi_region_properties
        self.policy = policy
        self.policy_version = str(mock_random.uuid4()) if policy is not None else None
        self.endpoint = f"{self.identifier}.{self.region_name}.on.aws"
        self.endpoint_service_name = f"com.amazonaws.{self.region_name}.dsql-7cwu"
        self.encryption_details: dict[str, str] = {
            "encryptionStatus": "ENABLED",
            "encryptionType": (
                "CUSTOMER_MANAGED_KMS_KEY"
                if kms_encryption_key
                else "AWS_OWNED_KMS_KEY"
            ),
        }
        if kms_encryption_key:
            self.encryption_details["kmsKeyArn"] = kms_encryption_key
        self.streams: dict[str, Stream] = OrderedDict()

    def to_summary(self) -> dict[str, str]:
        return {"identifier": self.identifier, "arn": self.arn}


class Stream(BaseModel, ManagedState):
    """Model for an Aurora DSQL change-data-capture stream."""

    def __init__(
        self,
        cluster: Cluster,
        target_definition: dict[str, Any],
        ordering: str,
        format_: str,
        tags: dict[str, str] | None,
        client_token: str | None,
    ):
        ManagedState.__init__(
            self, "dsql::stream", transitions=[("CREATING", "ACTIVE")]
        )
        self.cluster_identifier = cluster.identifier
        self.stream_identifier = mock_random.get_random_hex(26)
        self.arn = f"{cluster.arn}/stream/{self.stream_identifier}"
        self.creation_time = utcnow()
        self.ordering = ordering
        self.format = format_
        self.target_definition = target_definition
        self.tags = tags or {}
        self.client_token = client_token

    def to_summary(self) -> dict[str, Any]:
        return {
            "clusterIdentifier": self.cluster_identifier,
            "streamIdentifier": self.stream_identifier,
            "arn": self.arn,
            "creationTime": self.creation_time,
            "status": self.status,
        }


class AuroraDSQLBackend(BaseBackend):
    """Implementation of AuroraDSQL APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.region_name = region_name
        self.account_id = account_id
        self.partition = get_partition(region_name)
        self.clusters: dict[str, Cluster] = OrderedDict()

    def create_cluster(
        self,
        deletion_protection_enabled: bool,
        tags: dict[str, str] | None,
        client_token: str | None,
        kms_encryption_key: str | None = None,
        multi_region_properties: dict[str, Any] | None = None,
        policy: str | None = None,
    ) -> Cluster:
        if client_token:
            for cluster in self.clusters.values():
                if cluster.client_token == client_token:
                    return cluster
        cluster = Cluster(
            self.region_name,
            self.account_id,
            deletion_protection_enabled,
            tags,
            client_token,
            kms_encryption_key,
            multi_region_properties,
            policy,
        )
        self.clusters[cluster.identifier] = cluster
        return cluster

    def delete_cluster(self, identifier: str) -> Cluster:
        if identifier not in self.clusters:
            arn = f"arn:{get_partition(self.region_name)}:dsql:{self.region_name}:{self.account_id}:cluster/{identifier}"
            raise ResourceNotFoundException(arn, identifier, "cluster")
        cluster = self.clusters[identifier]
        if cluster.deletion_protection_enabled:
            raise ConflictException(
                "Deletion protection is enabled for this cluster.",
                identifier,
                "cluster",
            )
        self.clusters.pop(identifier)
        return cluster

    def list_clusters(
        self, max_results: int | None, next_token: str | None
    ) -> tuple[list[Cluster], str | None]:
        clusters = list(self.clusters.values())
        start = int(next_token or 0)
        end = start + (max_results or 100)
        return clusters[start:end], str(end) if end < len(clusters) else None

    def update_cluster(
        self,
        identifier: str,
        deletion_protection_enabled: bool | None,
        kms_encryption_key: str | None,
        multi_region_properties: dict[str, Any] | None,
    ) -> Cluster:
        cluster = self.get_cluster(identifier)
        if deletion_protection_enabled is not None:
            cluster.deletion_protection_enabled = deletion_protection_enabled
        if multi_region_properties is not None:
            cluster.multi_region_properties = multi_region_properties
        if kms_encryption_key is not None:
            cluster.encryption_details = {
                "encryptionStatus": "ENABLED",
                "encryptionType": "CUSTOMER_MANAGED_KMS_KEY",
                "kmsKeyArn": kms_encryption_key,
            }
        return cluster

    def get_cluster(self, identifier: str) -> Cluster:
        if identifier not in self.clusters:
            arn = f"arn:{get_partition(self.region_name)}:dsql:{self.region_name}:{self.account_id}:cluster/{identifier}"
            raise ResourceNotFoundException(arn, identifier, "cluster")
        cluster = self.clusters[identifier]
        cluster.advance()
        return cluster

    def get_vpc_endpoint_service_name(self, identifier: str) -> dict[str, str]:
        cluster = self.get_cluster(identifier=identifier)
        return {
            "serviceName": cluster.endpoint_service_name,
            "clusterVpcEndpoint": cluster.endpoint,
        }

    def list_tags_for_resource(self, identifier: str) -> dict[str, str]:
        resource = self._get_resource(identifier)
        return resource.tags or {}

    def tag_resource(self, identifier: str, tags: dict[str, str]) -> None:
        resource = self._get_resource(identifier)
        resource.tags = {**(resource.tags or {}), **tags}

    def untag_resource(self, identifier: str, tag_keys: list[str]) -> None:
        resource = self._get_resource(identifier)
        tags = resource.tags or {}
        for key in tag_keys:
            tags.pop(key, None)
        resource.tags = tags

    def put_cluster_policy(
        self, identifier: str, policy: str, expected_policy_version: str | None
    ) -> str:
        cluster = self.get_cluster(identifier)
        self._validate_policy_version(cluster, expected_policy_version)
        cluster.policy = policy
        cluster.policy_version = str(mock_random.uuid4())
        return cluster.policy_version

    def get_cluster_policy(self, identifier: str) -> tuple[str, str]:
        cluster = self.get_cluster(identifier)
        if cluster.policy is None or cluster.policy_version is None:
            raise ResourceNotFoundException(cluster.arn, identifier, "clusterPolicy")
        return cluster.policy, cluster.policy_version

    def delete_cluster_policy(
        self, identifier: str, expected_policy_version: str | None
    ) -> str:
        cluster = self.get_cluster(identifier)
        if cluster.policy is None:
            raise ResourceNotFoundException(cluster.arn, identifier, "clusterPolicy")
        self._validate_policy_version(cluster, expected_policy_version)
        cluster.policy = None
        cluster.policy_version = str(mock_random.uuid4())
        return cluster.policy_version

    def _validate_policy_version(
        self, cluster: Cluster, expected_policy_version: str | None
    ) -> None:
        if (
            expected_policy_version is not None
            and cluster.policy_version != expected_policy_version
        ):
            raise ConflictException(
                "The expected policy version does not match the current version.",
                cluster.identifier,
                "clusterPolicy",
            )

    def create_stream(
        self,
        cluster_identifier: str,
        target_definition: dict[str, Any],
        ordering: str,
        format_: str,
        tags: dict[str, str] | None,
        client_token: str | None,
    ) -> Stream:
        cluster = self.get_cluster(cluster_identifier)
        if client_token:
            for stream in cluster.streams.values():
                if stream.client_token == client_token:
                    return stream
        stream = Stream(
            cluster, target_definition, ordering, format_, tags, client_token
        )
        cluster.streams[stream.stream_identifier] = stream
        return stream

    def get_stream(self, cluster_identifier: str, stream_identifier: str) -> Stream:
        cluster = self.get_cluster(cluster_identifier)
        if stream_identifier not in cluster.streams:
            raise ResourceNotFoundException(
                f"{cluster.arn}/stream/{stream_identifier}", stream_identifier, "stream"
            )
        stream = cluster.streams[stream_identifier]
        stream.advance()
        return stream

    def list_streams(
        self,
        cluster_identifier: str,
        max_results: int | None,
        next_token: str | None,
    ) -> tuple[list[Stream], str | None]:
        cluster = self.get_cluster(cluster_identifier)
        streams = list(cluster.streams.values())
        start = int(next_token or 0)
        end = start + (max_results or 100)
        return streams[start:end], str(end) if end < len(streams) else None

    def delete_stream(self, cluster_identifier: str, stream_identifier: str) -> Stream:
        stream = self.get_stream(cluster_identifier, stream_identifier)
        cluster = self.get_cluster(cluster_identifier)
        cluster.streams.pop(stream_identifier)
        return stream

    def _get_resource(self, identifier: str) -> Cluster | Stream:
        if "/stream/" not in identifier:
            return self.get_cluster(identifier)
        cluster_identifier, stream_identifier = identifier.split("/stream/", 1)
        return self.get_stream(cluster_identifier, stream_identifier)


dsql_backends = BackendDict(
    AuroraDSQLBackend,
    "dsql",
    # currently botocore does not provide a dsql endpoint
    # https://github.com/boto/botocore/blob/e07cddc333fe4fb90efcd5d04324dd83f9cc3a57/botocore/data/endpoints.json
    use_boto3_regions=False,
    additional_regions=["us-east-1", "us-east-2"],
)
