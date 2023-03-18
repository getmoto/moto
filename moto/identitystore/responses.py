"""Handles incoming identitystore requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import identitystore_backends, IdentityStoreBackend


class IdentityStoreResponse(BaseResponse):
    """Handler for IdentityStore requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="identitystore")

    @property
    def identitystore_backend(self) -> IdentityStoreBackend:
        """Return backend instance specific for this region."""
        return identitystore_backends[self.current_account][self.region]

    def create_group(self) -> str:
        identity_store_id = self._get_param("IdentityStoreId")
        display_name = self._get_param("DisplayName")
        description = self._get_param("Description")
        group_id, identity_store_id = self.identitystore_backend.create_group(
            identity_store_id=identity_store_id,
            display_name=display_name,
            description=description,
        )
        return json.dumps(dict(GroupId=group_id, IdentityStoreId=identity_store_id))
