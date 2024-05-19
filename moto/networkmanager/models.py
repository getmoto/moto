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


class NetworkManagerBackend(BaseBackend):
    """Implementation of NetworkManager APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.global_networks: Dict[str, GlobalNetwork] = {}
        self.tags: TaggingService = TaggingService()

    # add methods from here

    def create_global_network(self, description, tags):
        global_network = GlobalNetwork(description, tags)
        gnw_id = global_network.global_network_id
        self.global_networks[gnw_id] = global_network
        self.tags.tag_resource(gnw_id, tags)
        return global_network


networkmanager_backends = BackendDict(
    NetworkManagerBackend,
    "networkmanager",
    use_boto3_regions=False,
    additional_regions=["global"],
)
