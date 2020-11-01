from __future__ import unicode_literals

import os
from boto3 import Session
from copy import deepcopy
from datetime import datetime

from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.sagemaker import validators
from .exceptions import MissingModel, ValidationError


class BaseObject(BaseModel):
    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split("_")):
            words.append(word.title())
        return "".join(words)

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


class FakeTrainingJob(BaseObject):
    def __init__(
        self,
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
        self.tags = tags
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
            training_job_name, region_name
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
    def arn_formatter(endpoint_name, region_name):
        return (
            "arn:aws:sagemaker:"
            + region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":training-job/"
            + endpoint_name
        )


class FakeEndpoint(BaseObject):
    def __init__(
        self,
        region_name,
        endpoint_name,
        endpoint_config_name,
        production_variants,
        data_capture_config,
        tags,
    ):
        self.endpoint_name = endpoint_name
        self.endpoint_arn = FakeEndpoint.arn_formatter(endpoint_name, region_name)
        self.endpoint_config_name = endpoint_config_name
        self.production_variants = production_variants
        self.data_capture_config = data_capture_config
        self.tags = tags or []
        self.endpoint_status = "InService"
        self.failure_reason = None
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
        return {"EndpointArn": self.endpoint_arn}

    @staticmethod
    def arn_formatter(endpoint_name, region_name):
        return (
            "arn:aws:sagemaker:"
            + region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":endpoint/"
            + endpoint_name
        )


class FakeEndpointConfig(BaseObject):
    def __init__(
        self,
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
            endpoint_config_name, region_name
        )
        self.production_variants = production_variants or []
        self.data_capture_config = data_capture_config or {}
        self.tags = tags or []
        self.kms_key_id = kms_key_id
        self.creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def validate_production_variants(self, production_variants):
        for production_variant in production_variants:
            self.validate_instance_type(production_variant["InstanceType"])

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
            message = "Value '{}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: {}".format(
                instance_type, VALID_INSTANCE_TYPES
            )
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
    def arn_formatter(model_name, region_name):
        return (
            "arn:aws:sagemaker:"
            + region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":endpoint-config/"
            + model_name
        )


class Model(BaseObject):
    def __init__(
        self,
        region_name,
        model_name,
        execution_role_arn,
        primary_container,
        vpc_config,
        containers=[],
        tags=[],
    ):
        self.model_name = model_name
        self.creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.containers = containers
        self.tags = tags
        self.enable_network_isolation = False
        self.vpc_config = vpc_config
        self.primary_container = primary_container
        self.execution_role_arn = execution_role_arn or "arn:test"
        self.model_arn = self.arn_for_model_name(self.model_name, region_name)

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"ModelArn": self.model_arn}

    @staticmethod
    def arn_for_model_name(model_name, region_name):
        return (
            "arn:aws:sagemaker:"
            + region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":model/"
            + model_name
        )


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


