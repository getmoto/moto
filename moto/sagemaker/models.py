from __future__ import unicode_literals
from datetime import datetime

from .exceptions import MissingModel
from moto.ec2 import ec2_backends
from moto.ecr.models import BaseObject
from moto.core import BaseBackend


class Model(BaseObject):
    def __init__(
        self,
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

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {
            k: v for k, v in response_object.items() if v is not None and v != [None]
        }

    @property
    def response_create(self):
        return {"ModelArn": self.ExecutionRoleArn}


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


class SageMakerBackend(BaseBackend):
    def __init__(self, region_name=None):
        self._models = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_model(self, **kwargs):
        model_obj = Model(
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

    def list_models(self):
        return {
            "Models": [
                {**model.response_create, **model.response_object}
                for model in self._models.values()
            ]
        }

    def delete_model(self, model_name=None):
        for model in self._models.values():
            if model.ModelName == model_name:
                self._models.pop(model.ModelName)
                break
        else:
            raise MissingModel(model=model_name)


sagemaker_backends = {}
for region, ec2_backend in ec2_backends.items():
    sagemaker_backends[region] = SageMakerBackend()
