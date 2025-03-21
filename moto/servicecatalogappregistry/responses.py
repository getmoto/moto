"""Handles incoming servicecatalogappregistry requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import AppRegistryBackend, servicecatalogappregistry_backends


class AppRegistryResponse(BaseResponse):
    """Handler for AppRegistry requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="servicecatalog-appregistry")

    @property
    def servicecatalogappregistry_backend(self) -> AppRegistryBackend:
        """Return backend instance specific for this region."""
        # TODO
        # servicecatalogappregistry_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return servicecatalogappregistry_backends[self.current_account][self.region]

    # add methods from here

    def create_application(self) -> str:
        name = self._get_param("name")
        description = self._get_param("description")
        tags = self._get_param("tags")
        client_token = self._get_param("clientToken")
        application = self.servicecatalogappregistry_backend.create_application(
            name=name,
            description=description,
            tags=tags,
            client_token=client_token,
        )
        return json.dumps({"application": application.to_json()})

    def list_applications(self) -> str:
        applications = self.servicecatalogappregistry_backend.list_applications()
        json_list = []
        for app in applications:
            json_list.append(app.to_json())
        return json.dumps({"applications": json_list})


# add templates from here
