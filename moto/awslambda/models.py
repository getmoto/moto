from __future__ import unicode_literals

import base64
import datetime
import hashlib
import io
import os
import json
import sys
import zipfile

try:
    from StringIO import StringIO
except:
    from io import StringIO

import boto.awslambda
from moto.core import BaseBackend, BaseModel
from moto.s3.models import s3_backend
from moto.s3.exceptions import MissingBucket, MissingKey


class LambdaFunction(BaseModel):

    def __init__(self, spec, validate_s3=True):
        # required
        self.code = spec['Code']
        self.function_name = spec['FunctionName']
        self.handler = spec['Handler']
        self.role = spec['Role']
        self.run_time = spec['Runtime']

        # optional
        self.description = spec.get('Description', '')
        self.memory_size = spec.get('MemorySize', 128)
        self.publish = spec.get('Publish', False)  # this is ignored currently
        self.timeout = spec.get('Timeout', 3)

        # this isn't finished yet. it needs to find out the VpcId value
        self._vpc_config = spec.get(
            'VpcConfig', {'SubnetIds': [], 'SecurityGroupIds': []})

        # auto-generated
        self.version = '$LATEST'
        self.last_modified = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        if 'ZipFile' in self.code:
            # more hackery to handle unicode/bytes/str in python3 and python2 -
            # argh!
            try:
                to_unzip_code = base64.b64decode(
                    bytes(self.code['ZipFile'], 'utf-8'))
            except Exception:
                to_unzip_code = base64.b64decode(self.code['ZipFile'])

            zbuffer = io.BytesIO()
            zbuffer.write(to_unzip_code)
            zip_file = zipfile.ZipFile(zbuffer, 'r', zipfile.ZIP_DEFLATED)
            self.code = zip_file.read("".join(zip_file.namelist()))
            self.code_size = len(to_unzip_code)
            self.code_sha_256 = hashlib.sha256(to_unzip_code).hexdigest()
        else:
            # validate s3 bucket and key
            key = None
            try:
                # FIXME: does not validate bucket region
                key = s3_backend.get_key(
                    self.code['S3Bucket'], self.code['S3Key'])
            except MissingBucket:
                if do_validate_s3():
                    raise ValueError(
                        "InvalidParameterValueException",
                        "Error occurred while GetObject. S3 Error Code: NoSuchBucket. S3 Error Message: The specified bucket does not exist")
            except MissingKey:
                if do_validate_s3():
                    raise ValueError(
                        "InvalidParameterValueException",
                        "Error occurred while GetObject. S3 Error Code: NoSuchKey. S3 Error Message: The specified key does not exist.")
            if key:
                self.code_size = key.size
                self.code_sha_256 = hashlib.sha256(key.value).hexdigest()
        self.function_arn = 'arn:aws:lambda:123456789012:function:{0}'.format(
            self.function_name)

        self.tags = dict()

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
        if isinstance(self.code, dict):
            return {
                "Code": {
                    "Location": "s3://lambda-functions.aws.amazon.com/{0}".format(self.code['S3Key']),
                    "RepositoryType": "S3"
                },
                "Configuration": self.get_configuration(),
            }
        else:
            return {
                "Configuration": self.get_configuration(),
            }

    def convert(self, s):
        try:
            return str(s, encoding='utf-8')
        except:
            return s

    def is_json(self, test_str):
        try:
            response = json.loads(test_str)
        except:
            response = test_str
        return response

    def _invoke_lambda(self, code, event={}, context={}):
        # TO DO: context not yet implemented
        try:
            mycode = "\n".join(['import json',
                                self.convert(self.code),
                                self.convert('print(json.dumps(lambda_handler(%s, %s)))' % (self.is_json(self.convert(event)), context))])

        except Exception as ex:
            print("Exception %s", ex)

        errored = False
        try:
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            codeOut = StringIO()
            codeErr = StringIO()
            sys.stdout = codeOut
            sys.stderr = codeErr
            exec(mycode)
            exec_err = codeErr.getvalue()
            exec_out = codeOut.getvalue()
            result = self.convert(exec_out.strip())
            if exec_err:
                result = "\n".join([exec_out.strip(), self.convert(exec_err)])
        except Exception as ex:
            errored = True
            result = '%s\n\n\nException %s' % (mycode, ex)
        finally:
            codeErr.close()
            codeOut.close()
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        return self.convert(result), errored

    def invoke(self, body, request_headers, response_headers):
        payload = dict()

        # Get the invocation type:
        res, errored = self._invoke_lambda(code=self.code, event=body)
        if request_headers.get("x-amz-invocation-type") == "RequestResponse":
            encoded = base64.b64encode(res.encode('utf-8'))
            response_headers["x-amz-log-result"] = encoded.decode('utf-8')
            payload['result'] = response_headers["x-amz-log-result"]
            result = res.encode('utf-8')
        else:
            result = json.dumps(payload)
        if errored:
            response_headers['x-amz-function-error'] = "Handled"

        return result

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
        # NOTE: Not doing `properties.get(k, DEFAULT)` to avoid duplicating the
        # default logic
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]

        # when ZipFile is present in CloudFormation, per the official docs,
        # the code it's a plaintext code snippet up to 4096 bytes.
        # this snippet converts this plaintext code to a proper base64-encoded ZIP file.
        if 'ZipFile' in properties['Code']:
            spec['Code']['ZipFile'] = base64.b64encode(
                cls._create_zipfile_from_plaintext_code(spec['Code']['ZipFile']))

        backend = lambda_backends[region_name]
        fn = backend.create_function(spec)
        return fn

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            region = 'us-east-1'
            return 'arn:aws:lambda:{0}:123456789012:function:{1}'.format(region, self.function_name)
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def _create_zipfile_from_plaintext_code(code):
        zip_output = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED)
        zip_file.writestr('lambda_function.zip', code)
        zip_file.close()
        zip_output.seek(0)
        return zip_output.read()


