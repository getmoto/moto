from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import kms_backends


class KmsResponse(BaseResponse):

    @property
    def parameters(self):
        return json.loads(self.body.decode("utf-8"))

    @property
    def kms_backend(self):
        return kms_backends[self.region]

    def create_key(self):
        policy = self.parameters.get('Policy')
        key_usage = self.parameters.get('KeyUsage')
        description = self.parameters.get('Description')

        key = self.kms_backend.create_key(policy, key_usage, description, self.region)
        return json.dumps(key.to_dict())

    def describe_key(self):
        key_id = self.parameters.get('KeyId')
        try:
            key = self.kms_backend.describe_key(key_id)
        except KeyError:
            self.headers['status'] = 404
            return "{}", self.headers
        return json.dumps(key.to_dict())

    def list_keys(self):
        keys = self.kms_backend.list_keys()

        return json.dumps({
            "Keys": [
                {
                    "KeyArn": key.arn,
                    "KeyId": key.id,
                } for key in keys
            ],
            "NextMarker": None,
            "Truncated": False,
        })
