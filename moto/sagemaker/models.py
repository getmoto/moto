from __future__ import unicode_literals
from datetime import datetime

from .exceptions import MissingModel
from moto.ec2 import ec2_backends
from moto.ecr.models import BaseObject
from moto.core import BaseBackend
from moto.core.exceptions import RESTError
from moto.sts.models import ACCOUNT_ID

import moto.sagemaker.validators as validators


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
        self.ModelName = model_name
        self.creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.Containers = containers
        self.Tags = tags
        self.EnableNetworkIsolation = False
        self.VpcConfig = vpc_config
        self.PrimaryContainer = primary_container
        self.ExecutionRoleArn = execution_role_arn or "arn:test"
        self.ModelArn = self.arn_for_model_name(self.ModelName, region_name)

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"ModelArn": self.ModelArn}

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
        self.SecurityGroupIds = security_group_ids
        self.Subnets = subnets

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }


class Container(BaseObject):
    def __init__(self, **kwargs):
        self.ContainerHostname = kwargs.get("container_hostname", "localhost")
        self.ModelDataUrl = kwargs.get("data_url", "")
        self.ModelPackageName = kwargs.get("package_name", "pkg")
        self.Image = kwargs.get("image", "")
        self.Environment = kwargs.get("environment", {})

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
            raise RESTError(
                error_type="ValidationException",
                message=message,
                template="error_json",
            )

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
            raise RESTError(
                error_type="ValidationException",
                message=message,
                template="error_json",
            )

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


class SageMakerModelBackend(BaseBackend):
    def __init__(self, region_name=None):
        self._models = {}
        self.notebook_instances = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_model(self, **kwargs):
        model_obj = Model(
            self.region_name,
            kwargs.get("ModelName"),
            kwargs.get("ExecutionRoleArn"),
            kwargs.get("PrimaryContainer", {}),
            kwargs.get("VpcConfig", {}),
            kwargs.get("Containers", []),
            kwargs.get("Tags", []),
        )

        self._models[kwargs.get("ModelName")] = model_obj
        return model_obj.response_create

    def describe_model(self, model_name=None):
        for model in self._models.values():
            # If a registry_id was supplied, ensure this repository matches
            if model.ModelName != model_name:
                continue
            return model.response_object
        message = f'Could not find model "{Model.arn_for_model_name(model_name, self.region_name)}"'
        raise RESTError(
            error_type="ValidationException", message=message, template="error_json",
        )

    def list_models(self):
        models = []
        for model in self._models.values():
            model_response = model.response_object.copy()
            model_response.update(model.response_create)
            models.append(model_response)
        return {"Models": models}

    def delete_model(self, model_name=None):
        for model in self._models.values():
            if model.ModelName == model_name:
                self._models.pop(model.ModelName)
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
            self.region_name,
            notebook_instance_name,
            instance_type,
            role_arn,
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
            raise RESTError(
                error_type="ValidationException",
                message=message,
                template="error_json",
            )

    def get_notebook_instance(self, notebook_instance_name):
        try:
            return self.notebook_instances[notebook_instance_name]
        except KeyError:
            message = "RecordNotFound"
            raise RESTError(
                error_type="ValidationException",
                message=message,
                template="error_json",
            )

    def get_notebook_instance_by_arn(self, arn):
        instances = [
            notebook_instance
            for notebook_instance in self.notebook_instances.values()
            if notebook_instance.arn == arn
        ]
        if len(instances) == 0:
            message = "RecordNotFound"
            raise RESTError(
                error_type="ValidationException",
                message=message,
                template="error_json",
            )
        return instances[0]

    def delete_notebook_instance(self, notebook_instance_name):
        notebook_instance = self.get_notebook_instance(notebook_instance_name)
        if not notebook_instance.is_deletable:
            message = f"Status ({notebook_instance.status}) not in ([Stopped, Failed]). Unable to transition to (Deleting) for Notebook Instance ({notebook_instance.arn})"
            raise RESTError(
                error_type="ValidationException",
                message=message,
                template="error_json",
            )
        del self.notebook_instances[notebook_instance_name]


sagemaker_backends = {}
for region, ec2_backend in ec2_backends.items():
    sagemaker_backends[region] = SageMakerModelBackend(region)

