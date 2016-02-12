from __future__ import unicode_literals

import datetime
import boto.awslambda
from moto.core import BaseBackend


class LambdaFunction(object):

    def __init__(self, spec):
        self.function_name = spec['FunctionName']
        self.run_time = spec['Runtime']
        self.role = spec['Role']
        self.handler = spec['Handler']
        self.description = spec['Description']
        self.timeout = spec['Timeout']
        self.memory_size = spec['MemorySize']
        self.vpc_config = spec.get('VpcConfig', {})
        self.code = spec['Code']

        self.version = '$LATEST'
        self.last_modified = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        self.code_size = 210  # hello world function
        self.code_sha_256 = 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9' # hello world function
        self.function_arn = 'arn:aws:lambda:123456789012:function:{}'.format(self.function_name)

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
