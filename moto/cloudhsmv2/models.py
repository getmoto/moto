"""CloudHSMV2Backend class with methods for supported APIs."""

import uuid
from typing import Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.utils import utcnow
from moto.utilities.paginator import Paginator


class Cluster:
    def __init__(
        self,
        backup_retention_policy: Optional[Dict[str, str]],
        hsm_type: str,
        source_backup_id: Optional[str],
        subnet_ids: List[str],
        network_type: str,
        tag_list: Optional[List[Dict[str, str]]],
        mode: str,
        region_name: str,
    ):
        self.cluster_id = str(uuid.uuid4())
        self.backup_policy = "DEFAULT"
        self.backup_retention_policy = backup_retention_policy
        self.create_timestamp = utcnow()
        self.hsms = []
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

    def to_dict(self) -> Dict:
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


class CloudHSMV2Backend(BaseBackend):
    """Implementation of CloudHSMV2 APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.tags = {}
        self.clusters = {}

    def list_tags(self, resource_id, next_token, max_results):
        """List tags for a CloudHSM resource.

        Args:
            resource_id (str): The identifier of the resource to list tags for
            next_token (str): Token for pagination
            max_results (int): Maximum number of results to return

        Returns:
            tuple: (list of tags, next token)
        """
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

    def tag_resource(self, resource_id, tag_list):
        """Add or update tags for a CloudHSM resource.

        Args:
            resource_id (str): The identifier of the resource to tag
            tag_list (list): List of tag dictionaries with 'Key' and 'Value' pairs

        Returns:
            dict: Empty dictionary per AWS spec

        Raises:
            ValueError: If resource_id or tag_list is None
        """
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

    def untag_resource(self, resource_id, tag_key_list):
        """Remove tags from a CloudHSM resource.

        Args:
            resource_id (str): The identifier of the resource to untag
            tag_key_list (list): List of tag keys to remove

        Returns:
            dict: Empty dictionary per AWS spec

        Raises:
            ValueError: If resource_id or tag_key_list is None
        """
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
        network_type: str,
        tag_list: Optional[List[Dict[str, str]]],
        mode: str,
    ) -> Dict:
        cluster = Cluster(
            backup_retention_policy=backup_retention_policy,
            hsm_type=hsm_type,
            source_backup_id=source_backup_id,
            subnet_ids=subnet_ids,
            network_type=network_type,
            tag_list=tag_list,
            mode=mode,
            region_name=self.region_name,
        )
        self.clusters[cluster.cluster_id] = cluster
        return cluster.to_dict()

    def delete_cluster(self, cluster_id: str) -> Dict:
        """Delete a CloudHSM cluster.

        Args:
            cluster_id (str): The identifier of the cluster to delete

        Returns:
            dict: The deleted cluster details

        Raises:
            ValueError: If cluster_id is not found
        """
        if cluster_id not in self.clusters:
            raise ValueError(f"Cluster {cluster_id} not found")

        cluster = self.clusters[cluster_id]
        cluster.state = "DELETE_IN_PROGRESS"
        cluster.state_message = "Cluster deletion in progress"

        # Remove the cluster from the backend
        del self.clusters[cluster_id]

        return cluster.to_dict()

    def describe_clusters(self, filters, next_token, max_results):
        """Describe CloudHSM clusters.

        Args:
            filters (dict): Filters to apply
            next_token (str): Token for pagination
            max_results (int): Maximum number of results to return

        Returns:
            tuple: (list of clusters, next token)
        """
        clusters = list(self.clusters.values())

        # Apply filters if provided
        if filters:
            for key, values in filters.items():
                if key == "clusterIds":
                    clusters = [c for c in clusters if c.cluster_id in values]
                elif key == "states":
                    clusters = [c for c in clusters if c.state in values]
                elif key == "vpcIds":
                    clusters = [c for c in clusters if c.vpc_id in values]

        # Sort clusters by creation timestamp for consistent pagination
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


cloudhsmv2_backends = BackendDict(CloudHSMV2Backend, "cloudhsmv2")