class EventSourceMapping(BaseModel):

    def __init__(self, spec):
        # required
        self.function_name = spec['FunctionName']
        self.event_source_arn = spec['EventSourceArn']
        self.starting_position = spec['StartingPosition']

        # optional
        self.batch_size = spec.get('BatchSize', 100)
        self.enabled = spec.get('Enabled', True)
        self.starting_position_timestamp = spec.get('StartingPositionTimestamp', None)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        spec = {
            'FunctionName': properties['FunctionName'],
            'EventSourceArn': properties['EventSourceArn'],
            'StartingPosition': properties['StartingPosition']
        }
        optional_properties = 'BatchSize Enabled StartingPositionTimestamp'.split()
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]
        return EventSourceMapping(spec)


class LambdaVersion(BaseModel):

    def __init__(self, spec):
        self.version = spec['Version']

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        spec = {
            'Version': properties.get('Version')
        }
        return LambdaVersion(spec)


class LambdaBackend(BaseBackend):

    def __init__(self):
        self._functions = {}

    def has_function(self, function_name):
        return function_name in self._functions

    def has_function_arn(self, function_arn):
        return self.get_function_by_arn(function_arn) is not None

    def create_function(self, spec):
        fn = LambdaFunction(spec)
        self._functions[fn.function_name] = fn
        return fn

    def get_function(self, function_name):
        return self._functions[function_name]

    def get_function_by_arn(self, function_arn):
        for function in self._functions.values():
            if function.function_arn == function_arn:
                return function
        return None

    def delete_function(self, function_name):
        del self._functions[function_name]

    def list_functions(self):
        return self._functions.values()

    def list_tags(self, resource):
        return self.get_function_by_arn(resource).tags

    def tag_resource(self, resource, tags):
        self.get_function_by_arn(resource).tags.update(tags)

    def untag_resource(self, resource, tagKeys):
        function = self.get_function_by_arn(resource)
        for key in tagKeys:
            try:
                del function.tags[key]
            except KeyError:
                pass
                # Don't care


def do_validate_s3():
    return os.environ.get('VALIDATE_LAMBDA_S3', '') in ['', '1', 'true']


lambda_backends = {}
for region in boto.awslambda.regions():
    lambda_backends[region.name] = LambdaBackend()

# Handle us forgotten regions, unless Lambda truly only runs out of US and
for region in ['ap-southeast-2']:
    lambda_backends[region] = LambdaBackend()
