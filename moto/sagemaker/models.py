import json
import os
import random
import string
from datetime import datetime

from moto.core import BaseBackend, BackendDict, BaseModel, CloudFormationModel
from moto.sagemaker import validators
from moto.utilities.paginator import paginate
from .exceptions import (
    MissingModel,
    ValidationError,
    AWSValidationException,
    ResourceNotFound,
)
from .utils import (
    get_pipeline_from_name,
    get_pipeline_execution_from_arn,
    get_pipeline_name_from_execution_arn,
)
from .utils import load_pipeline_definition_from_s3, arn_formatter


PAGINATION_MODEL = {
    "list_experiments": {
        "input_token": "NextToken",
        "limit_key": "MaxResults",
        "limit_default": 100,
        "unique_attribute": "experiment_arn",
        "fail_on_invalid_token": True,
    },
    "list_trials": {
        "input_token": "NextToken",
        "limit_key": "MaxResults",
        "limit_default": 100,
        "unique_attribute": "trial_arn",
        "fail_on_invalid_token": True,
    },
    "list_trial_components": {
        "input_token": "NextToken",
        "limit_key": "MaxResults",
        "limit_default": 100,
        "unique_attribute": "trial_component_arn",
        "fail_on_invalid_token": True,
    },
    "list_tags": {
        "input_token": "NextToken",
        "limit_key": "MaxResults",
        "limit_default": 50,
        "unique_attribute": "Key",
        "fail_on_invalid_token": True,
    },
}


class BaseObject(BaseModel):
    def camelCase(self, key):
        words = []
        for word in key.split("_"):
            words.append(word.title())
        return "".join(words)

    def update(self, details_json):
        details = json.loads(details_json)
        for k in details.keys():
            setattr(self, k, details[k])

    def gen_response_object(self):
        response_object = dict()
        for key, value in self.__dict__.items():
            if "_" in key:
                response_object[self.camelCase(key)] = value
            else:
                response_object[key[0].upper() + key[1:]] = value
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class FakePipelineExecution(BaseObject):
    def __init__(
        self,
        pipeline_execution_arn,
        pipeline_execution_display_name,
        pipeline_parameters,
        pipeline_execution_description,
        parallelism_configuration,
        pipeline_definition,
        client_request_token,
    ):
        self.pipeline_execution_arn = pipeline_execution_arn
        self.pipeline_execution_display_name = pipeline_execution_display_name
        self.pipeline_parameters = pipeline_parameters
        self.pipeline_execution_description = pipeline_execution_description
        self.pipeline_execution_status = "Succeeded"
        self.pipeline_execution_failure_reason = None
        self.parallelism_configuration = parallelism_configuration
        self.pipeline_definition_for_execution = pipeline_definition
        self.client_request_token = client_request_token

        now_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.creation_time = now_string
        self.last_modified_time = now_string
        self.start_time = now_string

        fake_user_profile_name = "fake-user-profile-name"
        fake_domain_id = "fake-domain-id"
        fake_user_profile_arn = arn_formatter(
            "user-profile",
            f"{fake_domain_id}/{fake_user_profile_name}",
            pipeline_execution_arn.split(":")[4],
            pipeline_execution_arn.split(":")[3],
        )
        self.created_by = {
            "UserProfileArn": fake_user_profile_arn,
            "UserProfileName": fake_user_profile_name,
            "DomainId": fake_domain_id,
        }
        self.last_modified_by = {
            "UserProfileArn": fake_user_profile_arn,
            "UserProfileName": fake_user_profile_name,
            "DomainId": fake_domain_id,
        }


class FakePipeline(BaseObject):
    def __init__(
        self,
        pipeline_name,
        pipeline_display_name,
        pipeline_definition,
        pipeline_description,
        role_arn,
        tags,
        account_id,
        region_name,
        parallelism_configuration,
    ):
        self.pipeline_name = pipeline_name
        self.pipeline_arn = arn_formatter(
            "pipeline", pipeline_name, account_id, region_name
        )
        self.pipeline_display_name = pipeline_display_name or pipeline_name
        self.pipeline_definition = pipeline_definition
        self.pipeline_description = pipeline_description
        self.pipeline_executions = dict()
        self.role_arn = role_arn
        self.tags = tags or []
        self.parallelism_configuration = parallelism_configuration

        now_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.creation_time = now_string
        self.last_modified_time = now_string
        self.last_execution_time = None

        self.pipeline_status = "Active"
        fake_user_profile_name = "fake-user-profile-name"
        fake_domain_id = "fake-domain-id"
        fake_user_profile_arn = arn_formatter(
            "user-profile",
            f"{fake_domain_id}/{fake_user_profile_name}",
            account_id,
            region_name,
        )
        self.created_by = {
            "UserProfileArn": fake_user_profile_arn,
            "UserProfileName": fake_user_profile_name,
            "DomainId": fake_domain_id,
        }
        self.last_modified_by = {
            "UserProfileArn": fake_user_profile_arn,
            "UserProfileName": fake_user_profile_name,
            "DomainId": fake_domain_id,
        }


class FakeProcessingJob(BaseObject):
    def __init__(
        self,
        app_specification,
        experiment_config,
        network_config,
        processing_inputs,
        processing_job_name,
        processing_output_config,
        account_id,
        region_name,
        role_arn,
        tags,
        stopping_condition,
    ):
        self.processing_job_name = processing_job_name
        self.processing_job_arn = arn_formatter(
            "processing-job", processing_job_name, account_id, region_name
        )

        now_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.creation_time = now_string
        self.last_modified_time = now_string
        self.processing_end_time = now_string
        self.tags = tags or []
        self.role_arn = role_arn
        self.app_specification = app_specification
        self.experiment_config = experiment_config
        self.network_config = network_config
        self.processing_inputs = processing_inputs
        self.processing_job_status = "Completed"
        self.processing_output_config = processing_output_config
        self.stopping_condition = stopping_condition

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"ProcessingJobArn": self.processing_job_arn}


class FakeTrainingJob(BaseObject):
    def __init__(
        self,
        account_id,
        region_name,
        training_job_name,
        hyper_parameters,
        algorithm_specification,
        role_arn,
        input_data_config,
        output_data_config,
        resource_config,
        vpc_config,
        stopping_condition,
        tags,
        enable_network_isolation,
        enable_inter_container_traffic_encryption,
        enable_managed_spot_training,
        checkpoint_config,
        debug_hook_config,
        debug_rule_configurations,
        tensor_board_output_config,
        experiment_config,
    ):
        self.training_job_name = training_job_name
        self.hyper_parameters = hyper_parameters
        self.algorithm_specification = algorithm_specification
        self.role_arn = role_arn
        self.input_data_config = input_data_config
        self.output_data_config = output_data_config
        self.resource_config = resource_config
        self.vpc_config = vpc_config
        self.stopping_condition = stopping_condition
        self.tags = tags or []
        self.enable_network_isolation = enable_network_isolation
        self.enable_inter_container_traffic_encryption = (
            enable_inter_container_traffic_encryption
        )
        self.enable_managed_spot_training = enable_managed_spot_training
        self.checkpoint_config = checkpoint_config
        self.debug_hook_config = debug_hook_config
        self.debug_rule_configurations = debug_rule_configurations
        self.tensor_board_output_config = tensor_board_output_config
        self.experiment_config = experiment_config
        self.training_job_arn = FakeTrainingJob.arn_formatter(
            training_job_name, account_id, region_name
        )
        self.creation_time = self.last_modified_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.model_artifacts = {
            "S3ModelArtifacts": os.path.join(
                self.output_data_config["S3OutputPath"],
                self.training_job_name,
                "output",
                "model.tar.gz",
            )
        }
        self.training_job_status = "Completed"
        self.secondary_status = "Completed"
        self.algorithm_specification["MetricDefinitions"] = [
            {
                "Name": "test:dcg",
                "Regex": "#quality_metric: host=\\S+, test dcg <score>=(\\S+)",
            }
        ]
        now_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.creation_time = now_string
        self.last_modified_time = now_string
        self.training_start_time = now_string
        self.training_end_time = now_string
        self.secondary_status_transitions = [
            {
                "Status": "Starting",
                "StartTime": self.creation_time,
                "EndTime": self.creation_time,
                "StatusMessage": "Preparing the instances for training",
            }
        ]
        self.final_metric_data_list = [
            {
                "MetricName": "train:progress",
                "Value": 100.0,
                "Timestamp": self.creation_time,
            }
        ]

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"TrainingJobArn": self.training_job_arn}

    @staticmethod
    def arn_formatter(name, account_id, region_name):
        return arn_formatter("training-job", name, account_id, region_name)


