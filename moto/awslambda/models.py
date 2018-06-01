from __future__ import unicode_literals

import base64
from collections import defaultdict
import copy
import datetime
import docker
import docker.errors
import hashlib
import io
import logging
import os
import json
import re
import zipfile
import uuid
import functools
import tarfile
import calendar
import threading
import traceback
import weakref
import requests.adapters

import boto.awslambda
from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.core.utils import unix_time_millis
from moto.s3.models import s3_backend
from moto.logs.models import logs_backends
from moto.s3.exceptions import MissingBucket, MissingKey
from moto import settings
from .utils import make_function_arn

logger = logging.getLogger(__name__)

ACCOUNT_ID = '123456789012'


try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory


_stderr_regex = re.compile(r'START|END|REPORT RequestId: .*')
_orig_adapter_send = requests.adapters.HTTPAdapter.send
docker_3 = docker.__version__.startswith("3")


def zip2tar(zip_bytes):
    with TemporaryDirectory() as td:
        tarname = os.path.join(td, 'data.tar')
        timeshift = int((datetime.datetime.now() -
                     datetime.datetime.utcnow()).total_seconds())
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zipf, \
                tarfile.TarFile(tarname, 'w') as tarf:
            for zipinfo in zipf.infolist():
                if zipinfo.filename[-1] == '/':  # is_dir() is py3.6+
                    continue

                tarinfo = tarfile.TarInfo(name=zipinfo.filename)
                tarinfo.size = zipinfo.file_size
                tarinfo.mtime = calendar.timegm(zipinfo.date_time) - timeshift
                infile = zipf.open(zipinfo.filename)
                tarf.addfile(tarinfo, infile)

        with open(tarname, 'rb') as f:
            tar_data = f.read()
            return tar_data


class _VolumeRefCount:
    __slots__ = "refcount", "volume"

    def __init__(self, refcount, volume):
        self.refcount = refcount
        self.volume = volume


