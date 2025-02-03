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
        return cloudhsmv2_backends[self.current_account][self.region]

    def list_tags(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        resource_id = params.get("ResourceId")
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")

        tag_list, next_token = self.cloudhsmv2_backend.list_tags(
            resource_id=resource_id,
            next_token=next_token,
            max_results=max_results,
        )

        return 200, {}, json.dumps({"TagList": tag_list, "NextToken": next_token})

    def tag_resource(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        resource_id = params.get("ResourceId")
        tag_list = params.get("TagList")

        self.cloudhsmv2_backend.tag_resource(
            resource_id=resource_id,
            tag_list=tag_list,
        )
        return json.dumps(dict())

    def untag_resource(self):
        raw_params = list(self._get_params().keys())[0]
        params = json.loads(raw_params)

        resource_id = params.get("ResourceId")
        tag_key_list = params.get("TagKeyList")
        self.cloudhsmv2_backend.untag_resource(
            resource_id=resource_id,
            tag_key_list=tag_key_list,
        )
        return json.dumps(dict())
