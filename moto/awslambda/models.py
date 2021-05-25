from __future__ import unicode_literals

import base64
import time
from collections import defaultdict
import copy
import datetime
from gzip import GzipFile

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
import tarfile
import calendar
import threading
import weakref
import requests.exceptions

from boto3 import Session

from moto.awslambda.policy import Policy
from moto.core import BaseBackend, CloudFormationModel
from moto.core.exceptions import RESTError
from moto.iam.models import iam_backend
from moto.iam.exceptions import IAMNotFoundException
from moto.core.utils import unix_time_millis
from moto.s3.models import s3_backend
from moto.logs.models import logs_backends
from moto.s3.exceptions import MissingBucket, MissingKey
from moto import settings
from .exceptions import (
    CrossAccountNotAllowed,
    InvalidRoleFormat,
    InvalidParameterValueException,
)
from .utils import (
    make_function_arn,
    make_function_ver_arn,
    make_layer_arn,
    make_layer_ver_arn,
    split_layer_arn,
)
from moto.sqs import sqs_backends
from moto.dynamodb2 import dynamodb_backends2
from moto.dynamodbstreams import dynamodbstreams_backends
from moto.core import ACCOUNT_ID
from moto.utilities.docker_utilities import DockerModel, parse_image_ref

logger = logging.getLogger(__name__)

try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory

docker_3 = docker.__version__[0] >= "3"


def zip2tar(zip_bytes):
    with TemporaryDirectory() as td:
        tarname = os.path.join(td, "data.tar")
        timeshift = int(
            (datetime.datetime.now() - datetime.datetime.utcnow()).total_seconds()
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf, tarfile.TarFile(
            tarname, "w"
        ) as tarf:
            for zipinfo in zipf.infolist():
                if zipinfo.filename[-1] == "/":  # is_dir() is py3.6+
                    continue

                tarinfo = tarfile.TarInfo(name=zipinfo.filename)
                tarinfo.size = zipinfo.file_size
                tarinfo.mtime = calendar.timegm(zipinfo.date_time) - timeshift
                infile = zipf.open(zipinfo.filename)
                tarf.addfile(tarinfo, infile)

        with open(tarname, "rb") as f:
            tar_data = f.read()
            return tar_data


class _VolumeRefCount:
    __slots__ = "refcount", "volume"

    def __init__(self, refcount, volume):
        self.refcount = refcount
        self.volume = volume


class _DockerDataVolumeContext:
    _data_vol_map = defaultdict(
        lambda: _VolumeRefCount(0, None)
    )  # {sha256: _VolumeRefCount}
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
            self._vol_ref.volume = self._lambda_func.docker_client.volumes.create(
                self._lambda_func.code_sha_256
            )
            if docker_3:
                volumes = {self.name: {"bind": "/tmp/data", "mode": "rw"}}
            else:
                volumes = {self.name: "/tmp/data"}
            self._lambda_func.docker_client.images.pull(
                ":".join(parse_image_ref("alpine"))
            )
            container = self._lambda_func.docker_client.containers.run(
                "alpine", "sleep 100", volumes=volumes, detach=True
            )
            try:
                tar_bytes = zip2tar(self._lambda_func.code_bytes)
                container.put_archive("/tmp/data", tar_bytes)
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


def _zipfile_content(zipfile):
    # more hackery to handle unicode/bytes/str in python3 and python2 -
    # argh!
    try:
        to_unzip_code = base64.b64decode(bytes(zipfile, "utf-8"))
    except Exception:
        to_unzip_code = base64.b64decode(zipfile)

    return to_unzip_code, len(to_unzip_code), hashlib.sha256(to_unzip_code).hexdigest()


def _validate_s3_bucket_and_key(data):
    key = None
    try:
        # FIXME: does not validate bucket region
        key = s3_backend.get_object(data["S3Bucket"], data["S3Key"])
    except MissingBucket:
        if do_validate_s3():
            raise InvalidParameterValueException(
                "Error occurred while GetObject. S3 Error Code: NoSuchBucket. S3 Error Message: The specified bucket does not exist"
            )
    except MissingKey:
        if do_validate_s3():
            raise ValueError(
                "InvalidParameterValueException",
                "Error occurred while GetObject. S3 Error Code: NoSuchKey. S3 Error Message: The specified key does not exist.",
            )
    return key


class Permission(CloudFormationModel):
    def __init__(self, region):
        self.region = region

    @staticmethod
    def cloudformation_name_type():
        return "Permission"

    @staticmethod
    def cloudformation_type():
        return "AWS::Lambda::Permission"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        backend = lambda_backends[region_name]
        fn = backend.get_function(properties["FunctionName"])
        fn.policy.add_statement(raw=json.dumps(properties))
        return Permission(region=region_name)


class LayerVersion(CloudFormationModel):
    def __init__(self, spec, region):
        # required
        self.region = region
        self.name = spec["LayerName"]
        self.content = spec["Content"]

        # optional
        self.description = spec.get("Description", "")
        self.compatible_runtimes = spec.get("CompatibleRuntimes", [])
        self.license_info = spec.get("LicenseInfo", "")

        # auto-generated
        self.created_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.version = None
        self._attached = False
        self._layer = None

        if "ZipFile" in self.content:
            self.code_bytes, self.code_size, self.code_sha_256 = _zipfile_content(
                self.content["ZipFile"]
            )
        else:
            key = _validate_s3_bucket_and_key(self.content)
            if key:
                self.code_bytes = key.value
                self.code_size = key.size
                self.code_sha_256 = hashlib.sha256(key.value).hexdigest()

    @property
    def arn(self):
        if self.version:
            return make_layer_ver_arn(self.region, ACCOUNT_ID, self.name, self.version)
        raise ValueError("Layer version is not set")

    def attach(self, layer, version):
        self._attached = True
        self._layer = layer
        self.version = version

    def get_layer_version(self):
        return {
            "Version": self.version,
            "LayerVersionArn": self.arn,
            "CreatedDate": self.created_date,
            "CompatibleRuntimes": self.compatible_runtimes,
            "Description": self.description,
            "LicenseInfo": self.license_info,
        }

    @staticmethod
    def cloudformation_name_type():
        return "LayerVersion"

    @staticmethod
    def cloudformation_type():
        return "AWS::Lambda::LayerVersion"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        optional_properties = (
            "Description",
            "CompatibleRuntimes",
            "LicenseInfo",
        )

        # required
        spec = {
            "Content": properties["Content"],
            "LayerName": resource_name,
        }
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]

        backend = lambda_backends[region_name]
        layer_version = backend.publish_layer_version(spec)
        return layer_version