class _DockerDataVolumeContext:
    _data_vol_map = defaultdict(lambda: _VolumeRefCount(0, None))  # {sha256: _VolumeRefCount}
    _lock = threading.Lock()

    def __init__(self, lambda_func):
        self._lambda_func = lambda_func
        self._vol_ref = None

    @property
    def name(self):
        return self._vol_ref.volume.name

    def __enter__(self):
        # See if volume is already known
        with self.__class__._lock:
            self._vol_ref = self.__class__._data_vol_map[self._lambda_func.code_sha_256]
            self._vol_ref.refcount += 1
            if self._vol_ref.refcount > 1:
                return self

            # See if the volume already exists
            for vol in self._lambda_func.docker_client.volumes.list():
                if vol.name == self._lambda_func.code_sha_256:
                    self._vol_ref.volume = vol
                    return self

            # It doesn't exist so we need to create it
            self._vol_ref.volume = self._lambda_func.docker_client.volumes.create(self._lambda_func.code_sha_256)
            if docker_3:
                volumes = {self.name: {'bind': '/tmp/data', 'mode': 'rw'}}
            else:
                volumes = {self.name: '/tmp/data'}
            container = self._lambda_func.docker_client.containers.run('alpine', 'sleep 100', volumes=volumes, detach=True)
            try:
                tar_bytes = zip2tar(self._lambda_func.code_bytes)
                container.put_archive('/tmp/data', tar_bytes)
            finally:
                container.remove(force=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.__class__._lock:
            self._vol_ref.refcount -= 1
            if self._vol_ref.refcount == 0:
                try:
                    self._vol_ref.volume.remove()
                except docker.errors.APIError as e:
                    if e.status_code != 409:
                        raise

                    raise  # multiple processes trying to use same volume?


class LambdaFunction(BaseModel):
    def __init__(self, spec, region, validate_s3=True, version=1):
        # required
        self.region = region
        self.code = spec['Code']
        self.function_name = spec['FunctionName']
        self.handler = spec['Handler']
        self.role = spec['Role']
        self.run_time = spec['Runtime']
        self.logs_backend = logs_backends[self.region]
        self.environment_vars = spec.get('Environment', {}).get('Variables', {})
        self.docker_client = docker.from_env()
        self.policy = ""

        # Unfortunately mocking replaces this method w/o fallback enabled, so we
        # need to replace it if we detect it's been mocked
        if requests.adapters.HTTPAdapter.send != _orig_adapter_send:
            _orig_get_adapter = self.docker_client.api.get_adapter

            def replace_adapter_send(*args, **kwargs):
                adapter = _orig_get_adapter(*args, **kwargs)

                if isinstance(adapter, requests.adapters.HTTPAdapter):
                    adapter.send = functools.partial(_orig_adapter_send, adapter)
                return adapter
            self.docker_client.api.get_adapter = replace_adapter_send

        # optional
        self.description = spec.get('Description', '')
        self.memory_size = spec.get('MemorySize', 128)
        self.publish = spec.get('Publish', False)  # this is ignored currently
        self.timeout = spec.get('Timeout', 3)

        self.logs_group_name = '/aws/lambda/{}'.format(self.function_name)
        self.logs_backend.ensure_log_group(self.logs_group_name, [])

        # this isn't finished yet. it needs to find out the VpcId value
        self._vpc_config = spec.get(
            'VpcConfig', {'SubnetIds': [], 'SecurityGroupIds': []})

        # auto-generated
        self.version = version
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

            self.code_bytes = to_unzip_code
            self.code_size = len(to_unzip_code)
            self.code_sha_256 = hashlib.sha256(to_unzip_code).hexdigest()

            # TODO: we should be putting this in a lambda bucket
            self.code['UUID'] = str(uuid.uuid4())
            self.code['S3Key'] = '{}-{}'.format(self.function_name, self.code['UUID'])
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
                self.code_bytes = key.value
                self.code_size = key.size
                self.code_sha_256 = hashlib.sha256(key.value).hexdigest()

        self.function_arn = make_function_arn(self.region, ACCOUNT_ID, self.function_name, version)

        self.tags = dict()

    def set_version(self, version):
        self.function_arn = make_function_arn(self.region, ACCOUNT_ID, self.function_name, version)
        self.version = version
        self.last_modified = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    @property
    def vpc_config(self):
        config = self._vpc_config.copy()
        if config['SecurityGroupIds']:
            config.update({"VpcId": "vpc-123abc"})
        return config

    def __repr__(self):
        return json.dumps(self.get_configuration())

    def get_configuration(self):
        config = {
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
            "Version": str(self.version),
            "VpcConfig": self.vpc_config,
        }

        if self.environment_vars:
            config['Environment'] = {
                'Variables': self.environment_vars
            }

        return config

    def get_code(self):
        return {
            "Code": {
                "Location": "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com/{1}".format(self.region, self.code['S3Key']),
                "RepositoryType": "S3"
            },
            "Configuration": self.get_configuration(),
        }

    @staticmethod
    def convert(s):
        try:
            return str(s, encoding='utf-8')
        except Exception:
            return s

    @staticmethod
    def is_json(test_str):
        try:
            response = json.loads(test_str)
        except Exception:
            response = test_str
        return response

    def _invoke_lambda(self, code, event=None, context=None):
        # TODO: context not yet implemented
        if event is None:
            event = dict()
        if context is None:
            context = {}

        try:
            # TODO: I believe we can keep the container running and feed events as needed
            #       also need to hook it up to the other services so it can make kws/s3 etc calls
            #  Should get invoke_id /RequestId from invovation
            env_vars = {
                "AWS_LAMBDA_FUNCTION_TIMEOUT": self.timeout,
                "AWS_LAMBDA_FUNCTION_NAME": self.function_name,
                "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": self.memory_size,
                "AWS_LAMBDA_FUNCTION_VERSION": self.version,
                "AWS_REGION": self.region,
            }

            env_vars.update(self.environment_vars)

            container = output = exit_code = None
            with _DockerDataVolumeContext(self) as data_vol:
                try:
                    run_kwargs = dict(links={'motoserver': 'motoserver'}) if settings.TEST_SERVER_MODE else {}
                    container = self.docker_client.containers.run(
                        "lambci/lambda:{}".format(self.run_time),
                        [self.handler, json.dumps(event)], remove=False,
                        mem_limit="{}m".format(self.memory_size),
                        volumes=["{}:/var/task".format(data_vol.name)], environment=env_vars, detach=True, **run_kwargs)
                finally:
                    if container:
                        try:
                            exit_code = container.wait(timeout=300)
                        except requests.exceptions.ReadTimeout:
                            exit_code = -1
                            container.stop()
                            container.kill()
                        else:
                            if docker_3:
                                exit_code = exit_code['StatusCode']

                        output = container.logs(stdout=False, stderr=True)
                        output += container.logs(stdout=True, stderr=False)
                        container.remove()

            output = output.decode('utf-8')

            # Send output to "logs" backend
            invoke_id = uuid.uuid4().hex
            log_stream_name = "{date.year}/{date.month:02d}/{date.day:02d}/[{version}]{invoke_id}".format(
                date=datetime.datetime.utcnow(), version=self.version, invoke_id=invoke_id
            )

            self.logs_backend.create_log_stream(self.logs_group_name, log_stream_name)

            log_events = [{'timestamp': unix_time_millis(), "message": line}
                          for line in output.splitlines()]
            self.logs_backend.put_log_events(self.logs_group_name, log_stream_name, log_events, None)

            if exit_code != 0:
                raise Exception(
                    'lambda invoke failed output: {}'.format(output))

            # strip out RequestId lines
            output = os.linesep.join([line for line in self.convert(output).splitlines() if not _stderr_regex.match(line)])
            return output, False
        except BaseException as e:
            traceback.print_exc()
            return "error running lambda: {}".format(e), True

    def invoke(self, body, request_headers, response_headers):
        payload = dict()

        if body:
            body = json.loads(body)

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
            return make_function_arn(self.region, ACCOUNT_ID, self.function_name)
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

    def __repr__(self):
        return str(self.logical_resource_id)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json,
                                        region_name):
        properties = cloudformation_json['Properties']
        spec = {
            'Version': properties.get('Version')
        }
        return LambdaVersion(spec)


