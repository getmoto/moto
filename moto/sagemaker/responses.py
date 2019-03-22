from __future__ import unicode_literals
import json
from base64 import b64encode
from datetime import datetime
import time

from moto.core.responses import BaseResponse
from .models import sagemaker_backends


class SageMakerResponse(BaseResponse):
    @property
    def sagemaker_backend(self):
        return sagemaker_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def describe_model(self):
        model_name = self._get_param('ModelName')
        response = self.sagemaker_backend.describe_model(model_name)
        return json.dumps(response)

    def create_model(self):
        response = self.sagemaker_backend.create_model(self.request_params)
        return json.dumps(response)

    def _get_param(self, param):
        return self.request_params.get(param, None)