class Layer(object):
    def __init__(self, name, region):
        self.region = region
        self.name = name

        self.layer_arn = make_layer_arn(region, ACCOUNT_ID, self.name)
        self._latest_version = 0
        self.layer_versions = {}

    def attach_version(self, layer_version):
        self._latest_version += 1
        layer_version.attach(self, self._latest_version)
        self.layer_versions[str(self._latest_version)] = layer_version

    def to_dict(self):
        return {
            "LayerName": self.name,
            "LayerArn": self.layer_arn,
            "LatestMatchingVersion": self.layer_versions[
                str(self._latest_version)
            ].get_layer_version(),
        }


class LambdaFunction(CloudFormationModel, DockerModel):
    def __init__(self, spec, region, validate_s3=True, version=1):
        DockerModel.__init__(self)
        # required
        self.region = region
        self.code = spec["Code"]
        self.function_name = spec["FunctionName"]
        self.handler = spec["Handler"]
        self.role = spec["Role"]
        self.run_time = spec["Runtime"]
        self.logs_backend = logs_backends[self.region]
        self.environment_vars = spec.get("Environment", {}).get("Variables", {})
        self.policy = None
        self.state = "Active"
        self.reserved_concurrency = spec.get("ReservedConcurrentExecutions", None)

        # optional
        self.description = spec.get("Description", "")
        self.memory_size = spec.get("MemorySize", 128)
        self.publish = spec.get("Publish", False)  # this is ignored currently
        self.timeout = spec.get("Timeout", 3)
        self.layers = self._get_layers_data(spec.get("Layers", []))

        self.logs_group_name = "/aws/lambda/{}".format(self.function_name)

        # this isn't finished yet. it needs to find out the VpcId value
        self._vpc_config = spec.get(
            "VpcConfig", {"SubnetIds": [], "SecurityGroupIds": []}
        )

        # auto-generated
        self.version = version
        self.last_modified = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if "ZipFile" in self.code:
            self.code_bytes, self.code_size, self.code_sha_256 = _zipfile_content(
                self.code["ZipFile"]
            )

            # TODO: we should be putting this in a lambda bucket
            self.code["UUID"] = str(uuid.uuid4())
            self.code["S3Key"] = "{}-{}".format(self.function_name, self.code["UUID"])
        else:
            key = _validate_s3_bucket_and_key(self.code)
            if key:
                self.code_bytes = key.value
                self.code_size = key.size
                self.code_sha_256 = hashlib.sha256(key.value).hexdigest()
            else:
                self.code_bytes = ""
                self.code_size = 0
                self.code_sha_256 = ""

        self.function_arn = make_function_arn(
            self.region, ACCOUNT_ID, self.function_name
        )

        self.tags = dict()

    def set_version(self, version):
        self.function_arn = make_function_ver_arn(
            self.region, ACCOUNT_ID, self.function_name, version
        )
        self.version = version
        self.last_modified = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def vpc_config(self):
        config = self._vpc_config.copy()
        if config["SecurityGroupIds"]:
            config.update({"VpcId": "vpc-123abc"})
        return config

    @property
    def physical_resource_id(self):
        return self.function_name

    def __repr__(self):
        return json.dumps(self.get_configuration())

    def _get_layers_data(self, layers_versions_arns):
        backend = lambda_backends[self.region]
        layer_versions = [
            backend.layers_versions_by_arn(layer_version)
            for layer_version in layers_versions_arns
        ]
        if not all(layer_versions):
            raise ValueError(
                "InvalidParameterValueException",
                "One or more LayerVersion does not exist {0}".format(
                    layers_versions_arns
                ),
            )
        return [{"Arn": lv.arn, "CodeSize": lv.code_size} for lv in layer_versions]

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
            "State": self.state,
            "Timeout": self.timeout,
            "Version": str(self.version),
            "VpcConfig": self.vpc_config,
            "Layers": self.layers,
        }
        if self.environment_vars:
            config["Environment"] = {"Variables": self.environment_vars}

        return config

    def get_code(self):
        code = {
            "Code": {
                "Location": "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com/{1}".format(
                    self.region, self.code["S3Key"]
                ),
                "RepositoryType": "S3",
            },
            "Configuration": self.get_configuration(),
        }
        if self.reserved_concurrency:
            code.update(
                {
                    "Concurrency": {
                        "ReservedConcurrentExecutions": self.reserved_concurrency
                    }
                }
            )
        return code

    def update_configuration(self, config_updates):
        for key, value in config_updates.items():
            if key == "Description":
                self.description = value
            elif key == "Handler":
                self.handler = value
            elif key == "MemorySize":
                self.memory_size = value
            elif key == "Role":
                self.role = value
            elif key == "Runtime":
                self.run_time = value
            elif key == "Timeout":
                self.timeout = value
            elif key == "VpcConfig":
                self._vpc_config = value
            elif key == "Environment":
                self.environment_vars = value["Variables"]
            elif key == "Layers":
                self.layers = self._get_layers_data(value)

        return self.get_configuration()

    def update_function_code(self, updated_spec):
        if "DryRun" in updated_spec and updated_spec["DryRun"]:
            return self.get_configuration()

        if "ZipFile" in updated_spec:
            self.code["ZipFile"] = updated_spec["ZipFile"]

            # using the "hackery" from __init__ because it seems to work
            # TODOs and FIXMEs included, because they'll need to be fixed
            # in both places now
            try:
                to_unzip_code = base64.b64decode(
                    bytes(updated_spec["ZipFile"], "utf-8")
                )
            except Exception:
                to_unzip_code = base64.b64decode(updated_spec["ZipFile"])

            self.code_bytes = to_unzip_code
            self.code_size = len(to_unzip_code)
            self.code_sha_256 = hashlib.sha256(to_unzip_code).hexdigest()

            # TODO: we should be putting this in a lambda bucket
            self.code["UUID"] = str(uuid.uuid4())
            self.code["S3Key"] = "{}-{}".format(self.function_name, self.code["UUID"])
        elif "S3Bucket" in updated_spec and "S3Key" in updated_spec:
            key = None
            try:
                # FIXME: does not validate bucket region
                key = s3_backend.get_object(
                    updated_spec["S3Bucket"], updated_spec["S3Key"]
                )
            except MissingBucket:
                if do_validate_s3():
                    raise ValueError(
                        "InvalidParameterValueException",
                        "Error occurred while GetObject. S3 Error Code: NoSuchBucket. S3 Error Message: The specified bucket does not exist",
                    )
            except MissingKey:
                if do_validate_s3():
                    raise ValueError(
                        "InvalidParameterValueException",
                        "Error occurred while GetObject. S3 Error Code: NoSuchKey. S3 Error Message: The specified key does not exist.",
                    )
            if key:
                self.code_bytes = key.value
                self.code_size = key.size
                self.code_sha_256 = hashlib.sha256(key.value).hexdigest()
                self.code["S3Bucket"] = updated_spec["S3Bucket"]
                self.code["S3Key"] = updated_spec["S3Key"]

        return self.get_configuration()

    @staticmethod
    def convert(s):
        try:
            return str(s, encoding="utf-8")
        except Exception:
            return s

    def _invoke_lambda(self, code, event=None, context=None):
        # Create the LogGroup if necessary, to write the result to
        self.logs_backend.ensure_log_group(self.logs_group_name, [])
        # TODO: context not yet implemented
        if event is None:
            event = dict()
        if context is None:
            context = {}
        output = None

        try:
            # TODO: I believe we can keep the container running and feed events as needed
            #       also need to hook it up to the other services so it can make kws/s3 etc calls
            #  Should get invoke_id /RequestId from invocation
            env_vars = {
                "_HANDLER": self.handler,
                "AWS_EXECUTION_ENV": "AWS_Lambda_{}".format(self.run_time),
                "AWS_LAMBDA_FUNCTION_TIMEOUT": self.timeout,
                "AWS_LAMBDA_FUNCTION_NAME": self.function_name,
                "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": self.memory_size,
                "AWS_LAMBDA_FUNCTION_VERSION": self.version,
                "AWS_REGION": self.region,
                "AWS_ACCESS_KEY_ID": "role-account-id",
                "AWS_SECRET_ACCESS_KEY": "role-secret-key",
                "AWS_SESSION_TOKEN": "session-token",
            }

            env_vars.update(self.environment_vars)

            container = exit_code = None
            log_config = docker.types.LogConfig(type=docker.types.LogConfig.types.JSON)
            with _DockerDataVolumeContext(self) as data_vol:
                try:
                    self.docker_client.ping()  # Verify Docker is running
                    run_kwargs = (
                        dict(links={"motoserver": "motoserver"})
                        if settings.TEST_SERVER_MODE
                        else {}
                    )
                    image_ref = "lambci/lambda:{}".format(self.run_time)
                    self.docker_client.images.pull(":".join(parse_image_ref(image_ref)))
                    container = self.docker_client.containers.run(
                        image_ref,
                        [self.handler, json.dumps(event)],
                        remove=False,
                        mem_limit="{}m".format(self.memory_size),
                        volumes=["{}:/var/task".format(data_vol.name)],
                        environment=env_vars,
                        detach=True,
                        log_config=log_config,
                        **run_kwargs
                    )
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
                                exit_code = exit_code["StatusCode"]

                        output = container.logs(stdout=False, stderr=True)
                        output += container.logs(stdout=True, stderr=False)
                        container.remove()

            output = output.decode("utf-8")

            # Send output to "logs" backend
            invoke_id = uuid.uuid4().hex
            log_stream_name = "{date.year}/{date.month:02d}/{date.day:02d}/[{version}]{invoke_id}".format(
                date=datetime.datetime.utcnow(),
                version=self.version,
                invoke_id=invoke_id,
            )

            self.logs_backend.create_log_stream(self.logs_group_name, log_stream_name)

            log_events = [
                {"timestamp": unix_time_millis(), "message": line}
                for line in output.splitlines()
            ]
            self.logs_backend.put_log_events(
                self.logs_group_name, log_stream_name, log_events, None
            )

            if exit_code != 0:
                raise Exception("lambda invoke failed output: {}".format(output))

            # We only care about the response from the lambda
            # Which is the last line of the output, according to https://github.com/lambci/docker-lambda/issues/25
            resp = output.splitlines()[-1]
            logs = os.linesep.join(
                [line for line in self.convert(output).splitlines()[:-1]]
            )
            return resp, False, logs
        except docker.errors.DockerException as e:
            # Docker itself is probably not running - there will be no Lambda-logs to handle
            return "error running docker: {}".format(e), True, ""
        except BaseException as e:
            logs = os.linesep.join(
                [line for line in self.convert(output).splitlines()[:-1]]
            )
            return "error running lambda: {}".format(e), True, logs

    def invoke(self, body, request_headers, response_headers):

        if body:
            body = json.loads(body)

        # Get the invocation type:
        res, errored, logs = self._invoke_lambda(code=self.code, event=body)
        inv_type = request_headers.get("x-amz-invocation-type", "RequestResponse")
        if inv_type == "RequestResponse":
            encoded = base64.b64encode(logs.encode("utf-8"))
            response_headers["x-amz-log-result"] = encoded.decode("utf-8")
            result = res.encode("utf-8")
        else:
            result = res
        if errored:
            response_headers["x-amz-function-error"] = "Handled"

        return result

    @staticmethod
    def cloudformation_name_type():
        return "FunctionName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-function.html
        return "AWS::Lambda::Function"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        optional_properties = (
            "Description",
            "MemorySize",
            "Publish",
            "Timeout",
            "VpcConfig",
            "Environment",
            "ReservedConcurrentExecutions",
        )

        # required
        spec = {
            "Code": properties["Code"],
            "FunctionName": resource_name,
            "Handler": properties["Handler"],
            "Role": properties["Role"],
            "Runtime": properties["Runtime"],
        }

        # NOTE: Not doing `properties.get(k, DEFAULT)` to avoid duplicating the
        # default logic
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]

        # when ZipFile is present in CloudFormation, per the official docs,
        # the code it's a plaintext code snippet up to 4096 bytes.
        # this snippet converts this plaintext code to a proper base64-encoded ZIP file.
        if "ZipFile" in properties["Code"]:
            spec["Code"]["ZipFile"] = base64.b64encode(
                cls._create_zipfile_from_plaintext_code(spec["Code"]["ZipFile"])
            )

        backend = lambda_backends[region_name]
        fn = backend.create_function(spec)
        return fn

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return make_function_arn(self.region, ACCOUNT_ID, self.function_name)
        raise UnformattedGetAttTemplateException()

    @classmethod
    def update_from_cloudformation_json(
        cls, new_resource_name, cloudformation_json, original_resource, region_name
    ):
        updated_props = cloudformation_json["Properties"]
        original_resource.update_configuration(updated_props)
        original_resource.update_function_code(updated_props["Code"])
        return original_resource

    @staticmethod
    def _create_zipfile_from_plaintext_code(code):
        zip_output = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
        zip_file.writestr("lambda_function.zip", code)
        zip_file.close()
        zip_output.seek(0)
        return zip_output.read()

    def delete(self, region):
        lambda_backends[region].delete_function(self.function_name)