class LambdaStorage(object):
    def __init__(self):
        # Format 'func_name' {'alias': {}, 'versions': []}
        self._functions = {}
        self._arns = weakref.WeakValueDictionary()

    def _get_latest(self, name):
        return self._functions[name]['latest']

    def _get_version(self, name, version):
        index = version - 1

        try:
            return self._functions[name]['versions'][index]
        except IndexError:
            return None

    def _get_alias(self, name, alias):
        return self._functions[name]['alias'].get(alias, None)

    def get_function(self, name, qualifier=None):
        if name not in self._functions:
            return None

        if qualifier is None:
            return self._get_latest(name)

        try:
            return self._get_version(name, int(qualifier))
        except ValueError:
            return self._functions[name]['latest']

    def get_arn(self, arn):
        return self._arns.get(arn, None)

    def put_function(self, fn):
        """
        :param fn: Function
        :type fn: LambdaFunction
        """
        if fn.function_name in self._functions:
            self._functions[fn.function_name]['latest'] = fn
        else:
            self._functions[fn.function_name] = {
                'latest': fn,
                'versions': [],
                'alias': weakref.WeakValueDictionary()
            }

        self._arns[fn.function_arn] = fn

    def publish_function(self, name):
        if name not in self._functions:
            return None
        if not self._functions[name]['latest']:
            return None

        new_version = len(self._functions[name]['versions']) + 1
        fn = copy.copy(self._functions[name]['latest'])
        fn.set_version(new_version)

        self._functions[name]['versions'].append(fn)
        return fn

    def del_function(self, name, qualifier=None):
        if name in self._functions:
            if not qualifier:
                # Something is still reffing this so delete all arns
                latest = self._functions[name]['latest'].function_arn
                del self._arns[latest]

                for fn in self._functions[name]['versions']:
                    del self._arns[fn.function_arn]

                del self._functions[name]

                return True

            elif qualifier == '$LATEST':
                self._functions[name]['latest'] = None

                # If theres no functions left
                if not self._functions[name]['versions'] and not self._functions[name]['latest']:
                    del self._functions[name]

                return True

            else:
                fn = self.get_function(name, qualifier)
                if fn:
                    self._functions[name]['versions'].remove(fn)

                    # If theres no functions left
                    if not self._functions[name]['versions'] and not self._functions[name]['latest']:
                        del self._functions[name]

                    return True

        return False

    def all(self):
        result = []

        for function_group in self._functions.values():
            if function_group['latest'] is not None:
                result.append(function_group['latest'])

            result.extend(function_group['versions'])

        return result


class LambdaBackend(BaseBackend):
    def __init__(self, region_name):
        self._lambdas = LambdaStorage()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_function(self, spec):
        function_name = spec.get('FunctionName', None)
        if function_name is None:
            raise RESTError('InvalidParameterValueException', 'Missing FunctionName')

        fn = LambdaFunction(spec, self.region_name, version='$LATEST')

        self._lambdas.put_function(fn)

        return fn

    def publish_function(self, function_name):
        return self._lambdas.publish_function(function_name)

    def get_function(self, function_name, qualifier=None):
        return self._lambdas.get_function(function_name, qualifier)

    def get_function_by_arn(self, function_arn):
        return self._lambdas.get_arn(function_arn)

    def delete_function(self, function_name, qualifier=None):
        return self._lambdas.del_function(function_name, qualifier)

    def list_functions(self):
        return self._lambdas.all()

    def send_message(self, function_name, message, subject=None, qualifier=None):
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
                        "Subject": subject or "TestInvoke"
                    }
                }
            ]

        }
        func = self._lambdas.get_function(function_name, qualifier)
        func.invoke(json.dumps(event), {}, {})

    def list_tags(self, resource):
        return self.get_function_by_arn(resource).tags

    def tag_resource(self, resource, tags):
        fn = self.get_function_by_arn(resource)
        if not fn:
            return False

        fn.tags.update(tags)
        return True

    def untag_resource(self, resource, tagKeys):
        fn = self.get_function_by_arn(resource)
        if fn:
            for key in tagKeys:
                try:
                    del fn.tags[key]
                except KeyError:
                    pass
                    # Don't care
            return True
        return False

    def add_policy(self, function_name, policy):
        self.get_function(function_name).policy = policy


def do_validate_s3():
    return os.environ.get('VALIDATE_LAMBDA_S3', '') in ['', '1', 'true']


# Handle us forgotten regions, unless Lambda truly only runs out of US and
lambda_backends = {_region.name: LambdaBackend(_region.name)
                   for _region in boto.awslambda.regions()}

lambda_backends['ap-southeast-2'] = LambdaBackend('ap-southeast-2')
lambda_backends['us-gov-west-1'] = LambdaBackend('us-gov-west-1')
