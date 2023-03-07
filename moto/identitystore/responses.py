"""Handles incoming identitystore requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import identitystore_backends


class IdentityStoreResponse(BaseResponse):
    """Handler for IdentityStore requests and responses."""

    def __init__(self):
        super().__init__(service_name="identitystore")

    @property
    def identitystore_backend(self):
        """Return backend instance specific for this region."""
        return identitystore_backends[self.current_account][self.region]

    # add methods from here

    def create_group(self):
        params = self._get_params()
        identity_store_id = params.get("IdentityStoreId")
        display_name = params.get("DisplayName")
        description = params.get("Description")
        group_id, identity_store_id = self.identitystore_backend.create_group(
            identity_store_id=identity_store_id,
            display_name=display_name,
            description=description,
        )
        return json.dumps(dict(GroupId=group_id, IdentityStoreId=identity_store_id))

    def _get_params(self):
        return json.loads(self.body)