class EventSourceMapping(CloudFormationModel):
    def __init__(self, spec):
        # required
        self.function_name = spec["FunctionName"]
        self.event_source_arn = spec["EventSourceArn"]

        # optional
        self.batch_size = spec.get("BatchSize")
        self.starting_position = spec.get("StartingPosition", "TRIM_HORIZON")
        self.enabled = spec.get("Enabled", True)
        self.starting_position_timestamp = spec.get("StartingPositionTimestamp", None)

        self.function_arn = spec["FunctionArn"]
        self.uuid = str(uuid.uuid4())
        self.last_modified = time.mktime(datetime.datetime.utcnow().timetuple())

    def _get_service_source_from_arn(self, event_source_arn):
        return event_source_arn.split(":")[2].lower()

    def _validate_event_source(self, event_source_arn):
        valid_services = ("dynamodb", "kinesis", "sqs")
        service = self._get_service_source_from_arn(event_source_arn)
        return True if service in valid_services else False

    @property
    def event_source_arn(self):
        return self._event_source_arn

    @event_source_arn.setter
    def event_source_arn(self, event_source_arn):
        if not self._validate_event_source(event_source_arn):
            raise ValueError(
                "InvalidParameterValueException", "Unsupported event source type"
            )
        self._event_source_arn = event_source_arn

    @property
    def batch_size(self):
        return self._batch_size

    @batch_size.setter
    def batch_size(self, batch_size):
        batch_size_service_map = {
            "kinesis": (100, 10000),
            "dynamodb": (100, 1000),
            "sqs": (10, 10),
        }

        source_type = self._get_service_source_from_arn(self.event_source_arn)
        batch_size_for_source = batch_size_service_map[source_type]

        if batch_size is None:
            self._batch_size = batch_size_for_source[0]
        elif batch_size > batch_size_for_source[1]:
            error_message = "BatchSize {} exceeds the max of {}".format(
                batch_size, batch_size_for_source[1]
            )
            raise ValueError("InvalidParameterValueException", error_message)
        else:
            self._batch_size = int(batch_size)

    def get_configuration(self):
        return {
            "UUID": self.uuid,
            "BatchSize": self.batch_size,
            "EventSourceArn": self.event_source_arn,
            "FunctionArn": self.function_arn,
            "LastModified": self.last_modified,
            "LastProcessingResult": "",
            "State": "Enabled" if self.enabled else "Disabled",
            "StateTransitionReason": "User initiated",
        }

    def delete(self, region_name):
        lambda_backend = lambda_backends[region_name]
        lambda_backend.delete_event_source_mapping(self.uuid)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-eventsourcemapping.html
        return "AWS::Lambda::EventSourceMapping"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        lambda_backend = lambda_backends[region_name]
        return lambda_backend.create_event_source_mapping(properties)

    @classmethod
    def update_from_cloudformation_json(
        cls, new_resource_name, cloudformation_json, original_resource, region_name
    ):
        properties = cloudformation_json["Properties"]
        event_source_uuid = original_resource.uuid
        lambda_backend = lambda_backends[region_name]
        return lambda_backend.update_event_source_mapping(event_source_uuid, properties)

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        lambda_backend = lambda_backends[region_name]
        esms = lambda_backend.list_event_source_mappings(
            event_source_arn=properties["EventSourceArn"],
            function_name=properties["FunctionName"],
        )

        for esm in esms:
            if esm.uuid == resource_name:
                esm.delete(region_name)

    @property
    def physical_resource_id(self):
        return self.uuid


