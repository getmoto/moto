"""Handles incoming cloudhsmv2 requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import cloudhsmv2_backends


class CloudHSMV2Response(BaseResponse):
    """Handler for CloudHSMV2 requests and responses."""

    def __init__(self):
        super().__init__(service_name="cloudhsmv2")

    @property
    def cloudhsmv2_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # cloudhsmv2_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return cloudhsmv2_backends[self.current_account][self.region]

    # add methods from here

    def list_tags(self):
        params = self._get_params()
        resource_id = params.get("ResourceId")
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")
        tag_list, next_token = self.cloudhsmv2_backend.list_tags(
            resource_id=resource_id,
            next_token=next_token,
            max_results=max_results,
        )
        # TODO: adjust response
        return json.dumps(dict(tagList=tag_list, nextToken=next_token))


# add templates from here
