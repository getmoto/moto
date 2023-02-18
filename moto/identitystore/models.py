"""IdentityStoreBackend class with methods for supported APIs."""
from moto.moto_api._internal import mock_random

from moto.core import BaseBackend, BackendDict


class IdentityStoreBackend(BaseBackend):
    """Implementation of IdentityStore APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.groups = {}

    # add methods from here

    def create_group(self, identity_store_id, display_name, description):
        group_id = str(mock_random.uuid4())
        group_dict = {
            "GroupId": group_id,
            "IdentityStoreId": identity_store_id,
            "DisplayName": display_name,
            "Description": description,
        }
        self.groups[group_id] = group_dict
        return group_id, identity_store_id


identitystore_backends = BackendDict(IdentityStoreBackend, "identitystore")
