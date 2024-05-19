"""Handles incoming networkmanager requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import networkmanager_backends


class NetworkManagerResponse(BaseResponse):
    """Handler for NetworkManager requests and responses."""

    def __init__(self):
        super().__init__(service_name="networkmanager")

    @property
    def networkmanager_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # networkmanager_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return networkmanager_backends[self.current_account]["global"]

    # add methods from here

    def create_global_network(self) -> str:
        params = json.loads(self.body)
        description = params.get("Description")
        tags = params.get("Tags")
        global_network = self.networkmanager_backend.create_global_network(
            description=description,
            tags=tags,
        )
        return json.dumps(dict(GlobalNetwork=global_network.to_dict()))

    def create_core_network(self):
        params = json.loads(self.body)
        global_network_id = params.get("GlobalNetworkId")
        description = params.get("Description")
        tags = params.get("Tags")
        policy_document = params.get("PolicyDocument")
        client_token = params.get("ClientToken")
        core_network = self.networkmanager_backend.create_core_network(
            global_network_id=global_network_id,
            description=description,
            tags=tags,
            policy_document=policy_document,
            client_token=client_token,
        )
        return json.dumps(dict(CoreNetwork=core_network.to_dict()))


# add templates from here
