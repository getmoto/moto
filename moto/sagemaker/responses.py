from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from .models import sagemaker_backends


class SageMakerResponse(BaseResponse):
    @property
    def sagemaker_backend(self):
        return sagemaker_backends[self.region]

