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
        try:
            sagemaker_notebook = self.sagemaker_backend.create_notebook_instance(
                notebook_instance_name=self._get_param("NotebookInstanceName"),
                instance_type=self._get_param("InstanceType"),
                subnet_id=self._get_param("SubnetId"),
                security_group_ids=self._get_param("SecurityGroupIds"),
                role_arn=self._get_param("RoleArn"),
                kms_key_id=self._get_param("KmsKeyId"),
                tags=self._get_param("Tags"),
                lifecycle_config_name=self._get_param("LifecycleConfigName"),
                direct_internet_access=self._get_param("DirectInternetAccess"),
                volume_size_in_gb=self._get_param("VolumeSizeInGB"),
                accelerator_types=self._get_param("AcceleratorTypes"),
                default_code_repository=self._get_param("DefaultCodeRepository"),
                additional_code_repositories=self._get_param(
                    "AdditionalCodeRepositories"
                ),
                root_access=self._get_param("RootAccess"),
            )
            response = {
                "NotebookInstanceArn": sagemaker_notebook.arn,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()

    @amzn_request_id
    def describe_notebook_instance(self):
        notebook_instance_name = self._get_param("NotebookInstanceName")
        try:
            notebook_instance = self.sagemaker_backend.get_notebook_instance(
                notebook_instance_name
            )
            response = {
                "NotebookInstanceArn": notebook_instance.arn,
                "NotebookInstanceName": notebook_instance.notebook_instance_name,
                "NotebookInstanceStatus": notebook_instance.status,
                "Url": notebook_instance.url,
                "InstanceType": notebook_instance.instance_type,
                "SubnetId": notebook_instance.subnet_id,
                "SecurityGroups": notebook_instance.security_group_ids,
                "RoleArn": notebook_instance.role_arn,
                "KmsKeyId": notebook_instance.kms_key_id,
                # ToDo: NetworkInterfaceId
                "LastModifiedTime": str(notebook_instance.last_modified_time),
                "CreationTime": str(notebook_instance.creation_time),
                "NotebookInstanceLifecycleConfigName": notebook_instance.lifecycle_config_name,
                "DirectInternetAccess": notebook_instance.direct_internet_access,
                "VolumeSizeInGB": notebook_instance.volume_size_in_gb,
                "AcceleratorTypes": notebook_instance.accelerator_types,
                "DefaultCodeRepository": notebook_instance.default_code_repository,
                "AdditionalCodeRepositories": notebook_instance.additional_code_repositories,
                "RootAccess": notebook_instance.root_access,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()

    @amzn_request_id
    def start_notebook_instance(self):
        notebook_instance_name = self._get_param("NotebookInstanceName")
        notebook_instance = self.sagemaker_backend.get_notebook_instance(
            notebook_instance_name
        )
        notebook_instance.start()
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def stop_notebook_instance(self):
        notebook_instance_name = self._get_param("NotebookInstanceName")
        notebook_instance = self.sagemaker_backend.get_notebook_instance(
            notebook_instance_name
        )
        notebook_instance.stop()
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def delete_notebook_instance(self):
        notebook_instance_name = self._get_param("NotebookInstanceName")
        self.sagemaker_backend.delete_notebook_instance(notebook_instance_name)
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def list_tags(self):
        arn = self._get_param("ResourceArn")
        try:
            notebook_instance = self.sagemaker_backend.get_notebook_instance_by_arn(arn)
            tags = notebook_instance.tags or []
        except AWSError:
            tags = []
        response = {"Tags": tags}
        return 200, {}, json.dumps(response)