class FakeEndpoint(BaseObject, CloudFormationModel):
    def __init__(
        self,
        account_id,
        region_name,
        endpoint_name,
        endpoint_config_name,
        production_variants,
        data_capture_config,
        tags,
    ):
        self.endpoint_name = endpoint_name
        self.endpoint_arn = FakeEndpoint.arn_formatter(
            endpoint_name, account_id, region_name
        )
        self.endpoint_config_name = endpoint_config_name
        self.production_variants = self._process_production_variants(
            production_variants
        )
        self.data_capture_config = data_capture_config
        self.tags = tags or []
        self.endpoint_status = "InService"
        self.failure_reason = None
        self.creation_time = self.last_modified_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def _process_production_variants(self, production_variants):
        endpoint_variants = []
        for production_variant in production_variants:
            temp_variant = {}

            # VariantName is the only required param
            temp_variant["VariantName"] = production_variant["VariantName"]

            if production_variant.get("InitialInstanceCount", None):
                temp_variant["CurrentInstanceCount"] = production_variant[
                    "InitialInstanceCount"
                ]
                temp_variant["DesiredInstanceCount"] = production_variant[
                    "InitialInstanceCount"
                ]

            if production_variant.get("InitialVariantWeight", None):
                temp_variant["CurrentWeight"] = production_variant[
                    "InitialVariantWeight"
                ]
                temp_variant["DesiredWeight"] = production_variant[
                    "InitialVariantWeight"
                ]

            if production_variant.get("ServerlessConfig", None):
                temp_variant["CurrentServerlessConfig"] = production_variant[
                    "ServerlessConfig"
                ]
                temp_variant["DesiredServerlessConfig"] = production_variant[
                    "ServerlessConfig"
                ]

            endpoint_variants.append(temp_variant)

        return endpoint_variants

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"EndpointArn": self.endpoint_arn}

    @staticmethod
    def arn_formatter(endpoint_name, account_id, region_name):
        return arn_formatter("endpoint", endpoint_name, account_id, region_name)

    @property
    def physical_resource_id(self):
        return self.endpoint_arn

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["EndpointName"]

    def get_cfn_attribute(self, attribute_name):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpoint.html#aws-resource-sagemaker-endpoint-return-values
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "EndpointName":
            return self.endpoint_name
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpoint.html
        return "AWS::SageMaker::Endpoint"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        sagemaker_backend = sagemaker_backends[account_id][region_name]

        # Get required properties from provided CloudFormation template
        properties = cloudformation_json["Properties"]
        endpoint_config_name = properties["EndpointConfigName"]

        endpoint = sagemaker_backend.create_endpoint(
            endpoint_name=resource_name,
            endpoint_config_name=endpoint_config_name,
            tags=properties.get("Tags", []),
        )
        return endpoint

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        # Changes to the Endpoint will not change resource name
        cls.delete_from_cloudformation_json(
            original_resource.endpoint_arn, cloudformation_json, account_id, region_name
        )
        new_resource = cls.create_from_cloudformation_json(
            original_resource.endpoint_name,
            cloudformation_json,
            account_id,
            region_name,
        )
        return new_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        # Get actual name because resource_name actually provides the ARN
        # since the Physical Resource ID is the ARN despite SageMaker
        # using the name for most of its operations.
        endpoint_name = resource_name.split("/")[-1]

        sagemaker_backends[account_id][region_name].delete_endpoint(endpoint_name)


class FakeEndpointConfig(BaseObject, CloudFormationModel):
    def __init__(
        self,
        account_id,
        region_name,
        endpoint_config_name,
        production_variants,
        data_capture_config,
        tags,
        kms_key_id,
    ):
        self.validate_production_variants(production_variants)

        self.endpoint_config_name = endpoint_config_name
        self.endpoint_config_arn = FakeEndpointConfig.arn_formatter(
            endpoint_config_name, account_id, region_name
        )
        self.production_variants = production_variants or []
        self.data_capture_config = data_capture_config or {}
        self.tags = tags or []
        self.kms_key_id = kms_key_id
        self.creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def validate_production_variants(self, production_variants):
        for production_variant in production_variants:
            if "InstanceType" in production_variant.keys():
                self.validate_instance_type(production_variant["InstanceType"])
            elif "ServerlessConfig" in production_variant.keys():
                self.validate_serverless_config(production_variant["ServerlessConfig"])
            else:
                message = f"Invalid Keys for ProductionVariant: received {production_variant.keys()} but expected it to contain one of {['InstanceType', 'ServerlessConfig']}"
                raise ValidationError(message=message)

    def validate_serverless_config(self, serverless_config):
        VALID_SERVERLESS_MEMORY_SIZE = [1024, 2048, 3072, 4096, 5120, 6144]
        if not validators.is_one_of(
            serverless_config["MemorySizeInMB"], VALID_SERVERLESS_MEMORY_SIZE
        ):
            message = f"Value '{serverless_config['MemorySizeInMB']}' at 'MemorySizeInMB' failed to satisfy constraint: Member must satisfy enum value set: {VALID_SERVERLESS_MEMORY_SIZE}"
            raise ValidationError(message=message)

    def validate_instance_type(self, instance_type):
        VALID_INSTANCE_TYPES = [
            "ml.r5d.12xlarge",
            "ml.r5.12xlarge",
            "ml.p2.xlarge",
            "ml.m5.4xlarge",
            "ml.m4.16xlarge",
            "ml.r5d.24xlarge",
            "ml.r5.24xlarge",
            "ml.p3.16xlarge",
            "ml.m5d.xlarge",
            "ml.m5.large",
            "ml.t2.xlarge",
            "ml.p2.16xlarge",
            "ml.m5d.12xlarge",
            "ml.inf1.2xlarge",
            "ml.m5d.24xlarge",
            "ml.c4.2xlarge",
            "ml.c5.2xlarge",
            "ml.c4.4xlarge",
            "ml.inf1.6xlarge",
            "ml.c5d.2xlarge",
            "ml.c5.4xlarge",
            "ml.g4dn.xlarge",
            "ml.g4dn.12xlarge",
            "ml.c5d.4xlarge",
            "ml.g4dn.2xlarge",
            "ml.c4.8xlarge",
            "ml.c4.large",
            "ml.c5d.xlarge",
            "ml.c5.large",
            "ml.g4dn.4xlarge",
            "ml.c5.9xlarge",
            "ml.g4dn.16xlarge",
            "ml.c5d.large",
            "ml.c5.xlarge",
            "ml.c5d.9xlarge",
            "ml.c4.xlarge",
            "ml.inf1.xlarge",
            "ml.g4dn.8xlarge",
            "ml.inf1.24xlarge",
            "ml.m5d.2xlarge",
            "ml.t2.2xlarge",
            "ml.c5d.18xlarge",
            "ml.m5d.4xlarge",
            "ml.t2.medium",
            "ml.c5.18xlarge",
            "ml.r5d.2xlarge",
            "ml.r5.2xlarge",
            "ml.p3.2xlarge",
            "ml.m5d.large",
            "ml.m5.xlarge",
            "ml.m4.10xlarge",
            "ml.t2.large",
            "ml.r5d.4xlarge",
            "ml.r5.4xlarge",
            "ml.m5.12xlarge",
            "ml.m4.xlarge",
            "ml.m5.24xlarge",
            "ml.m4.2xlarge",
            "ml.p2.8xlarge",
            "ml.m5.2xlarge",
            "ml.r5d.xlarge",
            "ml.r5d.large",
            "ml.r5.xlarge",
            "ml.r5.large",
            "ml.p3.8xlarge",
            "ml.m4.4xlarge",
        ]
        if not validators.is_one_of(instance_type, VALID_INSTANCE_TYPES):
            message = f"Value '{instance_type}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: {VALID_INSTANCE_TYPES}"
            raise ValidationError(message=message)

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"EndpointConfigArn": self.endpoint_config_arn}

    @staticmethod
    def arn_formatter(endpoint_config_name, account_id, region_name):
        return arn_formatter(
            "endpoint-config", endpoint_config_name, account_id, region_name
        )

    @property
    def physical_resource_id(self):
        return self.endpoint_config_arn

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["EndpointConfigName"]

    def get_cfn_attribute(self, attribute_name):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html#aws-resource-sagemaker-endpointconfig-return-values
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "EndpointConfigName":
            return self.endpoint_config_name
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html
        return "AWS::SageMaker::EndpointConfig"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        sagemaker_backend = sagemaker_backends[account_id][region_name]

        # Get required properties from provided CloudFormation template
        properties = cloudformation_json["Properties"]
        production_variants = properties["ProductionVariants"]

        endpoint_config = sagemaker_backend.create_endpoint_config(
            endpoint_config_name=resource_name,
            production_variants=production_variants,
            data_capture_config=properties.get("DataCaptureConfig", {}),
            kms_key_id=properties.get("KmsKeyId"),
            tags=properties.get("Tags", []),
        )
        return endpoint_config

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        # Most changes to the endpoint config will change resource name for EndpointConfigs
        cls.delete_from_cloudformation_json(
            original_resource.endpoint_config_arn,
            cloudformation_json,
            account_id,
            region_name,
        )
        new_resource = cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )
        return new_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        # Get actual name because resource_name actually provides the ARN
        # since the Physical Resource ID is the ARN despite SageMaker
        # using the name for most of its operations.
        endpoint_config_name = resource_name.split("/")[-1]

        sagemaker_backends[account_id][region_name].delete_endpoint_config(
            endpoint_config_name
        )


