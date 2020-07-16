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

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def describe_model(self):
        model_name = self._get_param("ModelName")
        response = self.sagemaker_backend.describe_model(model_name)
        return json.dumps(response)

    def create_model(self):
        response = self.sagemaker_backend.create_model(**self.request_params)
        return json.dumps(response)

    def delete_model(self):
        model_name = self._get_param("ModelName")
        response = self.sagemaker_backend.delete_model(model_name)
        return json.dumps(response)

    def list_models(self):
        response = self.sagemaker_backend.list_models(**self.request_params)
        return json.dumps(response)

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

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
        self.sagemaker_backend.start_notebook_instance(notebook_instance_name)
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def stop_notebook_instance(self):
        notebook_instance_name = self._get_param("NotebookInstanceName")
        self.sagemaker_backend.stop_notebook_instance(notebook_instance_name)
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
            if ":notebook-instance/" in arn:
                tags = self.sagemaker_backend.get_notebook_instance_tags(arn)
            elif ":endpoint/" in arn:
                tags = self.sagemaker_backend.get_endpoint_tags(arn)
            elif ":training-job/" in arn:
                tags = self.sagemaker_backend.get_training_job_tags(arn)
            else:
                tags = []
        except AWSError:
            tags = []
        response = {"Tags": tags}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def create_endpoint_config(self):
        try:
            endpoint_config = self.sagemaker_backend.create_endpoint_config(
                endpoint_config_name=self._get_param("EndpointConfigName"),
                production_variants=self._get_param("ProductionVariants"),
                data_capture_config=self._get_param("DataCaptureConfig"),
                tags=self._get_param("Tags"),
                kms_key_id=self._get_param("KmsKeyId"),
            )
            response = {
                "EndpointConfigArn": endpoint_config.endpoint_config_arn,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()

    @amzn_request_id
    def describe_endpoint_config(self):
        endpoint_config_name = self._get_param("EndpointConfigName")
        response = self.sagemaker_backend.describe_endpoint_config(endpoint_config_name)
        return json.dumps(response)

    @amzn_request_id
    def delete_endpoint_config(self):
        endpoint_config_name = self._get_param("EndpointConfigName")
        self.sagemaker_backend.delete_endpoint_config(endpoint_config_name)
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def create_endpoint(self):
        try:
            endpoint = self.sagemaker_backend.create_endpoint(
                endpoint_name=self._get_param("EndpointName"),
                endpoint_config_name=self._get_param("EndpointConfigName"),
                tags=self._get_param("Tags"),
            )
            response = {
                "EndpointArn": endpoint.endpoint_arn,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()

    @amzn_request_id
    def describe_endpoint(self):
        endpoint_name = self._get_param("EndpointName")
        response = self.sagemaker_backend.describe_endpoint(endpoint_name)
        return json.dumps(response)

    @amzn_request_id
    def delete_endpoint(self):
        endpoint_name = self._get_param("EndpointName")
        self.sagemaker_backend.delete_endpoint(endpoint_name)
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def create_training_job(self):
        try:
            training_job = self.sagemaker_backend.create_training_job(
                training_job_name=self._get_param("TrainingJobName"),
                hyper_parameters=self._get_param("HyperParameters"),
                algorithm_specification=self._get_param("AlgorithmSpecification"),
                role_arn=self._get_param("RoleArn"),
                input_data_config=self._get_param("InputDataConfig"),
                output_data_config=self._get_param("OutputDataConfig"),
                resource_config=self._get_param("ResourceConfig"),
                vpc_config=self._get_param("VpcConfig"),
                stopping_condition=self._get_param("StoppingCondition"),
                tags=self._get_param("Tags"),
                enable_network_isolation=self._get_param(
                    "EnableNetworkIsolation", False
                ),
                enable_inter_container_traffic_encryption=self._get_param(
                    "EnableInterContainerTrafficEncryption", False
                ),
                enable_managed_spot_training=self._get_param(
                    "EnableManagedSpotTraining", False
                ),
                checkpoint_config=self._get_param("CheckpointConfig"),
                debug_hook_config=self._get_param("DebugHookConfig"),
                debug_rule_configurations=self._get_param("DebugRuleConfigurations"),
                tensor_board_output_config=self._get_param("TensorBoardOutputConfig"),
                experiment_config=self._get_param("ExperimentConfig"),
            )
            response = {
                "TrainingJobArn": training_job.training_job_arn,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()

    @amzn_request_id
    def describe_training_job(self):
        training_job_name = self._get_param("TrainingJobName")
        response = self.sagemaker_backend.describe_training_job(training_job_name)
        return json.dumps(response)

    @amzn_request_id
    def delete_training_job(self):
        training_job_name = self._get_param("TrainingJobName")
        self.sagemaker_backend.delete_training_job(training_job_name)
        return 200, {}, json.dumps("{}")
