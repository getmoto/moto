"""NetworkManagerBackend class with methods for supported APIs."""

import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.ec2.utils import HEX_CHARS
from moto.utilities.tagging_service import TaggingService


class GlobalNetwork(BaseModel):
    def __init__(
        self, description: Optional[str], tags: Optional[List[Dict[str, str]]]
    ):
        self.description = description
        self.tags = tags
        self.global_network_id = "global-network-" + "".join(
            random.choice(HEX_CHARS) for _ in range(18)
        )
        self.global_network_arn = f"arn:aws:networkmanager:123456789012:global-network/{self.global_network_id}"
        self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.state = "PENDING"

    def to_dict(self):
        return {
            "GlobalNetworkId": self.global_network_id,
            "GlobalNetworkArn": self.global_network_arn,
            "Description": self.description,
            "Tags": self.tags,
            "State": self.state,
            "CreatedAt": self.created_at,
        }


class CoreNetwork(BaseModel):
    def __init__(
        self,
        global_network_id: str,
        description: Optional[str],
        tags: Optional[List[Dict[str, str]]],
        policy_document: str,
        client_token: str,
    ):
        self.global_network_id = global_network_id
        self.description = description
        self.tags = tags
        self.policy_document = policy_document
        self.client_token = client_token
        self.core_network_id = "core-network-" + "".join(
            random.choice(HEX_CHARS) for _ in range(18)
        )
        self.core_network_arn = (
            f"arn:aws:networkmanager:123456789012:core-network/{self.core_network_id}"
        )

        self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.state = "PENDING"

    def to_dict(self):
        return {
            "CoreNetworkId": self.core_network_id,
            "CoreNetworkArn": self.core_network_arn,
            "GlobalNetworkId": self.global_network_id,
            "Description": self.description,
            "Tags": self.tags,
            "PolicyDocument": self.policy_document,
            "State": self.state,
            "CreatedAt": self.created_at,
        }


class NetworkManagerBackend(BaseBackend):
    """Implementation of NetworkManager APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.global_networks: Dict[str, GlobalNetwork] = {}
        self.core_networks: Dict[str, CoreNetwork] = {}
        self.tags: TaggingService = TaggingService()

    # add methods from here

    def create_global_network(
        self, description: Optional[str], tags: Optional[List[Dict[str, str]]]
    ) -> GlobalNetwork:
        global_network = GlobalNetwork(description, tags)
        gnw_id = global_network.global_network_id
        self.global_networks[gnw_id] = global_network
        self.tags.tag_resource(gnw_id, tags)
        return global_network

    def create_core_network(
        self,
        global_network_id: str,
        description: Optional[str],
        tags: Optional[List[Dict[str, str]]],
        policy_document: str,
        client_token: str,
    ) -> CoreNetwork:
        # check if global network exists
        if global_network_id not in self.global_networks:
            raise Exception("Resource not found")

        core_network = CoreNetwork(
            global_network_id, description, tags, policy_document, client_token
        )
        cnw_id = core_network.core_network_id
        self.tags.tag_resource(cnw_id, tags)
        self.core_networks[cnw_id] = core_network
        return core_network

    def delete_core_network(self, core_network_id) -> CoreNetwork:
        # Check if core network exists
        if core_network_id not in self.core_networks:
            raise Exception("Resource not found")
        core_network = self.core_networks.pop(core_network_id)
        core_network.state = "DELETING"
        return core_network

    def tag_resource(self, resource_arn, tags):
        # implement here
        return

    def untag_resource(self, resource_arn, tag_keys):
        # implement here
        return

    def list_core_networks(
        self, max_results, next_token
    ) -> Tuple[List[CoreNetwork], str]:
        return list(self.core_networks.values()), next_token

    def get_core_network(self, core_network_id) -> CoreNetwork:
        if core_network_id not in self.core_networks:
            raise Exception("Resource not found")
        core_network = self.core_networks[core_network_id]
        return core_network


networkmanager_backends = BackendDict(
    NetworkManagerBackend,
    "networkmanager",
    use_boto3_regions=False,
    additional_regions=["global"],
)
