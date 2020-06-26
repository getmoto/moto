from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from .exceptions import AWSError
from .models import sagemaker_backends


class SageMakerResponse(BaseResponse):
    @property
    def sagemaker_backend(self):
        return sagemaker_backends[self.region]

    @amzn_request_id
    def create_notebook_instance(self):
        name = self._get_param("NotebookInstanceName")
        instance_type = self._get_param("InstanceType")
        role_arn = self._get_param("RoleArn")
        tags = self._get_param("Tags")
        try:
            sagemaker_notebook = self.sagemaker_backend.create_notebook_instance(
                name,
                instance_type,
                role_arn,
            )
            response = {
                "NotebookInstanceArn": sagemaker_notebook.arn,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()