"""CloudHSMV2Backend class with methods for supported APIs."""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.utils import utcnow
from moto.utilities.paginator import Paginator

from .exceptions import InvalidRequestException, ResourceNotFoundException


class Cluster:
    def __init__(
        self,
        backup_retention_policy: Optional[Dict[str, str]],
        hsm_type: str,
        source_backup_id: Optional[str],
        subnet_ids: List[str],
        network_type: str = "IPV4",
        tag_list: Optional[List[Dict[str, str]]] = None,
        mode: str = "DEFAULT",
        region_name: str = "us-east-1",
    ):
        self.cluster_id = str(uuid.uuid4())
        self.backup_policy = "DEFAULT"
        self.backup_retention_policy = backup_retention_policy
        self.create_timestamp = utcnow()
        self.hsms: List[Dict[str, Any]] = []
        self.hsm_type = hsm_type
        self.source_backup_id = source_backup_id
        self.state = "CREATE_IN_PROGRESS"
        self.state_message = "Cluster creation in progress"
        self.subnet_mapping = {subnet_id: region_name for subnet_id in subnet_ids}
        self.vpc_id = "vpc-" + str(uuid.uuid4())[:8]
        self.network_type = network_type
        self.certificates = {
            "ClusterCsr": "",
            "HsmCertificate": "",
            "AwsHardwareCertificate": "",
            "ManufacturerHardwareCertificate": "",
            "ClusterCertificate": "",
        }
        self.tag_list = tag_list or []
        self.mode = mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "BackupPolicy": self.backup_policy,
            "BackupRetentionPolicy": self.backup_retention_policy,
            "ClusterId": self.cluster_id,
            "CreateTimestamp": self.create_timestamp,
            "Hsms": self.hsms,
            "HsmType": self.hsm_type,
            "SourceBackupId": self.source_backup_id,
            "State": self.state,
            "StateMessage": self.state_message,
            "SubnetMapping": self.subnet_mapping,
            "VpcId": self.vpc_id,
            "NetworkType": self.network_type,
            "Certificates": self.certificates,
            "TagList": self.tag_list,
            "Mode": self.mode,
        }


class Backup:
    def __init__(
        self,
        cluster_id: str,
        hsm_type: str,
        mode: str,
        tag_list: Optional[List[Dict[str, str]]],
        source_backup: Optional[str] = None,
        source_cluster: Optional[str] = None,
        source_region: Optional[str] = None,
        never_expires: bool = False,
        region_name: str = "us-east-1",
    ):
        self.backup_id = str(uuid.uuid4())
        self.backup_arn = (
            f"arn:aws:cloudhsm:{region_name}:123456789012:backup/{self.backup_id}"
        )
        self.backup_state = "READY"
        self.cluster_id = cluster_id
        self.create_timestamp = utcnow()
        self.copy_timestamp = utcnow() if source_backup else None
        self.never_expires = never_expires
        self.source_region = source_region
        self.source_backup = source_backup
        self.source_cluster = source_cluster
        self.delete_timestamp = None
        self.tag_list = tag_list or []
        self.hsm_type = hsm_type
        self.mode = mode

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "BackupId": self.backup_id,
            "BackupArn": self.backup_arn,
            "BackupState": self.backup_state,
            "ClusterId": self.cluster_id,
            "CreateTimestamp": self.create_timestamp,
            "NeverExpires": self.never_expires,
            "TagList": self.tag_list,
            "HsmType": self.hsm_type,
            "Mode": self.mode,
        }

        if self.copy_timestamp:
            result["CopyTimestamp"] = self.copy_timestamp
        if self.source_region:
            result["SourceRegion"] = self.source_region
        if self.source_backup:
            result["SourceBackup"] = self.source_backup
        if self.source_cluster:
            result["SourceCluster"] = self.source_cluster
        if self.delete_timestamp:
            result["DeleteTimestamp"] = self.delete_timestamp

        return result