class LambdaVersion(CloudFormationModel):
    def __init__(self, spec):
        self.version = spec["Version"]

    def __repr__(self):
        return str(self.logical_resource_id)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-version.html
        return "AWS::Lambda::Version"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        function_name = properties["FunctionName"]
        func = lambda_backends[region_name].publish_function(function_name)
        spec = {"Version": func.version}
        return LambdaVersion(spec)


class LambdaStorage(object):
    def __init__(self):
        # Format 'func_name' {'alias': {}, 'versions': []}
        self._functions = {}
        self._arns = weakref.WeakValueDictionary()

    def _get_latest(self, name):
        return self._functions[name]["latest"]

    def _get_version(self, name, version):
        index = version - 1

        try:
            return self._functions[name]["versions"][index]
        except IndexError:
            return None

    def _get_alias(self, name, alias):
        return self._functions[name]["alias"].get(alias, None)

    def get_function_by_name(self, name, qualifier=None):
        if name not in self._functions:
            return None

        if qualifier is None:
            return self._get_latest(name)

        try:
            return self._get_version(name, int(qualifier))
        except ValueError:
            return self._functions[name]["latest"]

    def list_versions_by_function(self, name):
        if name not in self._functions:
            return None

        latest = copy.copy(self._functions[name]["latest"])
        latest.function_arn += ":$LATEST"
        return [latest] + self._functions[name]["versions"]

    def get_arn(self, arn):
        return self._arns.get(arn, None)

    def get_function_by_name_or_arn(self, input, qualifier=None):
        return self.get_function_by_name(input, qualifier) or self.get_arn(input)

    def put_function(self, fn):
        """
        :param fn: Function
        :type fn: LambdaFunction
        """
        valid_role = re.match(InvalidRoleFormat.pattern, fn.role)
        if valid_role:
            account = valid_role.group(2)
            if account != ACCOUNT_ID:
                raise CrossAccountNotAllowed()
            try:
                iam_backend.get_role_by_arn(fn.role)
            except IAMNotFoundException:
                raise InvalidParameterValueException(
                    "The role defined for the function cannot be assumed by Lambda."
                )
        else:
            raise InvalidRoleFormat(fn.role)
        if fn.function_name in self._functions:
            self._functions[fn.function_name]["latest"] = fn
        else:
            self._functions[fn.function_name] = {
                "latest": fn,
                "versions": [],
                "alias": weakref.WeakValueDictionary(),
            }
        # instantiate a new policy for this version of the lambda
        fn.policy = Policy(fn)
        self._arns[fn.function_arn] = fn

    def publish_function(self, name):
        if name not in self._functions:
            return None
        if not self._functions[name]["latest"]:
            return None

        new_version = len(self._functions[name]["versions"]) + 1
        fn = copy.copy(self._functions[name]["latest"])
        fn.set_version(new_version)

        self._functions[name]["versions"].append(fn)
        self._arns[fn.function_arn] = fn
        return fn

    def del_function(self, name_or_arn, qualifier=None):
        function = self.get_function_by_name_or_arn(name_or_arn)
        if function:
            name = function.function_name
            if not qualifier:
                # Something is still reffing this so delete all arns
                latest = self._functions[name]["latest"].function_arn
                del self._arns[latest]

                for fn in self._functions[name]["versions"]:
                    del self._arns[fn.function_arn]

                del self._functions[name]

                return True

            elif qualifier == "$LATEST":
                self._functions[name]["latest"] = None

                # If theres no functions left
                if (
                    not self._functions[name]["versions"]
                    and not self._functions[name]["latest"]
                ):
                    del self._functions[name]

                return True

            else:
                fn = self.get_function_by_name(name, qualifier)
                if fn:
                    self._functions[name]["versions"].remove(fn)

                    # If theres no functions left
                    if (
                        not self._functions[name]["versions"]
                        and not self._functions[name]["latest"]
                    ):
                        del self._functions[name]

                    return True

        return False

    def all(self):
        result = []

        for function_group in self._functions.values():
            if function_group["latest"] is not None:
                result.append(function_group["latest"])

            result.extend(function_group["versions"])

        return result


