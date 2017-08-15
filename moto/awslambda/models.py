from __future__ import unicode_literals

import base64
import datetime
import hashlib
import io
import logging
import os
import json
import tempfile
import zipfile
import uuid

try:
    from StringIO import StringIO
except:
    from io import StringIO

import boto.awslambda
from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time_millis
from moto.s3.models import s3_backend
from moto.logs.models import logs_backends
from moto.s3.exceptions import MissingBucket, MissingKey
import subprocess

logger = logging.getLogger(__name__)


class LambdaFunction(BaseModel):
    def __init__(self, spec, region, validate_s3=True):
        # required
        self.region = region
        self.code = spec['Code']
        self.function_name = spec['FunctionName']
        self.handler = spec['Handler']
        self.role = spec['Role']
        self.run_time = spec['Runtime']
        self.logs_backend = logs_backends[self.region]

        # optional
        self.description = spec.get('Description', '')
        self.memory_size = spec.get('MemorySize', 128)
        self.publish = spec.get('Publish', False)  # this is ignored currently
        self.timeout = spec.get('Timeout', 3)

        self.logs_group_name = '/aws/lambda/{}'.format(self.function_name)
        self.logs_backend.create_log_group(self.logs_group_name, [])


        # this isn't finished yet. it needs to find out the VpcId value
        self._vpc_config = spec.get(
            'VpcConfig', {'SubnetIds': [], 'SecurityGroupIds': []})

        # auto-generated
        self.version = '$LATEST'
        self.last_modified = datetime.datetime.utcnow().strftime(
            '%Y-%m-%d %H:%M:%S')
        if 'ZipFile' in self.code:
            # more hackery to handle unicode/bytes/str in python3 and python2 -
            # argh!
            try:
                to_unzip_code = base64.b64decode(
                    bytes(self.code['ZipFile'], 'utf-8'))
            except Exception:
                to_unzip_code = base64.b64decode(self.code['ZipFile'])

            self.code = to_unzip_code
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
        self.function_arn = 'arn:aws:lambda:{}:123456789012:function:{}'.format(
            self.region, self.function_name)

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
                "Location": "s3://lambda-functions.aws.amazon.com/{0}".format(
                    self.code['S3Key']),
                "RepositoryType": "S3"
            },
            "Configuration": self.get_configuration(),
        }

    @staticmethod
    def convert(s):
        try:
            return str(s, encoding='utf-8')
        except:
            return s

    @staticmethod
    def is_json(test_str):
        try:
            response = json.loads(test_str)
        except:
            response = test_str
        return response

    def _invoke_lambda(self, code, event=None, context=None):
        # TODO: context not yet implemented
        # TODO: switch to docker python API
        if event is None:
            event = dict()
        if context is None:
            context = {}

        with tempfile.TemporaryDirectory() as td, \
                zipfile.ZipFile(io.BytesIO(self.code)) as zf:
            zf.extractall(td)

            if td.startswith("/var/folders/"):
                td = td.replace("/var/folders/", "/private/var/folders/")

            try:
                # TODO: I believe we can keep the container running and feed events as needed
                #       also need to hook it up to the other services so it can make kws/s3 etc calls
                #  Should get invoke_id /RequestId from invovation

                proc = subprocess.run([
                    "docker", "run", "--rm", "-i",
                     "-e", "AWS_LAMBDA_FUNCTION_TIMEOUT={}".format(self.timeout),
                     "-e", "AWS_LAMBDA_FUNCTION_NAME={}".format(self.function_name),
                     "-e", "AWS_LAMBDA_FUNCTION_MEMORY_SIZE={}".format(self.memory_size),
                     "-e", "AWS_LAMBDA_FUNCTION_VERSION={}".format(self.version),
                     "-e", "AWS_REGION={}".format(self.region),
                     "-m", "{}m".format(self.memory_size),
                     "-v",
                     "{}:/var/task".format(td),
                     "lambci/lambda:{}".format(
                         self.run_time),
                     self.handler,
                     json.dumps(event)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                stdout = proc.stdout.decode('utf-8')
                stderr =  proc.stderr.decode('utf-8')

                # Send output to "logs" backend
                invoke_id = uuid.uuid4().hex
                log_stream_name = "{date.year}/{date.month:02d}/{date.day:02d}/[{version}]{invoke_id}".format(
                    date=datetime.datetime.utcnow(), version=self.version, invoke_id=invoke_id
                )

                self.logs_backend.create_log_stream(self.logs_group_name, log_stream_name)

                log_events = [{'timestamp': unix_time_millis(), "message": line}
                              for line in stderr.splitlines()]
                self.logs_backend.put_log_events(self.logs_group_name, log_stream_name, log_events, None)

                output = self.convert(stdout)
                self.logs_backend.put_log_events(self.logs_group_name, log_stream_name, [{'timestamp': unix_time_millis(), "message": output}], None)

                if proc.returncode != 0:
                    raise Exception(
                        'Ran: {} output: {} {} failed'.format(args, proc.stdout,
                                                              proc.stderr))

                self.logs_backend.put_log_events(self.logs_group_name, log_stream_name, [{'timestamp': unix_time_millis(), "message": output}], None)

                return output, False
            except BaseException as e:
                return "error running lambda: {}".format(e), True

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
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json,
                                        region_name):
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
                cls._create_zipfile_from_plaintext_code(
                    spec['Code']['ZipFile']))

        backend = lambda_backends[region_name]
        fn = backend.create_function(spec)
        return fn

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import \
            UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            return 'arn:aws:lambda:{0}:123456789012:function:{1}'.format(
                self.region, self.function_name)
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
        self.starting_position_timestamp = spec.get('StartingPositionTimestamp',
                                                    None)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json,
                                        region_name):
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
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json,
                                        region_name):
        properties = cloudformation_json['Properties']
        spec = {
            'Version': properties.get('Version')
        }
        return LambdaVersion(spec)


