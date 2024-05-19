"""NetworkManagerBackend class with methods for supported APIs."""

from typing import Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService


class GlobalNetwork(BaseModel):
    def __init__(
        self, description: Optional[str], tags: Optional[List[Dict[str, str]]]
    ):
        self.description = description
        self.tags = tags
        self.global_network_id = "global-network-1"
        self.global_network_arn = "arn:aws:networkmanager:us-west-2:123456789012:global-network/global-network-1"
        self.created_at = "2021-07-15T12:34:56Z"
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
        self.core_network_id = "core-network-1"
        self.core_network_arn = (
            "arn:aws:networkmanager:us-west-2:123456789012:core-network/core-network-1"
        )
        self.created_at = "2021-07-15T12:34:56Z"
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


networkmanager_backends = BackendDict(
    NetworkManagerBackend,
    "networkmanager",
    use_boto3_regions=False,
    additional_regions=["global"],
)