class LayerStorage(object):
    def __init__(self):
        self._layers = {}
        self._arns = weakref.WeakValueDictionary()

    def put_layer_version(self, layer_version):
        """
        :param layer_version: LayerVersion
        """
        if layer_version.name not in self._layers:
            self._layers[layer_version.name] = Layer(
                layer_version.name, layer_version.region
            )
        self._layers[layer_version.name].attach_version(layer_version)

    def list_layers(self):
        return [layer.to_dict() for layer in self._layers.values()]

    def get_layer_versions(self, layer_name):
        if layer_name in self._layers:
            return list(iter(self._layers[layer_name].layer_versions.values()))
        return []

    def get_layer_version_by_arn(self, layer_version_arn):
        split_arn = split_layer_arn(layer_version_arn)
        if split_arn.layer_name in self._layers:
            return self._layers[split_arn.layer_name].layer_versions.get(
                split_arn.version, None
            )
        return None


class LambdaBackend(BaseBackend):
    def __init__(self, region_name):
        self._lambdas = LambdaStorage()
        self._event_source_mappings = {}
        self._layers = LayerStorage()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_function(self, spec):
        function_name = spec.get("FunctionName", None)
        if function_name is None:
            raise RESTError("InvalidParameterValueException", "Missing FunctionName")

        fn = LambdaFunction(spec, self.region_name, version="$LATEST")

        self._lambdas.put_function(fn)

        if spec.get("Publish"):
            ver = self.publish_function(function_name)
            fn.version = ver.version
        return fn

    def create_event_source_mapping(self, spec):
        required = ["EventSourceArn", "FunctionName"]
        for param in required:
            if not spec.get(param):
                raise RESTError(
                    "InvalidParameterValueException", "Missing {}".format(param)
                )

        # Validate function name
        func = self._lambdas.get_function_by_name_or_arn(spec.get("FunctionName", ""))
        if not func:
            raise RESTError("ResourceNotFoundException", "Invalid FunctionName")

        # Validate queue
        for queue in sqs_backends[self.region_name].queues.values():
            if queue.queue_arn == spec["EventSourceArn"]:
                if queue.lambda_event_source_mappings.get("func.function_arn"):
                    # TODO: Correct exception?
                    raise RESTError(
                        "ResourceConflictException", "The resource already exists."
                    )
                if queue.fifo_queue:
                    raise RESTError(
                        "InvalidParameterValueException",
                        "{} is FIFO".format(queue.queue_arn),
                    )
                else:
                    spec.update({"FunctionArn": func.function_arn})
                    esm = EventSourceMapping(spec)
                    self._event_source_mappings[esm.uuid] = esm

                    # Set backend function on queue
                    queue.lambda_event_source_mappings[esm.function_arn] = esm

                    return esm
        for stream in json.loads(
            dynamodbstreams_backends[self.region_name].list_streams()
        )["Streams"]:
            if stream["StreamArn"] == spec["EventSourceArn"]:
                spec.update({"FunctionArn": func.function_arn})
                esm = EventSourceMapping(spec)
                self._event_source_mappings[esm.uuid] = esm
                table_name = stream["TableName"]
                table = dynamodb_backends2[self.region_name].get_table(table_name)
                table.lambda_event_source_mappings[esm.function_arn] = esm
                return esm
        raise RESTError("ResourceNotFoundException", "Invalid EventSourceArn")

    def publish_layer_version(self, spec):
        required = ["LayerName", "Content"]
        for param in required:
            if not spec.get(param):
                raise RESTError(
                    "InvalidParameterValueException", "Missing {}".format(param)
                )
        layer_version = LayerVersion(spec, self.region_name)
        self._layers.put_layer_version(layer_version)
        return layer_version

    def list_layers(self):
        return self._layers.list_layers()

    def get_layer_versions(self, layer_name):
        return self._layers.get_layer_versions(layer_name)

    def layers_versions_by_arn(self, layer_version_arn):
        return self._layers.get_layer_version_by_arn(layer_version_arn)

    def publish_function(self, function_name):
        return self._lambdas.publish_function(function_name)

    def get_function(self, function_name_or_arn, qualifier=None):
        return self._lambdas.get_function_by_name_or_arn(
            function_name_or_arn, qualifier
        )

    def list_versions_by_function(self, function_name):
        return self._lambdas.list_versions_by_function(function_name)

    def get_event_source_mapping(self, uuid):
        return self._event_source_mappings.get(uuid)

    def delete_event_source_mapping(self, uuid):
        return self._event_source_mappings.pop(uuid)

    def update_event_source_mapping(self, uuid, spec):
        esm = self.get_event_source_mapping(uuid)
        if not esm:
            return False

        for key, value in spec.items():
            if key == "FunctionName":
                func = self._lambdas.get_function_by_name_or_arn(spec[key])
                esm.function_arn = func.function_arn
            elif key == "BatchSize":
                esm.batch_size = spec[key]
            elif key == "Enabled":
                esm.enabled = spec[key]

        esm.last_modified = time.mktime(datetime.datetime.utcnow().timetuple())
        return esm

    def list_event_source_mappings(self, event_source_arn, function_name):
        esms = list(self._event_source_mappings.values())
        if event_source_arn:
            esms = list(filter(lambda x: x.event_source_arn == event_source_arn, esms))
        if function_name:
            esms = list(filter(lambda x: x.function_name == function_name, esms))
        return esms

    def get_function_by_arn(self, function_arn):
        return self._lambdas.get_arn(function_arn)

    def delete_function(self, function_name, qualifier=None):
        return self._lambdas.del_function(function_name, qualifier)

    def list_functions(self):
        return self._lambdas.all()

    def send_sqs_batch(self, function_arn, messages, queue_arn):
        success = True
        for message in messages:
            func = self.get_function_by_arn(function_arn)
            result = self._send_sqs_message(func, message, queue_arn)
            if not result:
                success = False
        return success

    def _send_sqs_message(self, func, message, queue_arn):
        event = {
            "Records": [
                {
                    "messageId": message.id,
                    "receiptHandle": message.receipt_handle,
                    "body": message.body,
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": "1545082649183",
                        "SenderId": "AIDAIENQZJOLO23YVJ4VO",
                        "ApproximateFirstReceiveTimestamp": "1545082649185",
                    },
                    "messageAttributes": {},
                    "md5OfBody": "098f6bcd4621d373cade4e832627b4f6",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": queue_arn,
                    "awsRegion": self.region_name,
                }
            ]
        }

        request_headers = {}
        response_headers = {}
        func.invoke(json.dumps(event), request_headers, response_headers)
        return "x-amz-function-error" not in response_headers

    def send_sns_message(self, function_name, message, subject=None, qualifier=None):
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
                            "Test": {"Type": "String", "Value": "TestString"},
                            "TestBinary": {"Type": "Binary", "Value": "TestBinary"},
                        },
                        "Type": "Notification",
                        "UnsubscribeUrl": "EXAMPLE",
                        "TopicArn": "arn:aws:sns:EXAMPLE",
                        "Subject": subject or "TestInvoke",
                    },
                }
            ]
        }
        func = self._lambdas.get_function_by_name_or_arn(function_name, qualifier)
        func.invoke(json.dumps(event), {}, {})

    def send_dynamodb_items(self, function_arn, items, source):
        event = {
            "Records": [
                {
                    "eventID": item.to_json()["eventID"],
                    "eventName": "INSERT",
                    "eventVersion": item.to_json()["eventVersion"],
                    "eventSource": item.to_json()["eventSource"],
                    "awsRegion": self.region_name,
                    "dynamodb": item.to_json()["dynamodb"],
                    "eventSourceARN": source,
                }
                for item in items
            ]
        }
        func = self._lambdas.get_arn(function_arn)
        return func.invoke(json.dumps(event), {}, {})

    def send_log_event(
        self, function_arn, filter_name, log_group_name, log_stream_name, log_events
    ):
        data = {
            "messageType": "DATA_MESSAGE",
            "owner": ACCOUNT_ID,
            "logGroup": log_group_name,
            "logStream": log_stream_name,
            "subscriptionFilters": [filter_name],
            "logEvents": log_events,
        }

        output = io.BytesIO()
        with GzipFile(fileobj=output, mode="w") as f:
            f.write(json.dumps(data, separators=(",", ":")).encode("utf-8"))
        payload_gz_encoded = base64.b64encode(output.getvalue()).decode("utf-8")

        event = {"awslogs": {"data": payload_gz_encoded}}

        func = self._lambdas.get_arn(function_arn)
        return func.invoke(json.dumps(event), {}, {})

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

    def add_permission(self, function_name, raw):
        fn = self.get_function(function_name)
        fn.policy.add_statement(raw)

    def remove_permission(self, function_name, sid, revision=""):
        fn = self.get_function(function_name)
        fn.policy.del_statement(sid, revision)

    def get_policy(self, function_name):
        fn = self.get_function(function_name)
        return fn.policy.get_policy()

    def get_policy_wire_format(self, function_name):
        fn = self.get_function(function_name)
        return fn.policy.wire_format()

    def update_function_code(self, function_name, qualifier, body):
        fn = self.get_function(function_name, qualifier)

        if fn:
            if body.get("Publish", False):
                fn = self.publish_function(function_name)

            config = fn.update_function_code(body)
            return config
        else:
            return None

    def update_function_configuration(self, function_name, qualifier, body):
        fn = self.get_function(function_name, qualifier)

        return fn.update_configuration(body) if fn else None

    def invoke(self, function_name, qualifier, body, headers, response_headers):
        fn = self.get_function(function_name, qualifier)
        if fn:
            payload = fn.invoke(body, headers, response_headers)
            response_headers["Content-Length"] = str(len(payload))
            return payload
        else:
            return None

    def put_function_concurrency(self, function_name, reserved_concurrency):
        fn = self.get_function(function_name)
        fn.reserved_concurrency = reserved_concurrency
        return fn.reserved_concurrency

    def delete_function_concurrency(self, function_name):
        fn = self.get_function(function_name)
        fn.reserved_concurrency = None
        return fn.reserved_concurrency

    def get_function_concurrency(self, function_name):
        fn = self.get_function(function_name)
        return fn.reserved_concurrency


def do_validate_s3():
    return os.environ.get("VALIDATE_LAMBDA_S3", "") in ["", "1", "true"]


lambda_backends = {}
for region in Session().get_available_regions("lambda"):
    lambda_backends[region] = LambdaBackend(region)
for region in Session().get_available_regions("lambda", partition_name="aws-us-gov"):
    lambda_backends[region] = LambdaBackend(region)
for region in Session().get_available_regions("lambda", partition_name="aws-cn"):
    lambda_backends[region] = LambdaBackend(region)