class LambdaBackend(BaseBackend):
    def __init__(self, region):
        self._functions = {}
        self._region = region

    def has_function(self, function_name):
        return function_name in self._functions

    def create_function(self, spec):
        fn = LambdaFunction(spec, self._region)
        self._functions[fn.function_name] = fn
        return fn

    def get_function(self, function_name):
        return self._functions[function_name]

    def delete_function(self, function_name):
        del self._functions[function_name]

    def list_functions(self):
        return self._functions.values()

    def send_message(self, function_name, message):
        event = {
            "Records": [
                {
                    "EventVersion": "1.0",
                    "EventSubscriptionArn": "arn:aws:sns:EXAMPLE",
                    "EventSource": "aws:sns",
                    "Sns": {
                        "SignatureVersion": "1",
                        "Timestamp": "1970-01-01T00:00:00.000Z",
                        "Signature": "EXAMPLE",
                        "SigningCertUrl": "EXAMPLE",
                        "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
                        "Message": message,
                        "MessageAttributes": {
                            "Test": {
                                "Type": "String",
                                "Value": "TestString"
                            },
                            "TestBinary": {
                                "Type": "Binary",
                                "Value": "TestBinary"
                            }
                        },
                        "Type": "Notification",
                        "UnsubscribeUrl": "EXAMPLE",
                        "TopicArn": "arn:aws:sns:EXAMPLE",
                        "Subject": "TestInvoke"
                    }
                }
            ]

        }
        self._functions[function_name].invoke(event, {}, {})
        pass


def do_validate_s3():
    return os.environ.get('VALIDATE_LAMBDA_S3', '') in ['', '1', 'true']


# Handle us forgotten regions, unless Lambda truly only runs out of US and
lambda_backends = {_region.name: LambdaBackend(_region.name)
                   for _region in boto.awslambda.regions()}

lambda_backends['ap-southeast-2'] = LambdaBackend('ap-southeast-2')