class Model(BaseObject, CloudFormationModel):
    def __init__(
        self,
        account_id,
        region_name,
        model_name,
        execution_role_arn,
        primary_container,
        vpc_config,
        containers=None,
        tags=None,
    ):
        self.model_name = model_name
        self.creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.containers = containers or []
        self.tags = tags or []
        self.enable_network_isolation = False
        self.vpc_config = vpc_config
        self.primary_container = primary_container
        self.execution_role_arn = execution_role_arn or "arn:test"
        self.model_arn = arn_formatter(
            "model", self.model_name, account_id, region_name
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"ModelArn": self.model_arn}

    @property
    def physical_resource_id(self):
        return self.model_arn

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["ModelName"]

    def get_cfn_attribute(self, attribute_name):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-model.html#aws-resource-sagemaker-model-return-values
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "ModelName":
            return self.model_name
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-model.html
        return "AWS::SageMaker::Model"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        sagemaker_backend = sagemaker_backends[account_id][region_name]

        # Get required properties from provided CloudFormation template
        properties = cloudformation_json["Properties"]
        execution_role_arn = properties["ExecutionRoleArn"]
        primary_container = properties["PrimaryContainer"]

        model = sagemaker_backend.create_model(
            ModelName=resource_name,
            ExecutionRoleArn=execution_role_arn,
            PrimaryContainer=primary_container,
            VpcConfig=properties.get("VpcConfig", {}),
            Containers=properties.get("Containers", []),
            Tags=properties.get("Tags", []),
        )
        return model

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        # Most changes to the model will change resource name for Models
        cls.delete_from_cloudformation_json(
            original_resource.model_arn, cloudformation_json, account_id, region_name
        )
        new_resource = cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )
        return new_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        # Get actual name because resource_name actually provides the ARN
        # since the Physical Resource ID is the ARN despite SageMaker
        # using the name for most of its operations.
        model_name = resource_name.split("/")[-1]

        sagemaker_backends[account_id][region_name].delete_model(model_name)


class VpcConfig(BaseObject):
    def __init__(self, security_group_ids, subnets):
        self.security_group_ids = security_group_ids
        self.subnets = subnets

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }


class Container(BaseObject):
    def __init__(self, **kwargs):
        self.container_hostname = kwargs.get("container_hostname", "localhost")
        self.model_data_url = kwargs.get("data_url", "")
        self.model_package_name = kwargs.get("package_name", "pkg")
        self.image = kwargs.get("image", "")
        self.environment = kwargs.get("environment", {})

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }


class FakeSagemakerNotebookInstance(CloudFormationModel):
    def __init__(
        self,
        account_id,
        region_name,
        notebook_instance_name,
        instance_type,
        role_arn,
        subnet_id,
        security_group_ids,
        kms_key_id,
        tags,
        lifecycle_config_name,
        direct_internet_access,
        volume_size_in_gb,
        accelerator_types,
        default_code_repository,
        additional_code_repositories,
        root_access,
    ):
        self.validate_volume_size_in_gb(volume_size_in_gb)
        self.validate_instance_type(instance_type)

        self.region_name = region_name
        self.notebook_instance_name = notebook_instance_name
        self.instance_type = instance_type
        self.role_arn = role_arn
        self.subnet_id = subnet_id
        self.security_group_ids = security_group_ids
        self.kms_key_id = kms_key_id
        self.tags = tags or []
        self.lifecycle_config_name = lifecycle_config_name
        self.direct_internet_access = direct_internet_access
        self.volume_size_in_gb = volume_size_in_gb
        self.accelerator_types = accelerator_types
        self.default_code_repository = default_code_repository
        self.additional_code_repositories = additional_code_repositories
        self.root_access = root_access
        self.status = None
        self.creation_time = self.last_modified_time = datetime.now()
        self.arn = arn_formatter(
            "notebook-instance", notebook_instance_name, account_id, region_name
        )
        self.start()

    def validate_volume_size_in_gb(self, volume_size_in_gb):
        if not validators.is_integer_between(volume_size_in_gb, mn=5, optional=True):
            message = "Invalid range for parameter VolumeSizeInGB, value: {}, valid range: 5-inf"
            raise ValidationError(message=message)

    def validate_instance_type(self, instance_type):
        VALID_INSTANCE_TYPES = [
            "ml.p2.xlarge",
            "ml.m5.4xlarge",
            "ml.m4.16xlarge",
            "ml.t3.xlarge",
            "ml.p3.16xlarge",
            "ml.t2.xlarge",
            "ml.p2.16xlarge",
            "ml.c4.2xlarge",
            "ml.c5.2xlarge",
            "ml.c4.4xlarge",
            "ml.c5d.2xlarge",
            "ml.c5.4xlarge",
            "ml.c5d.4xlarge",
            "ml.c4.8xlarge",
            "ml.c5d.xlarge",
            "ml.c5.9xlarge",
            "ml.c5.xlarge",
            "ml.c5d.9xlarge",
            "ml.c4.xlarge",
            "ml.t2.2xlarge",
            "ml.c5d.18xlarge",
            "ml.t3.2xlarge",
            "ml.t3.medium",
            "ml.t2.medium",
            "ml.c5.18xlarge",
            "ml.p3.2xlarge",
            "ml.m5.xlarge",
            "ml.m4.10xlarge",
            "ml.t2.large",
            "ml.m5.12xlarge",
            "ml.m4.xlarge",
            "ml.t3.large",
            "ml.m5.24xlarge",
            "ml.m4.2xlarge",
            "ml.p2.8xlarge",
            "ml.m5.2xlarge",
            "ml.p3.8xlarge",
            "ml.m4.4xlarge",
        ]
        if not validators.is_one_of(instance_type, VALID_INSTANCE_TYPES):
            message = f"Value '{instance_type}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: {VALID_INSTANCE_TYPES}"
            raise ValidationError(message=message)

    @property
    def url(self):
        return (
            f"{self.notebook_instance_name}.notebook.{self.region_name}.sagemaker.aws"
        )

    def start(self):
        self.status = "InService"

    @property
    def is_deletable(self):
        return self.status in ["Stopped", "Failed"]

    def stop(self):
        self.status = "Stopped"

    @property
    def physical_resource_id(self):
        return self.arn

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["NotebookInstanceName"]

    def get_cfn_attribute(self, attribute_name):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-notebookinstance.html#aws-resource-sagemaker-notebookinstance-return-values
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "NotebookInstanceName":
            return self.notebook_instance_name
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-notebookinstance.html
        return "AWS::SageMaker::NotebookInstance"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        # Get required properties from provided CloudFormation template
        properties = cloudformation_json["Properties"]
        instance_type = properties["InstanceType"]
        role_arn = properties["RoleArn"]

        notebook = sagemaker_backends[account_id][region_name].create_notebook_instance(
            notebook_instance_name=resource_name,
            instance_type=instance_type,
            role_arn=role_arn,
        )
        return notebook

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        # Operations keep same resource name so delete old and create new to mimic update
        cls.delete_from_cloudformation_json(
            original_resource.arn, cloudformation_json, account_id, region_name
        )
        new_resource = cls.create_from_cloudformation_json(
            original_resource.notebook_instance_name,
            cloudformation_json,
            account_id,
            region_name,
        )
        return new_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        # Get actual name because resource_name actually provides the ARN
        # since the Physical Resource ID is the ARN despite SageMaker
        # using the name for most of its operations.
        notebook_instance_name = resource_name.split("/")[-1]

        backend = sagemaker_backends[account_id][region_name]
        backend.stop_notebook_instance(notebook_instance_name)
        backend.delete_notebook_instance(notebook_instance_name)


