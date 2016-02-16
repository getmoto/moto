from __future__ import unicode_literals

import base64
import datetime
import hashlib

import boto.awslambda
from moto.core import BaseBackend


class LambdaFunction(object):

    def __init__(self, spec):
        # required
        self.code = spec['Code']
        self.function_name = spec['FunctionName']
        self.handler = spec['Handler']
        self.role = spec['Role']
        self.run_time = spec['Runtime']

        # optional
        self.description = spec.get('Description', '')
        self.memory_size = spec.get('MemorySize', 128)
        self.publish = spec.get('Publish', False) # this is ignored currently
        self.timeout = spec.get('Timeout', 3)

        # this isn't finished yet. it needs to find out the VpcId value
        self._vpc_config = spec.get('VpcConfig', {'SubnetIds': [], 'SecurityGroupIds': []})

        # auto-generated
        self.version = '$LATEST'
        self.last_modified = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        if 'ZipFile' in self.code:
            code = base64.b64decode(self.code['ZipFile'])
            self.code_size = len(code)
            self.code_sha_256 = hashlib.sha256(code).hexdigest()
        else:
            self.code_size = 123
            self.code_sha_256 = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        self.function_arn = 'arn:aws:lambda:123456789012:function:{}'.format(self.function_name)

    @property
    def vpc_config(self):
        config = self._vpc_config.copy()
        if config['SecurityGroupIds']:
            config.update({"VpcId": "vpc-123abc"})
        return config

    def __repr__(self):
        return json.dumps(self.get_configuration())

    def get_configuration(self):
        return {
            "CodeSha256": self.code_sha_256,
            "CodeSize": self.code_size,
            "Description": self.description,
            "FunctionArn": self.function_arn,
            "FunctionName": self.function_name,
            "Handler": self.handler,
            "LastModified": self.last_modified,
            "MemorySize": self.memory_size,
            "Role": self.role,
            "Runtime": self.run_time,
            "Timeout": self.timeout,
            "Version": self.version,
            "VpcConfig": self.vpc_config,
        }

    def get_code(self):
        return {
            "Code": {
                "Location": "s3://lambda-functions.aws.amazon.com/{}".format(self.code['S3Key']),
                "RepositoryType": "S3"
            },
            "Configuration": self.get_configuration(),
        }

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        backend = lambda_backends[region_name]
        fn = backend.create_function({
            # required
            'Code': properties['Code'],
            'FunctionName': resource_name,
            'Handler': properties['Handler'],
            'Role': properties['Role'],
            'Runtime': properties['Runtime'],

            # optional
            'Description': properties.get('Description', ''),
            'MemorySize': properties.get('MemorySize', 128),
            'Publish': properties.get('Publish', False),
            'Timeout': properties.get('Timeout', 3),
            'VpcConfig': properties.get('VpcConfig', {}),
        })
        return fn


class LambdaBackend(BaseBackend):

    def __init__(self):
        self._functions = {}
    
    def has_function(self, function_name):
        return function_name in self._functions

    def create_function(self, spec):
        fn = LambdaFunction(spec)
        self._functions[fn.function_name] = fn
        return fn

    def get_function(self, function_name):
        return self._functions[function_name]

    def delete_function(self, function_name):
        del self._functions[function_name]

    def list_functions(self):
        return self._functions.values()


lambda_backends = {}
for region in boto.awslambda.regions():
    lambda_backends[region.name] = LambdaBackend()
