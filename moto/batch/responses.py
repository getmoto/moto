from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import batch_backends
from six.moves.urllib.parse import urlsplit

from .exceptions import AWSError

import json


class BatchResponse(BaseResponse):
    def _error(self, code, message):
        return json.dumps({'__type': code, 'message': message}), dict(status=400)

    @property
    def batch_backend(self):
        return batch_backends[self.region]

    @property
    def json(self):
        if not hasattr(self, '_json'):
            self._json = json.loads(self.body)
        return self._json

    def _get_param(self, param_name, if_none=None):
        val = self.json.get(param_name)
        if val is not None:
            return val
        return if_none

    def _get_action(self):
        # Return element after the /v1/*
        return urlsplit(self.uri).path.lstrip('/').split('/')[1]

    # CreateComputeEnvironment
    def createcomputeenvironment(self):
        compute_env_name = self._get_param('computeEnvironmentName')
        compute_resource = self._get_param('computeResources')
        service_role = self._get_param('serviceRole')
        state = self._get_param('state')
        _type = self._get_param('type')

        try:
            name, arn = self.batch_backend.create_compute_environment(
                compute_environment_name=compute_env_name,
                _type=_type, state=state,
                compute_resources=compute_resource,
                service_role=service_role
            )
        except AWSError as err:
            return err.response()

        result = {
            'computeEnvironmentArn': arn,
            'computeEnvironmentName': name
        }

        return json.dumps(result)
