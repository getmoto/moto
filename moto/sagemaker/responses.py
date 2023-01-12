import json

from moto.sagemaker.exceptions import AWSValidationException

from moto.core.responses import BaseResponse
from moto.utilities.aws_headers import amzn_request_id
from .models import sagemaker_backends


def format_enum_error(value, attribute, allowed):
    return f"Value '{value}' at '{attribute}' failed to satisfy constraint: Member must satisfy enum value set: {allowed}"


class SageMakerResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="sagemaker")

    @property
    def sagemaker_backend(self):
        return sagemaker_backends[self.current_account][self.region]

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

    def _get_param(self, param_name, if_none=None):
        return self.request_params.get(param_name, if_none)

    @amzn_request_id
    def create_notebook_instance(self):
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
            additional_code_repositories=self._get_param("AdditionalCodeRepositories"),
            root_access=self._get_param("RootAccess"),
        )
        response = {
            "NotebookInstanceArn": sagemaker_notebook.arn,
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_notebook_instance(self):
        notebook_instance_name = self._get_param("NotebookInstanceName")
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
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        paged_results, next_token = self.sagemaker_backend.list_tags(
            arn=arn, MaxResults=max_results, NextToken=next_token
        )
        response = {"Tags": paged_results}
        if next_token:
            response["NextToken"] = next_token
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def add_tags(self):
        arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        tags = self.sagemaker_backend.add_tags(arn, tags)
        response = {"Tags": tags}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def delete_tags(self):
        arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.sagemaker_backend.delete_tags(arn, tag_keys)
        return 200, {}, json.dumps({})

    @amzn_request_id
    def create_endpoint_config(self):
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
        endpoint = self.sagemaker_backend.create_endpoint(
            endpoint_name=self._get_param("EndpointName"),
            endpoint_config_name=self._get_param("EndpointConfigName"),
            tags=self._get_param("Tags"),
        )
        response = {
            "EndpointArn": endpoint.endpoint_arn,
        }
        return 200, {}, json.dumps(response)

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
    def create_processing_job(self):
        processing_job = self.sagemaker_backend.create_processing_job(
            app_specification=self._get_param("AppSpecification"),
            experiment_config=self._get_param("ExperimentConfig"),
            network_config=self._get_param("NetworkConfig"),
            processing_inputs=self._get_param("ProcessingInputs"),
            processing_job_name=self._get_param("ProcessingJobName"),
            processing_output_config=self._get_param("ProcessingOutputConfig"),
            role_arn=self._get_param("RoleArn"),
            stopping_condition=self._get_param("StoppingCondition"),
            tags=self._get_param("Tags"),
        )
        response = {
            "ProcessingJobArn": processing_job.processing_job_arn,
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_processing_job(self):
        processing_job_name = self._get_param("ProcessingJobName")
        response = self.sagemaker_backend.describe_processing_job(processing_job_name)
        return json.dumps(response)

    @amzn_request_id
    def create_training_job(self):
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
            enable_network_isolation=self._get_param("EnableNetworkIsolation", False),
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

    @amzn_request_id
    def describe_training_job(self):
        training_job_name = self._get_param("TrainingJobName")
        response = self.sagemaker_backend.describe_training_job(training_job_name)
        return json.dumps(response)

    @amzn_request_id
    def create_notebook_instance_lifecycle_config(self):
        lifecycle_configuration = (
            self.sagemaker_backend.create_notebook_instance_lifecycle_config(
                notebook_instance_lifecycle_config_name=self._get_param(
                    "NotebookInstanceLifecycleConfigName"
                ),
                on_create=self._get_param("OnCreate"),
                on_start=self._get_param("OnStart"),
            )
        )
        response = {
            "NotebookInstanceLifecycleConfigArn": lifecycle_configuration.notebook_instance_lifecycle_config_arn,
        }
        return 200, {}, json.dumps(response)

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
    def search(self):
        response = self.sagemaker_backend.search(
            resource=self._get_param("Resource"),
            search_expression=self._get_param("SearchExpression"),
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_experiments(self):
        MaxResults = self._get_param("MaxResults")
        NextToken = self._get_param("NextToken")

        paged_results, next_token = self.sagemaker_backend.list_experiments(
            MaxResults=MaxResults, NextToken=NextToken
        )

        experiment_summaries = [
            {
                "ExperimentName": experiment_data.experiment_name,
                "ExperimentArn": experiment_data.experiment_arn,
                "CreationTime": experiment_data.creation_time,
                "LastModifiedTime": experiment_data.last_modified_time,
            }
            for experiment_data in paged_results
        ]

        response = {
            "ExperimentSummaries": experiment_summaries,
        }

        if next_token:
            response["NextToken"] = next_token

        return 200, {}, json.dumps(response)

    @amzn_request_id
    def delete_experiment(self):
        self.sagemaker_backend.delete_experiment(
            experiment_name=self._get_param("ExperimentName")
        )
        return 200, {}, json.dumps({})

    @amzn_request_id
    def create_experiment(self):
        response = self.sagemaker_backend.create_experiment(
            experiment_name=self._get_param("ExperimentName")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_experiment(self):
        response = self.sagemaker_backend.describe_experiment(
            experiment_name=self._get_param("ExperimentName")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_trials(self):
        MaxResults = self._get_param("MaxResults")
        NextToken = self._get_param("NextToken")

        paged_results, next_token = self.sagemaker_backend.list_trials(
            NextToken=NextToken,
            MaxResults=MaxResults,
            experiment_name=self._get_param("ExperimentName"),
            trial_component_name=self._get_param("TrialComponentName"),
        )

        trial_summaries = [
            {
                "TrialName": trial_data.trial_name,
                "TrialArn": trial_data.trial_arn,
                "CreationTime": trial_data.creation_time,
                "LastModifiedTime": trial_data.last_modified_time,
            }
            for trial_data in paged_results
        ]

        response = {
            "TrialSummaries": trial_summaries,
        }

        if next_token:
            response["NextToken"] = next_token

        return 200, {}, json.dumps(response)

    @amzn_request_id
    def create_trial(self):
        response = self.sagemaker_backend.create_trial(
            trial_name=self._get_param("TrialName"),
            experiment_name=self._get_param("ExperimentName"),
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_trial_components(self):
        MaxResults = self._get_param("MaxResults")
        NextToken = self._get_param("NextToken")

        paged_results, next_token = self.sagemaker_backend.list_trial_components(
            NextToken=NextToken,
            MaxResults=MaxResults,
            trial_name=self._get_param("TrialName"),
        )

        trial_component_summaries = [
            {
                "TrialComponentName": trial_component_data.trial_component_name,
                "TrialComponentArn": trial_component_data.trial_component_arn,
                "CreationTime": trial_component_data.creation_time,
                "LastModifiedTime": trial_component_data.last_modified_time,
            }
            for trial_component_data in paged_results
        ]

        response = {
            "TrialComponentSummaries": trial_component_summaries,
        }

        if next_token:
            response["NextToken"] = next_token

        return 200, {}, json.dumps(response)

    @amzn_request_id
    def create_trial_component(self):
        response = self.sagemaker_backend.create_trial_component(
            trial_component_name=self._get_param("TrialComponentName"),
            trial_name=self._get_param("TrialName"),
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_trial(self):
        trial_name = self._get_param("TrialName")
        response = self.sagemaker_backend.describe_trial(trial_name)
        return json.dumps(response)

    @amzn_request_id
    def delete_trial(self):
        trial_name = self._get_param("TrialName")
        self.sagemaker_backend.delete_trial(trial_name)
        return 200, {}, json.dumps({})

    @amzn_request_id
    def delete_trial_component(self):
        trial_component_name = self._get_param("TrialComponentName")
        self.sagemaker_backend.delete_trial_component(trial_component_name)
        return 200, {}, json.dumps({})

    @amzn_request_id
    def describe_trial_component(self):
        trial_component_name = self._get_param("TrialComponentName")
        response = self.sagemaker_backend.describe_trial_component(trial_component_name)
        return json.dumps(response)

    @amzn_request_id
    def associate_trial_component(self):
        response = self.sagemaker_backend.associate_trial_component(self.request_params)
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def disassociate_trial_component(self):
        response = self.sagemaker_backend.disassociate_trial_component(
            self.request_params
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_associations(self, *args, **kwargs):  # pylint: disable=unused-argument
        response = self.sagemaker_backend.list_associations(self.request_params)
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_pipeline(self):
        response = self.sagemaker_backend.describe_pipeline(
            self._get_param("PipelineName")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def start_pipeline_execution(self):
        response = self.sagemaker_backend.start_pipeline_execution(
            self._get_param("PipelineName"),
            self._get_param("PipelineExecutionDisplayName"),
            self._get_param("PipelineParameters"),
            self._get_param("PipelineExecutionDescription"),
            self._get_param("ParallelismConfiguration"),
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_pipeline_execution(self):
        response = self.sagemaker_backend.describe_pipeline_execution(
            self._get_param("PipelineExecutionArn")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_pipeline_definition_for_execution(self):
        response = self.sagemaker_backend.describe_pipeline_definition_for_execution(
            self._get_param("PipelineExecutionArn")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_pipeline_parameters_for_execution(self):
        response = self.sagemaker_backend.list_pipeline_parameters_for_execution(
            self._get_param("PipelineExecutionArn")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_pipeline_executions(self):
        response = self.sagemaker_backend.list_pipeline_executions(
            self._get_param("PipelineName")
        )
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def create_pipeline(self):
        pipeline = self.sagemaker_backend.create_pipeline(
            pipeline_name=self._get_param("PipelineName"),
            pipeline_display_name=self._get_param("PipelineDisplayName"),
            pipeline_definition=self._get_param("PipelineDefinition"),
            pipeline_definition_s3_location=self._get_param(
                "PipelineDefinitionS3Location"
            ),
            pipeline_description=self._get_param("PipelineDescription"),
            role_arn=self._get_param("RoleArn"),
            tags=self._get_param("Tags"),
            parallelism_configuration=self._get_param("ParallelismConfiguration"),
        )
        response = {
            "PipelineArn": pipeline.pipeline_arn,
        }

        return 200, {}, json.dumps(response)

    @amzn_request_id
    def delete_pipeline(self):
        pipeline_arn = self.sagemaker_backend.delete_pipeline(
            pipeline_name=self._get_param("PipelineName"),
        )
        response = {"PipelineArn": pipeline_arn}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def update_pipeline(self):
        pipeline_arn = self.sagemaker_backend.update_pipeline(
            pipeline_name=self._get_param("PipelineName"),
            pipeline_display_name=self._get_param("PipelineDisplayName"),
            pipeline_definition=self._get_param("PipelineDefinition"),
            pipeline_definition_s3_location=self._get_param(
                "PipelineDefinitionS3Location"
            ),
            pipeline_description=self._get_param("PipelineDescription"),
            role_arn=self._get_param("RoleArn"),
            parallelism_configuration=self._get_param("ParallelismConfiguration"),
        )

        response = {"PipelineArn": pipeline_arn}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_pipelines(self):
        max_results_range = range(1, 101)
        allowed_sort_by = ("Name", "CreationTime")
        allowed_sort_order = ("Ascending", "Descending")

        pipeline_name_prefix = self._get_param("PipelineNamePrefix")
        created_after = self._get_param("CreatedAfter")
        created_before = self._get_param("CreatedBefore")
        sort_by = self._get_param("SortBy", "CreationTime")
        sort_order = self._get_param("SortOrder", "Descending")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")

        errors = []
        if max_results and max_results not in max_results_range:
            errors.append(
                f"Value '{max_results}' at 'maxResults' failed to satisfy constraint: Member must have value less than or equal to {max_results_range[-1]}"
            )

        if sort_by not in allowed_sort_by:
            errors.append(format_enum_error(sort_by, "SortBy", allowed_sort_by))
        if sort_order not in allowed_sort_order:
            errors.append(
                format_enum_error(sort_order, "SortOrder", allowed_sort_order)
            )
        if errors:
            raise AWSValidationException(
                f"{len(errors)} validation errors detected: {';'.join(errors)}"
            )

        response = self.sagemaker_backend.list_pipelines(
            pipeline_name_prefix=pipeline_name_prefix,
            created_after=created_after,
            created_before=created_before,
            next_token=next_token,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_processing_jobs(self):
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

        max_results = self._get_int_param("MaxResults")
        sort_by = self._get_param("SortBy", "CreationTime")
        sort_order = self._get_param("SortOrder", "Ascending")
        status_equals = self._get_param("StatusEquals")
        next_token = self._get_param("NextToken")
        errors = []
        if max_results and max_results not in max_results_range:
            errors.append(
                f"Value '{max_results}' at 'maxResults' failed to satisfy constraint: Member must have value less than or equal to {max_results_range[-1]}"
            )

        if sort_by not in allowed_sort_by:
            errors.append(format_enum_error(sort_by, "sortBy", allowed_sort_by))
        if sort_order not in allowed_sort_order:
            errors.append(
                format_enum_error(sort_order, "sortOrder", allowed_sort_order)
            )

        if status_equals and status_equals not in allowed_status_equals:
            errors.append(
                format_enum_error(status_equals, "statusEquals", allowed_status_equals)
            )

        if errors != []:
            raise AWSValidationException(
                f"{len(errors)} validation errors detected: {';'.join(errors)}"
            )

        response = self.sagemaker_backend.list_processing_jobs(
            next_token=next_token,
            max_results=max_results,
            creation_time_after=self._get_param("CreationTimeAfter"),
            creation_time_before=self._get_param("CreationTimeBefore"),
            last_modified_time_after=self._get_param("LastModifiedTimeAfter"),
            last_modified_time_before=self._get_param("LastModifiedTimeBefore"),
            name_contains=self._get_param("NameContains"),
            status_equals=status_equals,
        )
        return 200, {}, json.dumps(response)

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

        max_results = self._get_int_param("MaxResults")
        sort_by = self._get_param("SortBy", "CreationTime")
        sort_order = self._get_param("SortOrder", "Ascending")
        status_equals = self._get_param("StatusEquals")
        next_token = self._get_param("NextToken")
        errors = []
        if max_results and max_results not in max_results_range:
            errors.append(
                f"Value '{max_results}' at 'maxResults' failed to satisfy constraint: Member must have value less than or equal to {max_results_range[-1]}"
            )

        if sort_by not in allowed_sort_by:
            errors.append(format_enum_error(sort_by, "sortBy", allowed_sort_by))
        if sort_order not in allowed_sort_order:
            errors.append(
                format_enum_error(sort_order, "sortOrder", allowed_sort_order)
            )

        if status_equals and status_equals not in allowed_status_equals:
            errors.append(
                format_enum_error(status_equals, "statusEquals", allowed_status_equals)
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
        )
        return 200, {}, json.dumps(response)

    def update_endpoint_weights_and_capacities(self):
        endpoint_name = self._get_param("EndpointName")
        desired_weights_and_capacities = self._get_param("DesiredWeightsAndCapacities")
        endpoint_arn = self.sagemaker_backend.update_endpoint_weights_and_capacities(
            endpoint_name=endpoint_name,
            desired_weights_and_capacities=desired_weights_and_capacities,
        )
        response = {"EndpointArn": endpoint_arn}
        return 200, {}, json.dumps(response)
