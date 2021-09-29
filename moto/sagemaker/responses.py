from __future__ import unicode_literals

import json
from moto.sagemaker.exceptions import AWSValidationException

from moto.core.exceptions import AWSError
from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from .models import sagemaker_backends


def format_enum_error(value, attribute, allowed):
    return f"Value '{value}' at '{attribute}' failed to satisfy constraint: Member must satisfy enum value set: {allowed}"


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
        model = self.sagemaker_backend.describe_model(model_name)
        return json.dumps(model.response_object)

    def create_model(self):
        model = self.sagemaker_backend.create_model(**self.request_params)
        return json.dumps(model.response_create)

    def delete_model(self):
        model_name = self._get_param("ModelName")
        response = self.sagemaker_backend.delete_model(model_name)
        return json.dumps(response)

    def list_models(self):
        models = self.sagemaker_backend.list_models(**self.request_params)
        return json.dumps({"Models": [model.response_object for model in models]})

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

    @amzn_request_id
    def create_notebook_instance_lifecycle_config(self):
        try:
            lifecycle_configuration = self.sagemaker_backend.create_notebook_instance_lifecycle_config(
                notebook_instance_lifecycle_config_name=self._get_param(
                    "NotebookInstanceLifecycleConfigName"
                ),
                on_create=self._get_param("OnCreate"),
                on_start=self._get_param("OnStart"),
            )
            response = {
                "NotebookInstanceLifecycleConfigArn": lifecycle_configuration.notebook_instance_lifecycle_config_arn,
            }
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()

    @amzn_request_id
    def describe_notebook_instance_lifecycle_config(self):
        response = self.sagemaker_backend.describe_notebook_instance_lifecycle_config(
            notebook_instance_lifecycle_config_name=self._get_param(
                "NotebookInstanceLifecycleConfigName"
            )
        )
        return json.dumps(response)

    @amzn_request_id
    def delete_notebook_instance_lifecycle_config(self):
        self.sagemaker_backend.delete_notebook_instance_lifecycle_config(
            notebook_instance_lifecycle_config_name=self._get_param(
                "NotebookInstanceLifecycleConfigName"
            )
        )
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def list_training_jobs(self):
        max_results_range = range(1, 101)
        allowed_sort_by = ["Name", "CreationTime", "Status"]
        allowed_sort_order = ["Ascending", "Descending"]
        allowed_status_equals = [
            "Completed",
            "Stopped",
            "InProgress",
            "Stopping",
            "Failed",
        ]

        try:
            max_results = self._get_int_param("MaxResults")
            sort_by = self._get_param("SortBy", "CreationTime")
            sort_order = self._get_param("SortOrder", "Ascending")
            status_equals = self._get_param("StatusEquals")
            next_token = self._get_param("NextToken")
            errors = []
            if max_results and max_results not in max_results_range:
                errors.append(
                    "Value '{0}' at 'maxResults' failed to satisfy constraint: Member must have value less than or equal to {1}".format(
                        max_results, max_results_range[-1]
                    )
                )

            if sort_by not in allowed_sort_by:
                errors.append(format_enum_error(sort_by, "sortBy", allowed_sort_by))
            if sort_order not in allowed_sort_order:
                errors.append(
                    format_enum_error(sort_order, "sortOrder", allowed_sort_order)
                )

            if status_equals and status_equals not in allowed_status_equals:
                errors.append(
                    format_enum_error(
                        status_equals, "statusEquals", allowed_status_equals
                    )
                )

            if errors != []:
                raise AWSValidationException(
                    f"{len(errors)} validation errors detected: {';'.join(errors)}"
                )

            response = self.sagemaker_backend.list_training_jobs(
                next_token=next_token,
                max_results=max_results,
                creation_time_after=self._get_param("CreationTimeAfter"),
                creation_time_before=self._get_param("CreationTimeBefore"),
                last_modified_time_after=self._get_param("LastModifiedTimeAfter"),
                last_modified_time_before=self._get_param("LastModifiedTimeBefore"),
                name_contains=self._get_param("NameContains"),
                status_equals=status_equals,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            return 200, {}, json.dumps(response)
        except AWSError as err:
            return err.response()