class CloudHSMV2Backend(BaseBackend):
    """Implementation of CloudHSMV2 APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.tags: Dict[str, List[Dict[str, str]]] = {}
        self.clusters: Dict[str, Cluster] = {}
        self.resource_policies: Dict[str, str] = {}
        self.backups: Dict[str, Backup] = {}

    def list_tags(
        self, resource_id: str, next_token: str, max_results: int
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """List tags for a CloudHSM resource."""
        if resource_id not in self.tags:
            return [], None

        tags = sorted(self.tags.get(resource_id, []), key=lambda x: x["Key"])

        if not max_results:
            return tags, None

        # Add padding to the token if it exists
        if next_token:
            padding = 4 - (len(next_token) % 4)
            if padding != 4:
                next_token = next_token + ("=" * padding)

        paginator = Paginator(
            max_results=max_results,
            unique_attribute="Key",
            starting_token=next_token,
            fail_on_invalid_token=False,
        )

        results, token = paginator.paginate(tags)

        # Remove padding from the token before returning
        if token:
            token = token.rstrip("=")

        return results, token

    def tag_resource(
        self, resource_id: str, tag_list: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Add or update tags for a CloudHSM resource."""
        if resource_id is None:
            raise ValueError("ResourceId must not be None")
        if tag_list is None:
            raise ValueError("TagList must not be None")

        if resource_id not in self.tags:
            self.tags[resource_id] = []

        # Update existing tags and add new ones
        for new_tag in tag_list:
            tag_exists = False
            for existing_tag in self.tags[resource_id]:
                if existing_tag["Key"] == new_tag["Key"]:
                    existing_tag["Value"] = new_tag["Value"]
                    tag_exists = True
                    break
            if not tag_exists:
                self.tags[resource_id].append(new_tag)

        return {}

    def untag_resource(
        self, resource_id: str, tag_key_list: List[str]
    ) -> Dict[str, Any]:
        """Remove tags from a CloudHSM resource."""
        if resource_id is None:
            raise ValueError("ResourceId must not be None")
        if tag_key_list is None:
            raise ValueError("TagKeyList must not be None")

        if resource_id in self.tags:
            self.tags[resource_id] = [
                tag for tag in self.tags[resource_id] if tag["Key"] not in tag_key_list
            ]

        return {}

    def create_cluster(
        self,
        backup_retention_policy: Optional[Dict[str, str]],
        hsm_type: str,
        source_backup_id: Optional[str],
        subnet_ids: List[str],
        network_type: Optional[str],
        tag_list: Optional[List[Dict[str, str]]],
        mode: Optional[str],
    ) -> Dict[str, Any]:
        cluster = Cluster(
            backup_retention_policy=backup_retention_policy,
            hsm_type=hsm_type,
            source_backup_id=source_backup_id,
            subnet_ids=subnet_ids,
            network_type=network_type or "IPV4",
            tag_list=tag_list,
            mode=mode or "DEFAULT",
            region_name=self.region_name,
        )
        self.clusters[cluster.cluster_id] = cluster

        # Automatically create a backup for the new cluster
        backup = Backup(
            cluster_id=cluster.cluster_id,
            hsm_type=hsm_type,
            mode=mode or "DEFAULT",
            tag_list=tag_list,
            region_name=self.region_name,
        )
        self.backups[backup.backup_id] = backup

        return cluster.to_dict()

    def delete_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """Delete a CloudHSM cluster."""
        if cluster_id not in self.clusters:
            raise ValueError(f"Cluster {cluster_id} not found")

        cluster = self.clusters[cluster_id]
        cluster.state = "DELETE_IN_PROGRESS"
        cluster.state_message = "Cluster deletion in progress"

        del self.clusters[cluster_id]

        return cluster.to_dict()

    def describe_clusters(
        self, filters: Dict[str, List[str]], next_token: str, max_results: int
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Describe CloudHSM clusters."""
        clusters = list(self.clusters.values())

        # If we have filters, filter the resource
        if filters:
            for key, values in filters.items():
                if key == "clusterIds":
                    clusters = [c for c in clusters if c.cluster_id in values]
                elif key == "states":
                    clusters = [c for c in clusters if c.state in values]
                elif key == "vpcIds":
                    clusters = [c for c in clusters if c.vpc_id in values]

        # Sort clusters by creation timestamp
        clusters = sorted(clusters, key=lambda x: x.create_timestamp)

        if not max_results:
            return [c.to_dict() for c in clusters], None

        paginator = Paginator(
            max_results=max_results,
            unique_attribute="ClusterId",
            starting_token=next_token,
            fail_on_invalid_token=False,
        )

        results, token = paginator.paginate([c.to_dict() for c in clusters])
        return results, token

    def get_resource_policy(self, resource_arn: str) -> Optional[str]:
        """Gets the resource policy attached to a CloudHSM backup."""
        if not resource_arn:
            raise InvalidRequestException("ResourceArn must not be empty")

        # Verify backup exists
        matching_backup = None
        for backup in self.backups.values():
            if backup.backup_arn == resource_arn:
                matching_backup = backup
                break
        if not matching_backup:
            raise ResourceNotFoundException(f"Backup with ARN {resource_arn} not found")

        # Return the policy if it exists, otherwise return None
        return self.resource_policies.get(resource_arn)

    def describe_backups(
        self,
        next_token: Optional[str],
        max_results: Optional[int],
        filters: Optional[Dict[str, List[str]]],
        shared: Optional[bool],
        sort_ascending: Optional[bool],
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Describe CloudHSM backups."""
        backups = list(self.backups.values())

        if filters:
            for key, values in filters.items():
                if key == "backupIds":
                    backups = [b for b in backups if b.backup_id in values]
                elif key == "sourceBackupIds":
                    backups = [b for b in backups if b.source_backup in values]
                elif key == "clusterIds":
                    backups = [b for b in backups if b.cluster_id in values]
                elif key == "states":
                    backups = [b for b in backups if b.backup_state in values]
                elif key == "neverExpires":
                    never_expires = values[0].lower() == "true"
                    backups = [b for b in backups if b.never_expires == never_expires]

        # Sort backups
        backups.sort(
            key=lambda x: x.create_timestamp,
            reverse=not sort_ascending if sort_ascending is not None else True,
        )
        if not max_results:
            return [b.to_dict() for b in backups], None

        paginator = Paginator(
            max_results=max_results,
            unique_attribute="BackupId",
            starting_token=next_token,
            fail_on_invalid_token=False,
        )
        results, token = paginator.paginate([b.to_dict() for b in backups])
        return results, token

    def put_resource_policy(self, resource_arn: str, policy: str) -> Dict[str, str]:
        # Find the backup
        matching_backup = None
        for backup in self.backups.values():
            if backup.backup_arn == resource_arn:
                matching_backup = backup
                break
        if not matching_backup:
            raise ResourceNotFoundException(f"Backup with ARN {resource_arn} not found")

        if matching_backup.backup_state != "READY":
            raise InvalidRequestException(
                f"Backup {matching_backup.backup_id} is not in READY state"
            )

        self.resource_policies[resource_arn] = policy
        return {"ResourceArn": resource_arn, "Policy": policy}


cloudhsmv2_backends = BackendDict(CloudHSMV2Backend, "cloudhsmv2")
