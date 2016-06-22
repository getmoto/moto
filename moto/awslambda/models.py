from __future__ import unicode_literals

import base64
import datetime
import hashlib
import json

import boto.awslambda
from moto.core import BaseBackend
from moto.s3.models import s3_backend
from moto.s3.exceptions import MissingBucket


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
            # validate s3 bucket
            try:
                # FIXME: does not validate bucket region
                key = s3_backend.get_key(self.code['S3Bucket'], self.code['S3Key'])
            except MissingBucket:
                raise ValueError(
                    "InvalidParameterValueException",
                    "Error occurred while GetObject. S3 Error Code: NoSuchBucket. S3 Error Message: The specified bucket does not exist")
            else:
                # validate s3 key
                if key is None:
                    raise ValueError(
                        "InvalidParameterValueException",
                        "Error occurred while GetObject. S3 Error Code: NoSuchKey. S3 Error Message: The specified key does not exist.")
                else:
                    self.code_size = key.size
                    self.code_sha_256 = hashlib.sha256(key.value).hexdigest()
        self.function_arn = 'arn:aws:lambda:123456789012:function:{0}'.format(self.function_name)

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
                "Location": "s3://lambda-functions.aws.amazon.com/{0}".format(self.code['S3Key']),
                "RepositoryType": "S3"
            },
            "Configuration": self.get_configuration(),
        }

    def invoke(self, request, headers):
        payload = dict()

        # Get the invocation type:
        if request.headers.get("x-amz-invocation-type") == "RequestResponse":
            encoded = base64.b64encode("Some log file output...".encode('utf-8'))
            headers["x-amz-log-result"] = encoded.decode('utf-8')

            payload["result"] = "Good"

        return json.dumps(payload, indent=4)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        # required
        spec = {
            'Code': properties['Code'],
            'FunctionName': resource_name,
            'Handler': properties['Handler'],
            'Role': properties['Role'],
            'Runtime': properties['Runtime'],
        }
        optional_properties = 'Description MemorySize Publish Timeout VpcConfig'.split()
        # NOTE: Not doing `properties.get(k, DEFAULT)` to avoid duplicating the default logic
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]

        backend = lambda_backends[region_name]
        fn = backend.create_function(spec)
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
