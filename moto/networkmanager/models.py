"""NetworkManagerBackend class with methods for supported APIs."""

import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.ec2.utils import HEX_CHARS

from .exceptions import ResourceNotFound, ValidationError


class GlobalNetwork(BaseModel):
    def __init__(
        self,
        account_id: str,
        description: Optional[str],
        tags: Optional[List[Dict[str, str]]],
    ):
        self.description = description
        self.tags = tags or []
        self.global_network_id = "global-network-" + "".join(
            random.choice(HEX_CHARS) for _ in range(18)
        )
        self.global_network_arn = f"arn:aws:networkmanager:{account_id}:global-network/{self.global_network_id}"
        self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.state = "PENDING"

    def to_dict(self) -> Dict[str, Any]:
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
        account_id: str,
        global_network_id: str,
        description: Optional[str],
        tags: Optional[List[Dict[str, str]]],
        policy_document: str,
        client_token: str,
    ):
        self.global_network_id = global_network_id
        self.description = description
        self.tags = tags or []
        self.policy_document = policy_document
        self.client_token = client_token
        self.core_network_id = "core-network-" + "".join(
            random.choice(HEX_CHARS) for _ in range(18)
        )
        self.core_network_arn = (
            f"arn:aws:networkmanager:{account_id}:core-network/{self.core_network_id}"
        )

        self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.state = "PENDING"

    def to_dict(self) -> Dict[str, Any]:
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

    def __init__(self, region_name, account_id) -> None:
        super().__init__(region_name, account_id)
        self.global_networks: Dict[str, GlobalNetwork] = {}
        self.core_networks: Dict[str, CoreNetwork] = {}

    # add methods from here

    def create_global_network(
        self,
        description: Optional[str],
        tags: Optional[List[Dict[str, str]]],
    ) -> GlobalNetwork:
        global_network = GlobalNetwork(
            description=description,
            tags=tags,
            account_id=self.account_id,
        )
        gnw_id = global_network.global_network_id
        self.global_networks[gnw_id] = global_network
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
            raise ResourceNotFound("Resource not found.")

        core_network = CoreNetwork(
            global_network_id=global_network_id,
            description=description,
            tags=tags,
            policy_document=policy_document,
            client_token=client_token,
            account_id=self.account_id,
        )
        cnw_id = core_network.core_network_id
        self.core_networks[cnw_id] = core_network
        return core_network

    def delete_core_network(self, core_network_id: str) -> CoreNetwork:
        # Check if core network exists
        if core_network_id not in self.core_networks:
            raise ResourceNotFound("Resource not found.")
        core_network = self.core_networks.pop(core_network_id)
        core_network.state = "DELETING"
        return core_network

    def tag_resource(self, resource_arn:str, tags:List[Dict[str,Any]]) -> None:
        resource = self._get_resource_from_arn(resource_arn)
        resource.tags.extend(tags)

    def untag_resource(self, resource_arn:str, tag_keys: List[str]) -> None:
        resource = self._get_resource_from_arn(resource_arn)
        resource.tags = [tag for tag in resource.tags if tag["Key"] not in tag_keys]

    def list_core_networks(
        self, max_results:int, next_token:str
    ) -> Tuple[List[CoreNetwork], str]:
        return list(self.core_networks.values()), next_token

    def get_core_network(self, core_network_id:str) -> CoreNetwork:
        if core_network_id not in self.core_networks:
            raise ResourceNotFound
        core_network = self.core_networks[core_network_id]
        return core_network

    def _get_resource_from_arn(self, arn: str) -> Any:
        resources = {
            "core-network": self.core_networks,
            "global-network": self.global_networks,
        }
        target_resource, target_name = arn.split(":")[-1].split("/")
        try:
            resource = resources.get(target_resource).get(target_name)  # type: ignore
        except KeyError:
            message = f"Could not find {target_resource} with name {target_name}"
            raise ValidationError(message=message)
        return resource

    def describe_global_networks(
        self,
        global_network_ids: List[str],
        max_results: int,
        next_token: str,
    ) -> Tuple[List[GlobalNetwork], str]:
        queried_global_networks = []
        if not global_network_ids:
            queried_global_networks = list(self.global_networks.values())
        elif isinstance(global_network_ids, str):
            if global_network_ids not in self.global_networks:
                raise ResourceNotFound
            queried_global_networks.append(self.global_networks[global_network_ids])
        else:
            for id in global_network_ids:
                if id in self.global_networks:
                    global_network = self.global_networks[id]
                    queried_global_networks.append(global_network)
        return queried_global_networks, next_token


networkmanager_backends = BackendDict(
    NetworkManagerBackend,
    "networkmanager",
    use_boto3_regions=False,
    additional_regions=["global"],
)