class FakeSagemakerNotebookInstance:
    def __init__(
        self,
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
            message = "Value '{}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: {}".format(
                instance_type, VALID_INSTANCE_TYPES
            )
            raise ValidationError(message=message)

    @property
    def arn(self):
        return (
            "arn:aws:sagemaker:"
            + self.region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":notebook-instance/"
            + self.notebook_instance_name
        )

    @property
    def url(self):
        return "{}.notebook.{}.sagemaker.aws".format(
            self.notebook_instance_name, self.region_name
        )

    def start(self):
        self.status = "InService"

    @property
    def is_deletable(self):
        return self.status in ["Stopped", "Failed"]

    def stop(self):
        self.status = "Stopped"


class FakeSageMakerNotebookInstanceLifecycleConfig(BaseObject):
    def __init__(
        self, region_name, notebook_instance_lifecycle_config_name, on_create, on_start
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
        self.notebook_instance_lifecycle_config_arn = FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
            self.notebook_instance_lifecycle_config_name, self.region_name
        )

    @staticmethod
    def arn_formatter(notebook_instance_lifecycle_config_name, region_name):
        return (
            "arn:aws:sagemaker:"
            + region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":notebook-instance-lifecycle-configuration/"
            + notebook_instance_lifecycle_config_name
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


class SageMakerModelBackend(BaseBackend):
    def __init__(self, region_name=None):
        self._models = {}
        self.notebook_instances = {}
        self.endpoint_configs = {}
        self.endpoints = {}
        self.training_jobs = {}
        self.notebook_instance_lifecycle_configurations = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_model(self, **kwargs):
        model_obj = Model(
            region_name=self.region_name,
            model_name=kwargs.get("ModelName"),
            execution_role_arn=kwargs.get("ExecutionRoleArn"),
            primary_container=kwargs.get("PrimaryContainer", {}),
            vpc_config=kwargs.get("VpcConfig", {}),
            containers=kwargs.get("Containers", []),
            tags=kwargs.get("Tags", []),
        )

        self._models[kwargs.get("ModelName")] = model_obj
        return model_obj.response_create

    def describe_model(self, model_name=None):
        model = self._models.get(model_name)
        if model:
            return model.response_object
        message = "Could not find model '{}'.".format(
            Model.arn_for_model_name(model_name, self.region_name)
        )
        raise ValidationError(message=message)

    def list_models(self):
        models = []
        for model in self._models.values():
            model_response = deepcopy(model.response_object)
            models.append(model_response)
        return {"Models": models}

    def delete_model(self, model_name=None):
        for model in self._models.values():
            if model.model_name == model_name:
                self._models.pop(model.model_name)
                break
        else:
            raise MissingModel(model=model_name)

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
            message = "Cannot create a duplicate Notebook Instance ({})".format(
                duplicate_arn
            )
            raise ValidationError(message=message)

    def get_notebook_instance(self, notebook_instance_name):
        try:
            return self.notebook_instances[notebook_instance_name]
        except KeyError:
            raise ValidationError(message="RecordNotFound")

    def get_notebook_instance_by_arn(self, arn):
        instances = [
            notebook_instance
            for notebook_instance in self.notebook_instances.values()
            if notebook_instance.arn == arn
        ]
        if len(instances) == 0:
            raise ValidationError(message="RecordNotFound")
        return instances[0]

    def start_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        notebook_instance.start()

    def stop_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        notebook_instance.stop()

    def delete_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        if not notebook_instance.is_deletable:
            message = "Status ({}) not in ([Stopped, Failed]). Unable to transition to (Deleting) for Notebook Instance ({})".format(
                notebook_instance.status, notebook_instance.arn
            )
            raise ValidationError(message=message)
        del self.notebook_instances[notebook_instance_name]

    def get_notebook_instance_tags(self, arn):
        try:
            notebook_instance = self.get_notebook_instance_by_arn(arn)
            return notebook_instance.tags or []
        except RESTError:
            return []

    def create_notebook_instance_lifecycle_config(
        self, notebook_instance_lifecycle_config_name, on_create, on_start
    ):
        if (
            notebook_instance_lifecycle_config_name
            in self.notebook_instance_lifecycle_configurations
        ):
            message = "Unable to create Notebook Instance Lifecycle Config {}. (Details: Notebook Instance Lifecycle Config already exists.)".format(
                FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                    notebook_instance_lifecycle_config_name, self.region_name
                )
            )
            raise ValidationError(message=message)
        lifecycle_config = FakeSageMakerNotebookInstanceLifecycleConfig(
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
            message = "Unable to describe Notebook Instance Lifecycle Config '{}'. (Details: Notebook Instance Lifecycle Config does not exist.)".format(
                FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                    notebook_instance_lifecycle_config_name, self.region_name
                )
            )
            raise ValidationError(message=message)

    def delete_notebook_instance_lifecycle_config(
        self, notebook_instance_lifecycle_config_name
    ):
        try:
            del self.notebook_instance_lifecycle_configurations[
                notebook_instance_lifecycle_config_name
            ]
        except KeyError:
            message = "Unable to delete Notebook Instance Lifecycle Config '{}'. (Details: Notebook Instance Lifecycle Config does not exist.)".format(
                FakeSageMakerNotebookInstanceLifecycleConfig.arn_formatter(
                    notebook_instance_lifecycle_config_name, self.region_name
                )
            )
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
                message = "Could not find model '{}'.".format(
                    Model.arn_for_model_name(
                        production_variant["ModelName"], self.region_name
                    )
                )
                raise ValidationError(message=message)

    def describe_endpoint_config(self, endpoint_config_name):
        try:
            return self.endpoint_configs[endpoint_config_name].response_object
        except KeyError:
            message = "Could not find endpoint configuration '{}'.".format(
                FakeEndpointConfig.arn_formatter(endpoint_config_name, self.region_name)
            )
            raise ValidationError(message=message)

    def delete_endpoint_config(self, endpoint_config_name):
        try:
            del self.endpoint_configs[endpoint_config_name]
        except KeyError:
            message = "Could not find endpoint configuration '{}'.".format(
                FakeEndpointConfig.arn_formatter(endpoint_config_name, self.region_name)
            )
            raise ValidationError(message=message)

    def create_endpoint(
        self, endpoint_name, endpoint_config_name, tags,
    ):
        try:
            endpoint_config = self.describe_endpoint_config(endpoint_config_name)
        except KeyError:
            message = "Could not find endpoint_config '{}'.".format(
                FakeEndpointConfig.arn_formatter(endpoint_config_name, self.region_name)
            )
            raise ValidationError(message=message)

        endpoint = FakeEndpoint(
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
            message = "Could not find endpoint configuration '{}'.".format(
                FakeEndpoint.arn_formatter(endpoint_name, self.region_name)
            )
            raise ValidationError(message=message)

    def delete_endpoint(self, endpoint_name):
        try:
            del self.endpoints[endpoint_name]
        except KeyError:
            message = "Could not find endpoint configuration '{}'.".format(
                FakeEndpoint.arn_formatter(endpoint_name, self.region_name)
            )
            raise ValidationError(message=message)

    def get_endpoint_by_arn(self, arn):
        endpoints = [
            endpoint
            for endpoint in self.endpoints.values()
            if endpoint.endpoint_arn == arn
        ]
        if len(endpoints) == 0:
            message = "RecordNotFound"
            raise ValidationError(message=message)
        return endpoints[0]

    def get_endpoint_tags(self, arn):
        try:
            endpoint = self.get_endpoint_by_arn(arn)
            return endpoint.tags or []
        except RESTError:
            return []

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
            message = "Could not find training job '{}'.".format(
                FakeTrainingJob.arn_formatter(training_job_name, self.region_name)
            )
            raise ValidationError(message=message)

    def delete_training_job(self, training_job_name):
        try:
            del self.training_jobs[training_job_name]
        except KeyError:
            message = "Could not find endpoint configuration '{}'.".format(
                FakeTrainingJob.arn_formatter(training_job_name, self.region_name)
            )
            raise ValidationError(message=message)

    def get_training_job_by_arn(self, arn):
        training_jobs = [
            training_job
            for training_job in self.training_jobs.values()
            if training_job.training_job_arn == arn
        ]
        if len(training_jobs) == 0:
            raise ValidationError(message="RecordNotFound")
        return training_jobs[0]

    def get_training_job_tags(self, arn):
        try:
            training_job = self.get_training_job_by_arn(arn)
            return training_job.tags or []
        except RESTError:
            return []


sagemaker_backends = {}
for region in Session().get_available_regions("sagemaker"):
    sagemaker_backends[region] = SageMakerModelBackend(region)
for region in Session().get_available_regions("sagemaker", partition_name="aws-us-gov"):
    sagemaker_backends[region] = SageMakerModelBackend(region)
for region in Session().get_available_regions("sagemaker", partition_name="aws-cn"):
    sagemaker_backends[region] = SageMakerModelBackend(region)