class FakeSageMakerNotebookInstanceLifecycleConfig(BaseObject, CloudFormationModel):
    def __init__(
        self,
        account_id,
        region_name,
        notebook_instance_lifecycle_config_name,
        on_create,
        on_start,
    ):
        self.region_name = region_name
        self.notebook_instance_lifecycle_config_name = (
            notebook_instance_lifecycle_config_name
        )
        self.on_create = on_create
        self.on_start = on_start
        self.creation_time = self.last_modified_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.notebook_instance_lifecycle_config_arn = (
            FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                self.notebook_instance_lifecycle_config_name, account_id, region_name
            )
        )

    @staticmethod
    def arn_formatter(name, account_id, region_name):
        return arn_formatter(
            "notebook-instance-lifecycle-configuration", name, account_id, region_name
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"TrainingJobArn": self.training_job_arn}

    @property
    def physical_resource_id(self):
        return self.notebook_instance_lifecycle_config_arn

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["NotebookInstanceLifecycleConfigName"]

    def get_cfn_attribute(self, attribute_name):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-notebookinstancelifecycleconfig.html#aws-resource-sagemaker-notebookinstancelifecycleconfig-return-values
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "NotebookInstanceLifecycleConfigName":
            return self.notebook_instance_lifecycle_config_name
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-notebookinstancelifecycleconfig.html
        return "AWS::SageMaker::NotebookInstanceLifecycleConfig"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        config = sagemaker_backends[account_id][
            region_name
        ].create_notebook_instance_lifecycle_config(
            notebook_instance_lifecycle_config_name=resource_name,
            on_create=properties.get("OnCreate"),
            on_start=properties.get("OnStart"),
        )
        return config

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        # Operations keep same resource name so delete old and create new to mimic update
        cls.delete_from_cloudformation_json(
            original_resource.notebook_instance_lifecycle_config_arn,
            cloudformation_json,
            account_id,
            region_name,
        )
        new_resource = cls.create_from_cloudformation_json(
            original_resource.notebook_instance_lifecycle_config_name,
            cloudformation_json,
            account_id,
            region_name,
        )
        return new_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        # Get actual name because resource_name actually provides the ARN
        # since the Physical Resource ID is the ARN despite SageMaker
        # using the name for most of its operations.
        config_name = resource_name.split("/")[-1]

        backend = sagemaker_backends[account_id][region_name]
        backend.delete_notebook_instance_lifecycle_config(config_name)


class SageMakerModelBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._models = {}
        self.notebook_instances = {}
        self.endpoint_configs = {}
        self.endpoints = {}
        self.experiments = {}
        self.pipelines = {}
        self.pipeline_executions = {}
        self.processing_jobs = {}
        self.trials = {}
        self.trial_components = {}
        self.training_jobs = {}
        self.notebook_instance_lifecycle_configurations = {}

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint services."""
        api_service = BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "api.sagemaker", special_service_name="sagemaker.api"
        )

        notebook_service_id = f"vpce-svc-{BaseBackend.vpce_random_number()}"
        studio_service_id = f"vpce-svc-{BaseBackend.vpce_random_number()}"

        notebook_service = {
            "AcceptanceRequired": False,
            "AvailabilityZones": zones,
            "BaseEndpointDnsNames": [
                f"{notebook_service_id}.{service_region}.vpce.amazonaws.com",
                f"notebook.{service_region}.vpce.sagemaker.aws",
            ],
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "PrivateDnsName": f"*.notebook.{service_region}.sagemaker.aws",
            "PrivateDnsNameVerificationState": "verified",
            "PrivateDnsNames": [
                {"PrivateDnsName": f"*.notebook.{service_region}.sagemaker.aws"}
            ],
            "ServiceId": notebook_service_id,
            "ServiceName": f"aws.sagemaker.{service_region}.notebook",
            "ServiceType": [{"ServiceType": "Interface"}],
            "Tags": [],
            "VpcEndpointPolicySupported": True,
        }
        studio_service = {
            "AcceptanceRequired": False,
            "AvailabilityZones": zones,
            "BaseEndpointDnsNames": [
                f"{studio_service_id}.{service_region}.vpce.amazonaws.com",
                f"studio.{service_region}.vpce.sagemaker.aws",
            ],
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "PrivateDnsName": f"*.studio.{service_region}.sagemaker.aws",
            "PrivateDnsNameVerificationState": "verified",
            "PrivateDnsNames": [
                {"PrivateDnsName": f"*.studio.{service_region}.sagemaker.aws"}
            ],
            "ServiceId": studio_service_id,
            "ServiceName": f"aws.sagemaker.{service_region}.studio",
            "ServiceType": [{"ServiceType": "Interface"}],
            "Tags": [],
            "VpcEndpointPolicySupported": True,
        }
        return api_service + [notebook_service, studio_service]

    def create_model(self, **kwargs):
        model_obj = Model(
            account_id=self.account_id,
            region_name=self.region_name,
            model_name=kwargs.get("ModelName"),
            execution_role_arn=kwargs.get("ExecutionRoleArn"),
            primary_container=kwargs.get("PrimaryContainer", {}),
            vpc_config=kwargs.get("VpcConfig", {}),
            containers=kwargs.get("Containers", []),
            tags=kwargs.get("Tags", []),
        )

        self._models[kwargs.get("ModelName")] = model_obj
        return model_obj

    def describe_model(self, model_name=None):
        model = self._models.get(model_name)
        if model:
            return model
        arn = arn_formatter("model", model_name, self.account_id, self.region_name)
        raise ValidationError(message=f"Could not find model '{arn}'.")

    def list_models(self):
        return self._models.values()

    def delete_model(self, model_name=None):
        for model in self._models.values():
            if model.model_name == model_name:
                self._models.pop(model.model_name)
                break
        else:
            raise MissingModel(model=model_name)

    def create_experiment(self, experiment_name):
        experiment = FakeExperiment(
            account_id=self.account_id,
            region_name=self.region_name,
            experiment_name=experiment_name,
            tags=[],
        )
        self.experiments[experiment_name] = experiment
        return experiment.response_create

    def describe_experiment(self, experiment_name):
        experiment_data = self.experiments[experiment_name]
        return {
            "ExperimentName": experiment_data.experiment_name,
            "ExperimentArn": experiment_data.experiment_arn,
            "CreationTime": experiment_data.creation_time,
            "LastModifiedTime": experiment_data.last_modified_time,
        }

    def _get_resource_from_arn(self, arn):
        resources = {
            "model": self._models,
            "notebook-instance": self.notebook_instances,
            "endpoint": self.endpoints,
            "endpoint-config": self.endpoint_configs,
            "training-job": self.training_jobs,
            "experiment": self.experiments,
            "experiment-trial": self.trials,
            "experiment-trial-component": self.trial_components,
            "processing-job": self.processing_jobs,
            "pipeline": self.pipelines,
        }
        target_resource, target_name = arn.split(":")[-1].split("/")
        try:
            resource = resources.get(target_resource).get(target_name)
        except KeyError:
            message = f"Could not find {target_resource} with name {target_name}"
            raise ValidationError(message=message)
        return resource

    def add_tags(self, arn, tags):
        resource = self._get_resource_from_arn(arn)
        resource.tags.extend(tags)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_tags(self, arn):
        resource = self._get_resource_from_arn(arn)
        return resource.tags

    def delete_tags(self, arn, tag_keys):
        resource = self._get_resource_from_arn(arn)
        resource.tags = [tag for tag in resource.tags if tag["Key"] not in tag_keys]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_experiments(self):
        return list(self.experiments.values())

    def search(self, resource=None, search_expression=None):
        next_index = None

        valid_resources = [
            "Pipeline",
            "ModelPackageGroup",
            "TrainingJob",
            "ExperimentTrialComponent",
            "FeatureGroup",
            "Endpoint",
            "PipelineExecution",
            "Project",
            "ExperimentTrial",
            "Image",
            "ImageVersion",
            "ModelPackage",
            "Experiment",
        ]

        if resource not in valid_resources:
            raise AWSValidationException(
                f"An error occurred (ValidationException) when calling the Search operation: 1 validation error detected: Value '{resource}' at 'resource' failed to satisfy constraint: Member must satisfy enum value set: {valid_resources}"
            )

        def evaluate_search_expression(item):
            filters = None
            if search_expression is not None:
                filters = search_expression.get("Filters")

            if filters is not None:
                for f in filters:
                    if f["Operator"] == "Equals":
                        if f["Name"].startswith("Tags."):
                            key = f["Name"][5:]
                            value = f["Value"]

                            if (
                                len(
                                    [
                                        e
                                        for e in item.tags
                                        if e["Key"] == key and e["Value"] == value
                                    ]
                                )
                                == 0
                            ):
                                return False
                        if f["Name"] == "ExperimentName":
                            experiment_name = f["Value"]

                            if hasattr(item, "experiment_name"):
                                if getattr(item, "experiment_name") != experiment_name:
                                    return False
                            else:
                                raise ValidationError(
                                    message="Unknown property name: ExperimentName"
                                )

                        if f["Name"] == "TrialName":
                            raise AWSValidationException(
                                f"An error occurred (ValidationException) when calling the Search operation: Unknown property name: {f['Name']}"
                            )

                        if f["Name"] == "Parents.TrialName":
                            trial_name = f["Value"]

                            if getattr(item, "trial_name") != trial_name:
                                return False

            return True

        result = {
            "Results": [],
            "NextToken": str(next_index) if next_index is not None else None,
        }
        if resource == "Experiment":
            experiments_fetched = list(self.experiments.values())

            experiment_summaries = [
                {
                    "ExperimentName": experiment_data.experiment_name,
                    "ExperimentArn": experiment_data.experiment_arn,
                    "CreationTime": experiment_data.creation_time,
                    "LastModifiedTime": experiment_data.last_modified_time,
                }
                for experiment_data in experiments_fetched
                if evaluate_search_expression(experiment_data)
            ]

            for experiment_summary in experiment_summaries:
                result["Results"].append({"Experiment": experiment_summary})

        if resource == "ExperimentTrial":
            trials_fetched = list(self.trials.values())

            trial_summaries = [
                {
                    "TrialName": trial_data.trial_name,
                    "TrialArn": trial_data.trial_arn,
                    "CreationTime": trial_data.creation_time,
                    "LastModifiedTime": trial_data.last_modified_time,
                }
                for trial_data in trials_fetched
                if evaluate_search_expression(trial_data)
            ]

            for trial_summary in trial_summaries:
                result["Results"].append({"Trial": trial_summary})

        if resource == "ExperimentTrialComponent":
            trial_components_fetched = list(self.trial_components.values())

            trial_component_summaries = [
                {
                    "TrialComponentName": trial_component_data.trial_component_name,
                    "TrialComponentArn": trial_component_data.trial_component_arn,
                    "CreationTime": trial_component_data.creation_time,
                    "LastModifiedTime": trial_component_data.last_modified_time,
                }
                for trial_component_data in trial_components_fetched
                if evaluate_search_expression(trial_component_data)
            ]

            for trial_component_summary in trial_component_summaries:
                result["Results"].append({"TrialComponent": trial_component_summary})
        return result

    def delete_experiment(self, experiment_name):
        try:
            del self.experiments[experiment_name]
        except KeyError:
            arn = FakeTrial.arn_formatter(experiment_name, self.region_name)
            raise ValidationError(
                message=f"Could not find experiment configuration '{arn}'."
            )

    def create_trial(self, trial_name, experiment_name):
        trial = FakeTrial(
            account_id=self.account_id,
            region_name=self.region_name,
            trial_name=trial_name,
            experiment_name=experiment_name,
            tags=[],
            trial_components=[],
        )
        self.trials[trial_name] = trial
        return trial.response_create

    def describe_trial(self, trial_name):
        try:
            return self.trials[trial_name].response_object
        except KeyError:
            arn = FakeTrial.arn_formatter(trial_name, self.region_name)
            raise ValidationError(message=f"Could not find trial '{arn}'.")

    def delete_trial(self, trial_name):
        try:
            del self.trials[trial_name]
        except KeyError:
            arn = FakeTrial.arn_formatter(trial_name, self.region_name)
            raise ValidationError(
                message=f"Could not find trial configuration '{arn}'."
            )

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_trials(self, experiment_name=None, trial_component_name=None):
        trials_fetched = list(self.trials.values())

        def evaluate_filter_expression(trial_data):
            if experiment_name is not None:
                if trial_data.experiment_name != experiment_name:
                    return False

            if trial_component_name is not None:
                if trial_component_name not in trial_data.trial_components:
                    return False

            return True

        return [
            trial_data
            for trial_data in trials_fetched
            if evaluate_filter_expression(trial_data)
        ]

    def create_trial_component(self, trial_component_name, trial_name):
        trial_component = FakeTrialComponent(
            account_id=self.account_id,
            region_name=self.region_name,
            trial_component_name=trial_component_name,
            trial_name=trial_name,
            tags=[],
        )
        self.trial_components[trial_component_name] = trial_component
        return trial_component.response_create

    def delete_trial_component(self, trial_component_name):
        try:
            del self.trial_components[trial_component_name]
        except KeyError:
            arn = FakeTrial.arn_formatter(trial_component_name, self.region_name)
            raise ValidationError(
                message=f"Could not find trial-component configuration '{arn}'."
            )

    def describe_trial_component(self, trial_component_name):
        try:
            return self.trial_components[trial_component_name].response_object
        except KeyError:
            arn = FakeTrialComponent.arn_formatter(
                trial_component_name, self.account_id, self.region_name
            )
            raise ValidationError(message=f"Could not find trial component '{arn}'.")

    def _update_trial_component_details(self, trial_component_name, details_json):
        self.trial_components[trial_component_name].update(details_json)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_trial_components(self, trial_name=None):
        trial_components_fetched = list(self.trial_components.values())

        return [
            trial_component_data
            for trial_component_data in trial_components_fetched
            if trial_name is None or trial_component_data.trial_name == trial_name
        ]

    def associate_trial_component(self, params):
        trial_name = params["TrialName"]
        trial_component_name = params["TrialComponentName"]

        if trial_name in self.trials.keys():
            self.trials[trial_name].trial_components.extend([trial_component_name])
        else:
            raise ResourceNotFound(
                message=f"Trial 'arn:aws:sagemaker:{self.region_name}:{self.account_id}:experiment-trial/{trial_name}' does not exist."
            )

        if trial_component_name in self.trial_components.keys():
            self.trial_components[trial_component_name].trial_name = trial_name

        return {
            "TrialComponentArn": self.trial_components[
                trial_component_name
            ].trial_component_arn,
            "TrialArn": self.trials[trial_name].trial_arn,
        }

    def disassociate_trial_component(self, params):
        trial_component_name = params["TrialComponentName"]
        trial_name = params["TrialName"]

        if trial_component_name in self.trial_components.keys():
            self.trial_components[trial_component_name].trial_name = None

        if trial_name in self.trials.keys():
            self.trials[trial_name].trial_components = list(
                filter(
                    lambda x: x != trial_component_name,
                    self.trials[trial_name].trial_components,
                )
            )

        return {
            "TrialComponentArn": f"arn:aws:sagemaker:{self.region_name}:{self.account_id}:experiment-trial-component/{trial_component_name}",
            "TrialArn": f"arn:aws:sagemaker:{self.region_name}:{self.account_id}:experiment-trial/{trial_name}",
        }

    def create_notebook_instance(
        self,
        notebook_instance_name,
        instance_type,
        role_arn,
        subnet_id=None,
        security_group_ids=None,
        kms_key_id=None,
        tags=None,
        lifecycle_config_name=None,
        direct_internet_access="Enabled",
        volume_size_in_gb=5,
        accelerator_types=None,
        default_code_repository=None,
        additional_code_repositories=None,
        root_access=None,
    ):
        self._validate_unique_notebook_instance_name(notebook_instance_name)

        notebook_instance = FakeSagemakerNotebookInstance(
            account_id=self.account_id,
            region_name=self.region_name,
            notebook_instance_name=notebook_instance_name,
            instance_type=instance_type,
            role_arn=role_arn,
            subnet_id=subnet_id,
            security_group_ids=security_group_ids,
            kms_key_id=kms_key_id,
            tags=tags,
            lifecycle_config_name=lifecycle_config_name,
            direct_internet_access=direct_internet_access
            if direct_internet_access is not None
            else "Enabled",
            volume_size_in_gb=volume_size_in_gb if volume_size_in_gb is not None else 5,
            accelerator_types=accelerator_types,
            default_code_repository=default_code_repository,
            additional_code_repositories=additional_code_repositories,
            root_access=root_access,
        )
        self.notebook_instances[notebook_instance_name] = notebook_instance
        return notebook_instance

    def _validate_unique_notebook_instance_name(self, notebook_instance_name):
        if notebook_instance_name in self.notebook_instances:
            duplicate_arn = self.notebook_instances[notebook_instance_name].arn
            message = f"Cannot create a duplicate Notebook Instance ({duplicate_arn})"
            raise ValidationError(message=message)

    def get_notebook_instance(self, notebook_instance_name):
        try:
            return self.notebook_instances[notebook_instance_name]
        except KeyError:
            raise ValidationError(message="RecordNotFound")

    def start_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        notebook_instance.start()

    def stop_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        notebook_instance.stop()

    def delete_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        if not notebook_instance.is_deletable:
            message = f"Status ({notebook_instance.status}) not in ([Stopped, Failed]). Unable to transition to (Deleting) for Notebook Instance ({notebook_instance.arn})"
            raise ValidationError(message=message)
        del self.notebook_instances[notebook_instance_name]

    def create_notebook_instance_lifecycle_config(
        self, notebook_instance_lifecycle_config_name, on_create, on_start
    ):
        if (
            notebook_instance_lifecycle_config_name
            in self.notebook_instance_lifecycle_configurations
        ):
            arn = FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                notebook_instance_lifecycle_config_name,
                self.account_id,
                self.region_name,
            )
            message = f"Unable to create Notebook Instance Lifecycle Config {arn}. (Details: Notebook Instance Lifecycle Config already exists.)"
            raise ValidationError(message=message)
        lifecycle_config = FakeSageMakerNotebookInstanceLifecycleConfig(
            account_id=self.account_id,
            region_name=self.region_name,
            notebook_instance_lifecycle_config_name=notebook_instance_lifecycle_config_name,
            on_create=on_create,
            on_start=on_start,
        )
        self.notebook_instance_lifecycle_configurations[
            notebook_instance_lifecycle_config_name
        ] = lifecycle_config
        return lifecycle_config

    def describe_notebook_instance_lifecycle_config(
        self, notebook_instance_lifecycle_config_name
    ):
        try:
            return self.notebook_instance_lifecycle_configurations[
                notebook_instance_lifecycle_config_name
            ].response_object
        except KeyError:
            arn = FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                notebook_instance_lifecycle_config_name,
                self.account_id,
                self.region_name,
            )
            message = f"Unable to describe Notebook Instance Lifecycle Config '{arn}'. (Details: Notebook Instance Lifecycle Config does not exist.)"
            raise ValidationError(message=message)

    def delete_notebook_instance_lifecycle_config(
        self, notebook_instance_lifecycle_config_name
    ):
        try:
            del self.notebook_instance_lifecycle_configurations[
                notebook_instance_lifecycle_config_name
            ]
        except KeyError:
            arn = FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                notebook_instance_lifecycle_config_name,
                self.account_id,
                self.region_name,
            )
            message = f"Unable to delete Notebook Instance Lifecycle Config '{arn}'. (Details: Notebook Instance Lifecycle Config does not exist.)"
            raise ValidationError(message=message)

    def create_endpoint_config(
        self,
        endpoint_config_name,
        production_variants,
        data_capture_config,
        tags,
        kms_key_id,
    ):
        endpoint_config = FakeEndpointConfig(
            account_id=self.account_id,
            region_name=self.region_name,
            endpoint_config_name=endpoint_config_name,
            production_variants=production_variants,
            data_capture_config=data_capture_config,
            tags=tags,
            kms_key_id=kms_key_id,
        )
        self.validate_production_variants(production_variants)

        self.endpoint_configs[endpoint_config_name] = endpoint_config
        return endpoint_config

    def validate_production_variants(self, production_variants):
        for production_variant in production_variants:
            if production_variant["ModelName"] not in self._models:
                arn = arn_formatter(
                    "model",
                    production_variant["ModelName"],
                    self.account_id,
                    self.region_name,
                )
                raise ValidationError(message=f"Could not find model '{arn}'.")

    def describe_endpoint_config(self, endpoint_config_name):
        try:
            return self.endpoint_configs[endpoint_config_name].response_object
        except KeyError:
            arn = FakeEndpointConfig.arn_formatter(
                endpoint_config_name, self.account_id, self.region_name
            )
            raise ValidationError(
                message=f"Could not find endpoint configuration '{arn}'."
            )

    def delete_endpoint_config(self, endpoint_config_name):
        try:
            del self.endpoint_configs[endpoint_config_name]
        except KeyError:
            arn = FakeEndpointConfig.arn_formatter(
                endpoint_config_name, self.account_id, self.region_name
            )
            raise ValidationError(
                message=f"Could not find endpoint configuration '{arn}'."
            )

    def create_endpoint(self, endpoint_name, endpoint_config_name, tags):
        try:
            endpoint_config = self.describe_endpoint_config(endpoint_config_name)
        except KeyError:
            arn = FakeEndpointConfig.arn_formatter(
                endpoint_config_name, self.account_id, self.region_name
            )
            raise ValidationError(message=f"Could not find endpoint_config '{arn}'.")

        endpoint = FakeEndpoint(
            account_id=self.account_id,
            region_name=self.region_name,
            endpoint_name=endpoint_name,
            endpoint_config_name=endpoint_config_name,
            production_variants=endpoint_config["ProductionVariants"],
            data_capture_config=endpoint_config["DataCaptureConfig"],
            tags=tags,
        )

        self.endpoints[endpoint_name] = endpoint
        return endpoint

    def describe_endpoint(self, endpoint_name):
        try:
            return self.endpoints[endpoint_name].response_object
        except KeyError:
            arn = FakeEndpoint.arn_formatter(
                endpoint_name, self.account_id, self.region_name
            )
            raise ValidationError(message=f"Could not find endpoint '{arn}'.")

    def delete_endpoint(self, endpoint_name):
        try:
            del self.endpoints[endpoint_name]
        except KeyError:
            arn = FakeEndpoint.arn_formatter(
                endpoint_name, self.account_id, self.region_name
            )
            raise ValidationError(message=f"Could not find endpoint '{arn}'.")

    def create_processing_job(
        self,
        app_specification,
        experiment_config,
        network_config,
        processing_inputs,
        processing_job_name,
        processing_output_config,
        role_arn,
        tags,
        stopping_condition,
    ):
        processing_job = FakeProcessingJob(
            app_specification=app_specification,
            experiment_config=experiment_config,
            network_config=network_config,
            processing_inputs=processing_inputs,
            processing_job_name=processing_job_name,
            processing_output_config=processing_output_config,
            account_id=self.account_id,
            region_name=self.region_name,
            role_arn=role_arn,
            stopping_condition=stopping_condition,
            tags=tags,
        )
        self.processing_jobs[processing_job_name] = processing_job
        return processing_job

    def describe_processing_job(self, processing_job_name):
        try:
            return self.processing_jobs[processing_job_name].response_object
        except KeyError:
            arn = FakeProcessingJob.arn_formatter(
                processing_job_name, self.account_id, self.region_name
            )
            raise ValidationError(message=f"Could not find processing job '{arn}'.")

    def create_pipeline(
        self,
        pipeline_name,
        pipeline_display_name,
        pipeline_definition,
        pipeline_definition_s3_location,
        pipeline_description,
        role_arn,
        tags,
        parallelism_configuration,
    ):
        if not any([pipeline_definition, pipeline_definition_s3_location]):
            raise ValidationError(
                "An error occurred (ValidationException) when calling the CreatePipeline operation: Either "
                "Pipeline Definition or Pipeline Definition S3 location should be provided"
            )
        if all([pipeline_definition, pipeline_definition_s3_location]):
            raise ValidationError(
                "An error occurred (ValidationException) when calling the CreatePipeline operation: "
                "Both Pipeline Definition and Pipeline Definition S3 Location shouldn't be present"
            )

        if pipeline_name in self.pipelines:
            raise ValidationError(
                f"An error occurred (ValidationException) when calling the CreatePipeline operation: Pipeline names "
                f"must be unique within an AWS account and region. Pipeline with name ({pipeline_name}) already exists."
            )

        if pipeline_definition_s3_location:
            pipeline_definition = load_pipeline_definition_from_s3(
                pipeline_definition_s3_location, self.account_id
            )

        pipeline = FakePipeline(
            pipeline_name,
            pipeline_display_name,
            pipeline_definition,
            pipeline_description,
            role_arn,
            tags,
            self.account_id,
            self.region_name,
            parallelism_configuration,
        )

        self.pipelines[pipeline_name] = pipeline
        return pipeline

    def delete_pipeline(
        self,
        pipeline_name,
    ):
        pipeline = get_pipeline_from_name(self.pipelines, pipeline_name)
        del self.pipelines[pipeline.pipeline_name]
        return pipeline.pipeline_arn

    def update_pipeline(
        self,
        pipeline_name,
        **kwargs,
    ):
        pipeline = get_pipeline_from_name(self.pipelines, pipeline_name)
        if all(
            [
                kwargs.get("pipeline_definition"),
                kwargs.get("pipeline_definition_s3_location"),
            ]
        ):
            raise ValidationError(
                "An error occurred (ValidationException) when calling the UpdatePipeline operation: "
                "Both Pipeline Definition and Pipeline Definition S3 Location shouldn't be present"
            )

        for attr_key, attr_value in kwargs.items():
            if attr_value:
                if attr_key == "pipeline_definition_s3_location":
                    self.pipelines[
                        pipeline_name
                    ].pipeline_definition = load_pipeline_definition_from_s3(
                        attr_value, self.account_id
                    )
                    continue
                setattr(self.pipelines[pipeline_name], attr_key, attr_value)

        return pipeline.pipeline_arn

    def start_pipeline_execution(
        self,
        pipeline_name,
        pipeline_execution_display_name,
        pipeline_parameters,
        pipeline_execution_description,
        parallelism_configuration,
        client_request_token,
    ):
        pipeline = get_pipeline_from_name(self.pipelines, pipeline_name)
        execution_id = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=12)
        )
        pipeline_execution_arn = arn_formatter(
            _type="pipeline",
            _id=f"{pipeline.pipeline_name}/execution/{execution_id}",
            account_id=self.account_id,
            region_name=self.region_name,
        )

        fake_pipeline_execution = FakePipelineExecution(
            pipeline_execution_arn=pipeline_execution_arn,
            pipeline_execution_display_name=pipeline_execution_display_name,
            pipeline_parameters=pipeline_parameters,
            pipeline_execution_description=pipeline_execution_description,
            pipeline_definition=pipeline.pipeline_definition,
            parallelism_configuration=parallelism_configuration
            or pipeline.parallelism_configuration,
            client_request_token=client_request_token,
        )

        self.pipelines[pipeline_name].pipeline_executions[
            pipeline_execution_arn
        ] = fake_pipeline_execution
        self.pipelines[
            pipeline_name
        ].last_execution_time = fake_pipeline_execution.start_time

        response = {"PipelineExecutionArn": pipeline_execution_arn}
        return response

    def list_pipeline_executions(
        self,
        pipeline_name,
    ):
        pipeline = get_pipeline_from_name(self.pipelines, pipeline_name)
        response = {
            "PipelineExecutionSummaries": [
                {
                    "PipelineExecutionArn": pipeline_execution_arn,
                    "StartTime": pipeline_execution.start_time,
                    "PipelineExecutionStatus": pipeline_execution.pipeline_execution_status,
                    "PipelineExecutionDescription": pipeline_execution.pipeline_execution_description,
                    "PipelineExecutionDisplayName": pipeline_execution.pipeline_execution_display_name,
                    "PipelineExecutionFailureReason": str(
                        pipeline_execution.pipeline_execution_failure_reason
                    ),
                }
                for pipeline_execution_arn, pipeline_execution in pipeline.pipeline_executions.items()
            ]
        }
        return response

    def describe_pipeline_definition_for_execution(
        self,
        pipeline_execution_arn,
    ):
        pipeline_execution = get_pipeline_execution_from_arn(
            self.pipelines, pipeline_execution_arn
        )
        response = {
            "PipelineDefinition": str(
                pipeline_execution.pipeline_definition_for_execution
            ),
            "CreationTime": pipeline_execution.creation_time,
        }
        return response

    def list_pipeline_parameters_for_execution(
        self,
        pipeline_execution_arn,
    ):
        pipeline_execution = get_pipeline_execution_from_arn(
            self.pipelines, pipeline_execution_arn
        )
        response = {
            "PipelineParameters": pipeline_execution.pipeline_parameters,
        }
        return response

    def describe_pipeline_execution(
        self,
        pipeline_execution_arn,
    ):
        pipeline_execution = get_pipeline_execution_from_arn(
            self.pipelines, pipeline_execution_arn
        )
        pipeline_name = get_pipeline_name_from_execution_arn(pipeline_execution_arn)
        pipeline = get_pipeline_from_name(self.pipelines, pipeline_name)

        pipeline_execution_summaries = {
            "PipelineArn": pipeline.pipeline_arn,
            "PipelineExecutionArn": pipeline_execution.pipeline_execution_arn,
            "PipelineExecutionDisplayName": pipeline_execution.pipeline_execution_display_name,
            "PipelineExecutionStatus": pipeline_execution.pipeline_execution_status,
            "PipelineExecutionDescription": pipeline_execution.pipeline_execution_description,
            "PipelineExperimentConfig": {},
            "FailureReason": "",
            "CreationTime": pipeline_execution.creation_time,
            "LastModifiedTime": pipeline_execution.last_modified_time,
            "CreatedBy": pipeline_execution.created_by,
            "LastModifiedBy": pipeline_execution.last_modified_by,
            "ParallelismConfiguration": pipeline_execution.parallelism_configuration,
        }
        return pipeline_execution_summaries

    def describe_pipeline(
        self,
        pipeline_name,
    ):
        pipeline = get_pipeline_from_name(self.pipelines, pipeline_name)
        response = {
            "PipelineArn": pipeline.pipeline_arn,
            "PipelineName": pipeline.pipeline_name,
            "PipelineDisplayName": pipeline.pipeline_display_name,
            "PipelineDescription": pipeline.pipeline_description,
            "PipelineDefinition": pipeline.pipeline_definition,
            "RoleArn": pipeline.role_arn,
            "PipelineStatus": pipeline.pipeline_status,
            "CreationTime": pipeline.creation_time,
            "LastModifiedTime": pipeline.last_modified_time,
            "LastRunTime": pipeline.last_execution_time,
            "CreatedBy": pipeline.created_by,
            "LastModifiedBy": pipeline.last_modified_by,
            "ParallelismConfiguration": pipeline.parallelism_configuration,
        }

        return response

    def list_pipelines(
        self,
        pipeline_name_prefix,
        created_after,
        created_before,
        next_token,
        max_results,
        sort_by,
        sort_order,
    ):
        if next_token:
            try:
                starting_index = int(next_token)
                if starting_index > len(self.pipelines):
                    raise ValueError  # invalid next_token
            except ValueError:
                raise AWSValidationException('Invalid pagination token because "{0}".')
        else:
            starting_index = 0

        if max_results:
            end_index = max_results + starting_index
            pipelines_fetched = list(self.pipelines.values())[starting_index:end_index]
            if end_index >= len(self.pipelines):
                next_index = None
            else:
                next_index = end_index
        else:
            pipelines_fetched = list(self.pipelines.values())
            next_index = None

        if pipeline_name_prefix is not None:
            pipelines_fetched = filter(
                lambda x: pipeline_name_prefix in x.pipeline_name,
                pipelines_fetched,
            )

        def format_time(x):
            return (
                x
                if isinstance(x, str)
                else datetime.fromtimestamp(x).strftime("%Y-%m-%d " "%H:%M:%S")
            )

        if created_after is not None:
            pipelines_fetched = filter(
                lambda x: x.creation_time > format_time(created_after),
                pipelines_fetched,
            )

        if created_before is not None:
            pipelines_fetched = filter(
                lambda x: x.creation_time < format_time(created_before),
                pipelines_fetched,
            )

        sort_key = "pipeline_name" if sort_by == "Name" else "creation_time"
        sort_order = False if sort_order == "Ascending" else True
        pipelines_fetched = sorted(
            pipelines_fetched,
            key=lambda pipeline_fetched: getattr(pipeline_fetched, sort_key),
            reverse=sort_order,
        )

        pipeline_summaries = [
            {
                "PipelineArn": pipeline_data.pipeline_arn,
                "PipelineName": pipeline_data.pipeline_name,
                "PipelineDisplayName": pipeline_data.pipeline_display_name,
                "PipelineDescription": pipeline_data.pipeline_description,
                "RoleArn": pipeline_data.role_arn,
                "CreationTime": pipeline_data.creation_time,
                "LastModifiedTime": pipeline_data.last_modified_time,
                "LastExecutionTime": pipeline_data.last_execution_time,
            }
            for pipeline_data in pipelines_fetched
        ]

        return {
            "PipelineSummaries": pipeline_summaries,
            "NextToken": str(next_index) if next_index is not None else None,
        }

    def list_processing_jobs(
        self,
        next_token,
        max_results,
        creation_time_after,
        creation_time_before,
        last_modified_time_after,
        last_modified_time_before,
        name_contains,
        status_equals,
    ):
        if next_token:
            try:
                starting_index = int(next_token)
                if starting_index > len(self.processing_jobs):
                    raise ValueError  # invalid next_token
            except ValueError:
                raise AWSValidationException('Invalid pagination token because "{0}".')
        else:
            starting_index = 0

        if max_results:
            end_index = max_results + starting_index
            processing_jobs_fetched = list(self.processing_jobs.values())[
                starting_index:end_index
            ]
            if end_index >= len(self.processing_jobs):
                next_index = None
            else:
                next_index = end_index
        else:
            processing_jobs_fetched = list(self.processing_jobs.values())
            next_index = None

        if name_contains is not None:
            processing_jobs_fetched = filter(
                lambda x: name_contains in x.processing_job_name,
                processing_jobs_fetched,
            )

        if creation_time_after is not None:
            processing_jobs_fetched = filter(
                lambda x: x.creation_time > creation_time_after, processing_jobs_fetched
            )

        if creation_time_before is not None:
            processing_jobs_fetched = filter(
                lambda x: x.creation_time < creation_time_before,
                processing_jobs_fetched,
            )

        if last_modified_time_after is not None:
            processing_jobs_fetched = filter(
                lambda x: x.last_modified_time > last_modified_time_after,
                processing_jobs_fetched,
            )

        if last_modified_time_before is not None:
            processing_jobs_fetched = filter(
                lambda x: x.last_modified_time < last_modified_time_before,
                processing_jobs_fetched,
            )
        if status_equals is not None:
            processing_jobs_fetched = filter(
                lambda x: x.training_job_status == status_equals,
                processing_jobs_fetched,
            )

        processing_job_summaries = [
            {
                "ProcessingJobName": processing_job_data.processing_job_name,
                "ProcessingJobArn": processing_job_data.processing_job_arn,
                "CreationTime": processing_job_data.creation_time,
                "ProcessingEndTime": processing_job_data.processing_end_time,
                "LastModifiedTime": processing_job_data.last_modified_time,
                "ProcessingJobStatus": processing_job_data.processing_job_status,
            }
            for processing_job_data in processing_jobs_fetched
        ]

        return {
            "ProcessingJobSummaries": processing_job_summaries,
            "NextToken": str(next_index) if next_index is not None else None,
        }

    def create_training_job(
        self,
        training_job_name,
        hyper_parameters,
        algorithm_specification,
        role_arn,
        input_data_config,
        output_data_config,
        resource_config,
        vpc_config,
        stopping_condition,
        tags,
        enable_network_isolation,
        enable_inter_container_traffic_encryption,
        enable_managed_spot_training,
        checkpoint_config,
        debug_hook_config,
        debug_rule_configurations,
        tensor_board_output_config,
        experiment_config,
    ):
        training_job = FakeTrainingJob(
            account_id=self.account_id,
            region_name=self.region_name,
            training_job_name=training_job_name,
            hyper_parameters=hyper_parameters,
            algorithm_specification=algorithm_specification,
            role_arn=role_arn,
            input_data_config=input_data_config,
            output_data_config=output_data_config,
            resource_config=resource_config,
            vpc_config=vpc_config,
            stopping_condition=stopping_condition,
            tags=tags,
            enable_network_isolation=enable_network_isolation,
            enable_inter_container_traffic_encryption=enable_inter_container_traffic_encryption,
            enable_managed_spot_training=enable_managed_spot_training,
            checkpoint_config=checkpoint_config,
            debug_hook_config=debug_hook_config,
            debug_rule_configurations=debug_rule_configurations,
            tensor_board_output_config=tensor_board_output_config,
            experiment_config=experiment_config,
        )
        self.training_jobs[training_job_name] = training_job
        return training_job

    def describe_training_job(self, training_job_name):
        try:
            return self.training_jobs[training_job_name].response_object
        except KeyError:
            arn = FakeTrainingJob.arn_formatter(
                training_job_name, self.account_id, self.region_name
            )
            message = f"Could not find training job '{arn}'."
            raise ValidationError(message=message)

    def list_training_jobs(
        self,
        next_token,
        max_results,
        creation_time_after,
        creation_time_before,
        last_modified_time_after,
        last_modified_time_before,
        name_contains,
        status_equals,
    ):
        if next_token:
            try:
                starting_index = int(next_token)
                if starting_index > len(self.training_jobs):
                    raise ValueError  # invalid next_token
            except ValueError:
                raise AWSValidationException('Invalid pagination token because "{0}".')
        else:
            starting_index = 0

        if max_results:
            end_index = max_results + starting_index
            training_jobs_fetched = list(self.training_jobs.values())[
                starting_index:end_index
            ]
            if end_index >= len(self.training_jobs):
                next_index = None
            else:
                next_index = end_index
        else:
            training_jobs_fetched = list(self.training_jobs.values())
            next_index = None

        if name_contains is not None:
            training_jobs_fetched = filter(
                lambda x: name_contains in x.training_job_name, training_jobs_fetched
            )

        if creation_time_after is not None:
            training_jobs_fetched = filter(
                lambda x: x.creation_time > creation_time_after, training_jobs_fetched
            )

        if creation_time_before is not None:
            training_jobs_fetched = filter(
                lambda x: x.creation_time < creation_time_before, training_jobs_fetched
            )

        if last_modified_time_after is not None:
            training_jobs_fetched = filter(
                lambda x: x.last_modified_time > last_modified_time_after,
                training_jobs_fetched,
            )

        if last_modified_time_before is not None:
            training_jobs_fetched = filter(
                lambda x: x.last_modified_time < last_modified_time_before,
                training_jobs_fetched,
            )
        if status_equals is not None:
            training_jobs_fetched = filter(
                lambda x: x.training_job_status == status_equals, training_jobs_fetched
            )

        training_job_summaries = [
            {
                "TrainingJobName": training_job_data.training_job_name,
                "TrainingJobArn": training_job_data.training_job_arn,
                "CreationTime": training_job_data.creation_time,
                "TrainingEndTime": training_job_data.training_end_time,
                "LastModifiedTime": training_job_data.last_modified_time,
                "TrainingJobStatus": training_job_data.training_job_status,
            }
            for training_job_data in training_jobs_fetched
        ]

        return {
            "TrainingJobSummaries": training_job_summaries,
            "NextToken": str(next_index) if next_index is not None else None,
        }

    def update_endpoint_weights_and_capacities(
        self, endpoint_name, desired_weights_and_capacities
    ):
        # Validate inputs
        endpoint = self.endpoints.get(endpoint_name, None)
        if not endpoint:
            arn = FakeEndpoint.arn_formatter(
                endpoint_name, self.account_id, self.region_name
            )
            raise AWSValidationException(f'Could not find endpoint "{arn}".')

        names_checked = []
        for variant_config in desired_weights_and_capacities:
            name = variant_config.get("VariantName")

            if name in names_checked:
                raise AWSValidationException(
                    f'The variant name "{name}" was non-unique within the request.'
                )

            if not any(
                variant["VariantName"] == name
                for variant in endpoint.production_variants
            ):
                raise AWSValidationException(
                    f'The variant name(s) "{name}" is/are not present within endpoint configuration "{endpoint.endpoint_config_name}".'
                )

            names_checked.append(name)

        # Update endpoint variants
        endpoint.endpoint_status = "Updating"

        for variant_config in desired_weights_and_capacities:
            name = variant_config.get("VariantName")
            desired_weight = variant_config.get("DesiredWeight")
            desired_instance_count = variant_config.get("DesiredInstanceCount")

            for variant in endpoint.production_variants:
                if variant.get("VariantName") == name:
                    variant["DesiredWeight"] = desired_weight
                    variant["CurrentWeight"] = desired_weight
                    variant["DesiredInstanceCount"] = desired_instance_count
                    variant["CurrentInstanceCount"] = desired_instance_count
                    break

        endpoint.endpoint_status = "InService"
        return endpoint.endpoint_arn


class FakeExperiment(BaseObject):
    def __init__(self, account_id, region_name, experiment_name, tags):
        self.experiment_name = experiment_name
        self.experiment_arn = arn_formatter(
            "experiment", experiment_name, account_id, region_name
        )
        self.tags = tags
        self.creation_time = self.last_modified_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"ExperimentArn": self.experiment_arn}


class FakeTrial(BaseObject):
    def __init__(
        self,
        account_id,
        region_name,
        trial_name,
        experiment_name,
        tags,
        trial_components,
    ):
        self.trial_name = trial_name
        self.trial_arn = arn_formatter(
            "experiment-trial", trial_name, account_id, region_name
        )
        self.tags = tags
        self.trial_components = trial_components
        self.experiment_name = experiment_name
        self.creation_time = self.last_modified_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"TrialArn": self.trial_arn}


class FakeTrialComponent(BaseObject):
    def __init__(self, account_id, region_name, trial_component_name, trial_name, tags):
        self.trial_component_name = trial_component_name
        self.trial_component_arn = FakeTrialComponent.arn_formatter(
            trial_component_name, account_id, region_name
        )
        self.tags = tags
        self.trial_name = trial_name
        now_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.creation_time = self.last_modified_time = now_string

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"TrialComponentArn": self.trial_component_arn}

    @staticmethod
    def arn_formatter(trial_component_name, account_id, region_name):
        return arn_formatter(
            "experiment-trial-component", trial_component_name, account_id, region_name
        )


sagemaker_backends = BackendDict(SageMakerModelBackend, "sagemaker")
