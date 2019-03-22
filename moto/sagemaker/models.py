from __future__ import unicode_literals

import hashlib
from copy import copy
from random import random
from datetime import datetime

from botocore.exceptions import ParamValidationError

from moto.ec2 import ec2_backends
from moto.ecr.models import BaseObject
from moto.core import BaseBackend, BaseModel

'''
{
   "Containers": [ 
      { 
         "ContainerHostname": "string",
         "Environment": { 
            "string" : "string" 
         },
         "Image": "string",
         "ModelDataUrl": "string",
         "ModelPackageName": "string"
      }
   ],
   "EnableNetworkIsolation": boolean,
   "ExecutionRoleArn": "string",
   "ModelName": "string",
   "PrimaryContainer": { 
      "ContainerHostname": "string",
      "Environment": { 
         "string" : "string" 
      },
      "Image": "string",
      "ModelDataUrl": "string",
      "ModelPackageName": "string"
   },
   "Tags": [ 
      { 
         "Key": "string",
         "Value": "string"
      }
   ],
   "VpcConfig": { 
      "SecurityGroupIds": [ "string" ],
      "Subnets": [ "string" ]
   }
}
'''
class Model(BaseObject):

    def __init__(self, model_name,execution_role_arn,  primary_container, vpc_config, containers = [], tags = []):
        self.model_name = model_name
        self.creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.containers = containers
        self.tags = tags
        self.enable_network_isolation = False
        self.vpc_config = vpc_config
        self.primary_container = primary_container
        self.execution_role_arn = execution_role_arn or "arn:test"

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {k: v for k, v in response_object.items() if v is not None and v != [None]}

    @property
    def response_create(self):
        return { "ModelArn": self.execution_role_arn }

'''
{ 
"SecurityGroupIds": [ "string" ],
"Subnets": [ "string" ]
}
'''
class VpcConfig(BaseObject):
    def __init__(self, security_group_ids = [], subnets = []): 
        self.security_group_ids = security_group_ids
        self.subnets = subnets

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {k: v for k, v in response_object.items() if v is not None and v != [None]}


'''
{
    "ContainerHostname": "string",
    "Environment": { 
    "string" : "string" 
    },
    "Image": "string",
    "ModelDataUrl": "string",
    "ModelPackageName": "string"
}
'''
class Container(BaseObject):

    def __init__(self, container_hostname, name, data_url, package_name, image, environment = {}):
        self.container_hostname = container_hostname or "localhost"
        self.model_data_url = data_url
        self.model_package_name = package_name
        self.image = image
        self.environment = environment
    
    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return {k: v for k, v in response_object.items() if v is not None and v != [None]}

class SageMakerBackend(BaseBackend):

    def __init__(self, region_name=None):
        self._models = {}
        self.region_name = region_name

    
    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)
    
    def create_model(self, model):
        model_obj = Model(
            model.get('model_name', 'test'),
            model.get('execution_role_arn', 'arn:test'),
            model.get('primary_container', {}),
            model.get('vpc_config', {}),
            model.get('containers', []),
            model.get('tags', [])
            )

        self._models[model.get('model_name', 'test')] = model_obj
        return model_obj.response_create



    def describe_model(self, model_name=None):
        for model in self._models.values():
            # If a registry_id was supplied, ensure this repository matches            
            if model.model_name != model_name:
                continue
            return model.response_object


sagemaker_backends = {}
for region, ec2_backend in ec2_backends.items():
    sagemaker_backends[region] = SageMakerBackend()