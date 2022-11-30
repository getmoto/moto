import base64
import time
from collections import defaultdict
import copy
import datetime
from gzip import GzipFile
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from sys import platform

import docker
import docker.errors
import hashlib
import io
import logging
import os
import json
import re
import zipfile
import tarfile
import calendar
import threading
import weakref
import requests.exceptions

from moto.awslambda.policy import Policy
from moto.core import BaseBackend, BackendDict, BaseModel, CloudFormationModel
from moto.core.exceptions import RESTError
from moto.core.utils import unix_time_millis
from moto.iam.models import iam_backends
from moto.iam.exceptions import IAMNotFoundException
from moto.ecr.exceptions import ImageNotFoundException
from moto.logs.models import logs_backends
from moto.moto_api._internal import mock_random as random
from moto.s3.models import s3_backends, FakeKey
from moto.ecr.models import ecr_backends
from moto.s3.exceptions import MissingBucket, MissingKey
from moto import settings
from .exceptions import (
    CrossAccountNotAllowed,
    FunctionUrlConfigNotFound,
    InvalidRoleFormat,
    InvalidParameterValueException,
    UnknownLayerException,
    UnknownFunctionException,
    UnknownAliasException,
)
from .utils import (
    make_function_arn,
    make_function_ver_arn,
    make_layer_arn,
    make_layer_ver_arn,
    split_layer_arn,
)
from moto.sqs import sqs_backends
from moto.dynamodb import dynamodb_backends
from moto.dynamodbstreams import dynamodbstreams_backends
from moto.utilities.docker_utilities import DockerModel, parse_image_ref
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)


docker_3 = docker.__version__[0] >= "3"


def zip2tar(zip_bytes: bytes) -> bytes:
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

    def __init__(self, refcount: int, volume: Any):
        self.refcount = refcount
        self.volume = volume


class _DockerDataVolumeContext:
    # {sha256: _VolumeRefCount}
    _data_vol_map: Dict[str, _VolumeRefCount] = defaultdict(
        lambda: _VolumeRefCount(0, None)
    )
    _lock = threading.Lock()

    def __init__(self, lambda_func: "LambdaFunction"):
        self._lambda_func = lambda_func
        self._vol_ref: Optional[_VolumeRefCount] = None

    @property
    def name(self) -> str:
        return self._vol_ref.volume.name  # type: ignore[union-attr]

    def __enter__(self) -> "_DockerDataVolumeContext":
        # See if volume is already known
        with self.__class__._lock:
            self._vol_ref = self.__class__._data_vol_map[self._lambda_func.code_digest]
            self._vol_ref.refcount += 1
            if self._vol_ref.refcount > 1:
                return self

            # See if the volume already exists
            for vol in self._lambda_func.docker_client.volumes.list():
                if vol.name == self._lambda_func.code_digest:
                    self._vol_ref.volume = vol
                    return self

            # It doesn't exist so we need to create it
            self._vol_ref.volume = self._lambda_func.docker_client.volumes.create(
                self._lambda_func.code_digest
            )
            volumes = {
                self.name: {"bind": "/tmp/data", "mode": "rw"}
                if docker_3
                else "/tmp/data"
            }

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

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        with self.__class__._lock:
            self._vol_ref.refcount -= 1  # type: ignore[union-attr]
            if self._vol_ref.refcount == 0:  # type: ignore[union-attr]
                try:
                    self._vol_ref.volume.remove()  # type: ignore[union-attr]
                except docker.errors.APIError as e:
                    if e.status_code != 409:
                        raise

                    raise  # multiple processes trying to use same volume?


def _zipfile_content(zipfile_content: Union[str, bytes]) -> Tuple[bytes, int, str, str]:
    try:
        to_unzip_code = base64.b64decode(bytes(zipfile_content, "utf-8"))  # type: ignore[arg-type]
    except Exception:
        to_unzip_code = base64.b64decode(zipfile_content)

    sha_code = hashlib.sha256(to_unzip_code)
    base64ed_sha = base64.b64encode(sha_code.digest()).decode("utf-8")
    sha_hex_digest = sha_code.hexdigest()
    return to_unzip_code, len(to_unzip_code), base64ed_sha, sha_hex_digest


def _s3_content(key: Any) -> Tuple[bytes, int, str, str]:
    sha_code = hashlib.sha256(key.value)
    base64ed_sha = base64.b64encode(sha_code.digest()).decode("utf-8")
    sha_hex_digest = sha_code.hexdigest()
    return key.value, key.size, base64ed_sha, sha_hex_digest


def _validate_s3_bucket_and_key(
    account_id: str, data: Dict[str, Any]
) -> Optional[FakeKey]:
    key = None
    try:
        # FIXME: does not validate bucket region
        key = s3_backends[account_id]["global"].get_object(
            data["S3Bucket"], data["S3Key"]
        )
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
    def __init__(self, region: str):
        self.region = region

    @staticmethod
    def cloudformation_name_type() -> str:
        return "Permission"

    @staticmethod
    def cloudformation_type() -> str:
        return "AWS::Lambda::Permission"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "Permission":
        properties = cloudformation_json["Properties"]
        backend = lambda_backends[account_id][region_name]
        fn = backend.get_function(properties["FunctionName"])
        fn.policy.add_statement(raw=json.dumps(properties))
        return Permission(region=region_name)


class LayerVersion(CloudFormationModel):
    def __init__(self, spec: Dict[str, Any], account_id: str, region: str):
        # required
        self.account_id = account_id
        self.region = region
        self.name = spec["LayerName"]
        self.content = spec["Content"]

        # optional
        self.description = spec.get("Description", "")
        self.compatible_architectures = spec.get("CompatibleArchitectures", [])
        self.compatible_runtimes = spec.get("CompatibleRuntimes", [])
        self.license_info = spec.get("LicenseInfo", "")

        # auto-generated
        self.created_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.version: Optional[int] = None
        self._attached = False
        self._layer: Optional["Layer"] = None

        if "ZipFile" in self.content:
            (
                self.code_bytes,
                self.code_size,
                self.code_sha_256,
                self.code_digest,
            ) = _zipfile_content(self.content["ZipFile"])
        else:
            key = _validate_s3_bucket_and_key(account_id, data=self.content)
            if key:
                (
                    self.code_bytes,
                    self.code_size,
                    self.code_sha_256,
                    self.code_digest,
                ) = _s3_content(
                    key
                )  # type: ignore[assignment]

    @property
    def arn(self) -> str:
        if self.version:
            return make_layer_ver_arn(
                self.region, self.account_id, self.name, self.version
            )
        raise ValueError("Layer version is not set")

    def attach(self, layer: "Layer", version: int) -> None:
        self._attached = True
        self._layer = layer
        self.version = version

    def get_layer_version(self) -> Dict[str, Any]:
        return {
            "Content": {
                "Location": "s3://",
                "CodeSha256": self.code_sha_256,
                "CodeSize": self.code_size,
            },
            "Version": self.version,
            "LayerArn": self._layer.layer_arn,  # type: ignore[union-attr]
            "LayerVersionArn": self.arn,
            "CreatedDate": self.created_date,
            "CompatibleArchitectures": self.compatible_architectures,
            "CompatibleRuntimes": self.compatible_runtimes,
            "Description": self.description,
            "LicenseInfo": self.license_info,
        }

    @staticmethod
    def cloudformation_name_type() -> str:
        return "LayerVersion"

    @staticmethod
    def cloudformation_type() -> str:
        return "AWS::Lambda::LayerVersion"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "LayerVersion":
        properties = cloudformation_json["Properties"]
        optional_properties = ("Description", "CompatibleRuntimes", "LicenseInfo")

        # required
        spec = {
            "Content": properties["Content"],
            "LayerName": resource_name,
        }
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]

        backend = lambda_backends[account_id][region_name]
        layer_version = backend.publish_layer_version(spec)
        return layer_version


class LambdaAlias(BaseModel):
    def __init__(
        self,
        account_id: str,
        region: str,
        name: str,
        function_name: str,
        function_version: str,
        description: str,
        routing_config: str,
    ):
        self.arn = (
            f"arn:aws:lambda:{region}:{account_id}:function:{function_name}:{name}"
        )
        self.name = name
        self.function_version = function_version
        self.description = description
        self.routing_config = routing_config
        self.revision_id = str(random.uuid4())

    def update(
        self,
        description: Optional[str],
        function_version: Optional[str],
        routing_config: Optional[str],
    ) -> None:
        if description is not None:
            self.description = description
        if function_version is not None:
            self.function_version = function_version
        if routing_config is not None:
            self.routing_config = routing_config

    def to_json(self) -> Dict[str, Any]:
        return {
            "AliasArn": self.arn,
            "Description": self.description,
            "FunctionVersion": self.function_version,
            "Name": self.name,
            "RevisionId": self.revision_id,
            "RoutingConfig": self.routing_config or None,
        }


class Layer(object):
    def __init__(self, layer_version: LayerVersion):
        self.region = layer_version.region
        self.name = layer_version.name

        self.layer_arn = make_layer_arn(
            self.region, layer_version.account_id, self.name
        )
        self._latest_version = 0
        self.layer_versions: Dict[str, LayerVersion] = {}

    def attach_version(self, layer_version: LayerVersion) -> None:
        self._latest_version += 1
        layer_version.attach(self, self._latest_version)
        self.layer_versions[str(self._latest_version)] = layer_version

    def delete_version(self, layer_version: str) -> None:
        self.layer_versions.pop(str(layer_version), None)

    def to_dict(self) -> Dict[str, Any]:
        if not self.layer_versions:
            return {}

        last_key = sorted(self.layer_versions.keys(), key=lambda version: int(version))[
            -1
        ]
        return {
            "LayerName": self.name,
            "LayerArn": self.layer_arn,
            "LatestMatchingVersion": self.layer_versions[last_key].get_layer_version(),
        }


class LambdaFunction(CloudFormationModel, DockerModel):
    def __init__(
        self,
        account_id: str,
        spec: Dict[str, Any],
        region: str,
        version: Union[str, int] = 1,
    ):
        DockerModel.__init__(self)
        # required
        self.account_id = account_id
        self.region = region
        self.code = spec["Code"]
        self.function_name = spec["FunctionName"]
        self.handler = spec.get("Handler")
        self.role = spec["Role"]
        self.run_time = spec.get("Runtime")
        self.logs_backend = logs_backends[account_id][self.region]
        self.environment_vars = spec.get("Environment", {}).get("Variables", {})
        self.policy: Optional[Policy] = None
        self.url_config: Optional[FunctionUrlConfig] = None
        self.state = "Active"
        self.reserved_concurrency = spec.get("ReservedConcurrentExecutions", None)

        # optional
        self.description = spec.get("Description", "")
        self.memory_size = spec.get("MemorySize", 128)
        self.package_type = spec.get("PackageType", None)
        self.publish = spec.get("Publish", False)  # this is ignored currently
        self.timeout = spec.get("Timeout", 3)
        self.layers = self._get_layers_data(spec.get("Layers", []))
        self.signing_profile_version_arn = spec.get("SigningProfileVersionArn")
        self.signing_job_arn = spec.get("SigningJobArn")
        self.code_signing_config_arn = spec.get("CodeSigningConfigArn")
        self.tracing_config = spec.get("TracingConfig") or {"Mode": "PassThrough"}

        self.logs_group_name = f"/aws/lambda/{self.function_name}"

        # this isn't finished yet. it needs to find out the VpcId value
        self._vpc_config = spec.get(
            "VpcConfig", {"SubnetIds": [], "SecurityGroupIds": []}
        )

        # auto-generated
        self.version = version
        self.last_modified = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if "ZipFile" in self.code:
            (
                self.code_bytes,
                self.code_size,
                self.code_sha_256,
                self.code_digest,
            ) = _zipfile_content(self.code["ZipFile"])

            # TODO: we should be putting this in a lambda bucket
            self.code["UUID"] = str(random.uuid4())
            self.code["S3Key"] = f"{self.function_name}-{self.code['UUID']}"
        elif "S3Bucket" in self.code:
            key = _validate_s3_bucket_and_key(self.account_id, data=self.code)
            if key:
                (
                    self.code_bytes,
                    self.code_size,
                    self.code_sha_256,
                    self.code_digest,
                ) = _s3_content(key)
            else:
                self.code_bytes = b""
                self.code_size = 0
                self.code_sha_256 = ""
        elif "ImageUri" in self.code:
            if settings.lambda_stub_ecr():
                self.code_sha_256 = hashlib.sha256(
                    self.code["ImageUri"].encode("utf-8")
                ).hexdigest()
                self.code_size = 0
            else:
                uri, tag = self.code["ImageUri"].split(":")
                repo_name = uri.split("/")[-1]
                image_id = {"imageTag": tag}
                ecr_backend = ecr_backends[self.account_id][self.region]
                registry_id = ecr_backend.describe_registry()["registryId"]
                images = ecr_backend.batch_get_image(
                    repository_name=repo_name, image_ids=[image_id]
                )["images"]

                if len(images) == 0:
                    raise ImageNotFoundException(image_id, repo_name, registry_id)  # type: ignore
                else:
                    manifest = json.loads(images[0]["imageManifest"])
                    self.code_sha_256 = images[0]["imageId"]["imageDigest"].replace(
                        "sha256:", ""
                    )
                    self.code_size = manifest["config"]["size"]

        self.function_arn = make_function_arn(
            self.region, self.account_id, self.function_name
        )

        self.tags = spec.get("Tags") or dict()

        self._aliases: Dict[str, LambdaAlias] = dict()

    def __getstate__(self) -> Dict[str, Any]:
        return {
            k: v
            for (k, v) in self.__dict__.items()
            if k != "_DockerModel__docker_client"
        }

    def set_version(self, version: int) -> None:
        self.function_arn = make_function_ver_arn(
            self.region, self.account_id, self.function_name, version
        )
        self.version = version
        self.last_modified = datetime.datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%S.000+0000"
        )

    @property
    def vpc_config(self) -> Dict[str, Any]:  # type: ignore[misc]
        config = self._vpc_config.copy()
        if config["SecurityGroupIds"]:
            config.update({"VpcId": "vpc-123abc"})
        return config

    @property
    def physical_resource_id(self) -> str:
        return self.function_name

    def __repr__(self) -> str:
        return json.dumps(self.get_configuration())

    def _get_layers_data(self, layers_versions_arns: List[str]) -> List[Dict[str, str]]:
        backend = lambda_backends[self.account_id][self.region]
        layer_versions = [
            backend.layers_versions_by_arn(layer_version)
            for layer_version in layers_versions_arns
        ]
        if not all(layer_versions):
            raise ValueError(
                "InvalidParameterValueException",
                f"One or more LayerVersion does not exist {layers_versions_arns}",
            )
        return [{"Arn": lv.arn, "CodeSize": lv.code_size} for lv in layer_versions]

    def get_code_signing_config(self) -> Dict[str, Any]:
        return {
            "CodeSigningConfigArn": self.code_signing_config_arn,
            "FunctionName": self.function_name,
        }

    def get_configuration(self, on_create: bool = False) -> Dict[str, Any]:
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
            "PackageType": self.package_type,
            "Timeout": self.timeout,
            "Version": str(self.version),
            "VpcConfig": self.vpc_config,
            "Layers": self.layers,
            "SigningProfileVersionArn": self.signing_profile_version_arn,
            "SigningJobArn": self.signing_job_arn,
            "TracingConfig": self.tracing_config,
        }
        if not on_create:
            # Only return this variable after the first creation
            config["LastUpdateStatus"] = "Successful"
        if self.environment_vars:
            config["Environment"] = {"Variables": self.environment_vars}

        return config

    def get_code(self) -> Dict[str, Any]:
        resp = {"Configuration": self.get_configuration()}
        if "S3Key" in self.code:
            resp["Code"] = {
                "Location": f"s3://awslambda-{self.region}-tasks.s3-{self.region}.amazonaws.com/{self.code['S3Key']}",
                "RepositoryType": "S3",
            }
        elif "ImageUri" in self.code:
            resp["Code"] = {
                "RepositoryType": "ECR",
                "ImageUri": self.code.get("ImageUri"),
                "ResolvedImageUri": self.code.get("ImageUri").split(":")[0]
                + "@sha256:"
                + self.code_sha_256,
            }
        if self.tags:
            resp["Tags"] = self.tags
        if self.reserved_concurrency:
            resp.update(
                {
                    "Concurrency": {
                        "ReservedConcurrentExecutions": self.reserved_concurrency
                    }
                }
            )
        return resp

    def update_configuration(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
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

    def update_function_code(self, updated_spec: Dict[str, Any]) -> Dict[str, Any]:
        if "DryRun" in updated_spec and updated_spec["DryRun"]:
            return self.get_configuration()

        if "ZipFile" in updated_spec:
            self.code["ZipFile"] = updated_spec["ZipFile"]

            (
                self.code_bytes,
                self.code_size,
                self.code_sha_256,
                self.code_digest,
            ) = _zipfile_content(updated_spec["ZipFile"])

            # TODO: we should be putting this in a lambda bucket
            self.code["UUID"] = str(random.uuid4())
            self.code["S3Key"] = f"{self.function_name}-{self.code['UUID']}"
        elif "S3Bucket" in updated_spec and "S3Key" in updated_spec:
            key = None
            try:
                # FIXME: does not validate bucket region
                key = s3_backends[self.account_id]["global"].get_object(
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
                (
                    self.code_bytes,
                    self.code_size,
                    self.code_sha_256,
                    self.code_digest,
                ) = _s3_content(
                    key
                )  # type: ignore[assignment]
                self.code["S3Bucket"] = updated_spec["S3Bucket"]
                self.code["S3Key"] = updated_spec["S3Key"]

        return self.get_configuration()

    @staticmethod
    def convert(s: Any) -> str:  # type: ignore[misc]
        try:
            return str(s, encoding="utf-8")
        except Exception:
            return s

    def _invoke_lambda(self, event: Optional[str] = None) -> Tuple[str, bool, str]:
        # Create the LogGroup if necessary, to write the result to
        self.logs_backend.ensure_log_group(self.logs_group_name, [])
        # TODO: context not yet implemented
        if event is None:
            event = dict()  # type: ignore[assignment]
        output = None

        try:
            # TODO: I believe we can keep the container running and feed events as needed
            #       also need to hook it up to the other services so it can make kws/s3 etc calls
            #  Should get invoke_id /RequestId from invocation
            env_vars = {
                "_HANDLER": self.handler,
                "AWS_EXECUTION_ENV": f"AWS_Lambda_{self.run_time}",
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
            env_vars["MOTO_HOST"] = settings.moto_server_host()
            env_vars["MOTO_PORT"] = settings.moto_server_port()
            env_vars[
                "MOTO_HTTP_ENDPOINT"
            ] = f'{env_vars["MOTO_HOST"]}:{env_vars["MOTO_PORT"]}'

            container = exit_code = None
            log_config = docker.types.LogConfig(type=docker.types.LogConfig.types.JSON)

            with _DockerDataVolumeContext(self) as data_vol:
                try:
                    run_kwargs: Dict[str, Any] = dict()
                    network_name = settings.moto_network_name()
                    network_mode = settings.moto_network_mode()
                    if network_name:
                        run_kwargs["network"] = network_name
                    elif network_mode:
                        run_kwargs["network_mode"] = network_mode
                    elif settings.TEST_SERVER_MODE:
                        # AWSLambda can make HTTP requests to a Docker container called 'motoserver'
                        # Only works if our Docker-container is named 'motoserver'
                        # TODO: should remove this and rely on 'network_mode' instead, as this is too tightly coupled with our own test setup
                        run_kwargs["links"] = {"motoserver": "motoserver"}

                    # add host.docker.internal host on linux to emulate Mac + Windows behavior
                    #   for communication with other mock AWS services running on localhost
                    if platform == "linux" or platform == "linux2":
                        run_kwargs["extra_hosts"] = {
                            "host.docker.internal": "host-gateway"
                        }

                    image_repo = settings.moto_lambda_image()
                    image_ref = f"{image_repo}:{self.run_time}"
                    self.docker_client.images.pull(":".join(parse_image_ref(image_ref)))
                    container = self.docker_client.containers.run(
                        image_ref,
                        [self.handler, json.dumps(event)],
                        remove=False,
                        mem_limit=f"{self.memory_size}m",
                        volumes=[f"{data_vol.name}:/var/task"],
                        environment=env_vars,
                        detach=True,
                        log_config=log_config,
                        **run_kwargs,
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

            output = output.decode("utf-8")  # type: ignore[union-attr]

            self.save_logs(output)

            # We only care about the response from the lambda
            # Which is the last line of the output, according to https://github.com/lambci/docker-lambda/issues/25
            resp = output.splitlines()[-1]
            logs = os.linesep.join(
                [line for line in self.convert(output).splitlines()[:-1]]
            )
            invocation_error = exit_code != 0
            return resp, invocation_error, logs
        except docker.errors.DockerException as e:
            # Docker itself is probably not running - there will be no Lambda-logs to handle
            msg = f"error running docker: {e}"
            self.save_logs(msg)
            return msg, True, ""

    def save_logs(self, output: str) -> None:
        # Send output to "logs" backend
        invoke_id = random.uuid4().hex
        date = datetime.datetime.utcnow()
        log_stream_name = (
            f"{date.year}/{date.month:02d}/{date.day:02d}/[{self.version}]{invoke_id}"
        )
        self.logs_backend.create_log_stream(self.logs_group_name, log_stream_name)
        log_events = [
            {"timestamp": unix_time_millis(), "message": line}
            for line in output.splitlines()
        ]
        self.logs_backend.put_log_events(
            self.logs_group_name, log_stream_name, log_events
        )

    def invoke(
        self, body: str, request_headers: Any, response_headers: Any
    ) -> Union[str, bytes]:
        if body:
            body = json.loads(body)
        else:
            body = "{}"

        # Get the invocation type:
        res, errored, logs = self._invoke_lambda(event=body)
        if errored:
            response_headers["x-amz-function-error"] = "Handled"

        inv_type = request_headers.get("x-amz-invocation-type", "RequestResponse")
        if inv_type == "RequestResponse":
            encoded = base64.b64encode(logs.encode("utf-8"))
            response_headers["x-amz-log-result"] = encoded.decode("utf-8")
            return res.encode("utf-8")
        else:
            return res

    @staticmethod
    def cloudformation_name_type() -> str:
        return "FunctionName"

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-function.html
        return "AWS::Lambda::Function"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "LambdaFunction":
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

        backend = lambda_backends[account_id][region_name]
        fn = backend.create_function(spec)
        return fn

    @classmethod
    def has_cfn_attr(cls, attr: str) -> bool:
        return attr in ["Arn"]

    def get_cfn_attribute(self, attribute_name: str) -> str:
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return make_function_arn(self.region, self.account_id, self.function_name)
        raise UnformattedGetAttTemplateException()

    @classmethod
    def update_from_cloudformation_json(  # type: ignore[misc]
        cls,
        original_resource: "LambdaFunction",
        new_resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
    ) -> "LambdaFunction":
        updated_props = cloudformation_json["Properties"]
        original_resource.update_configuration(updated_props)
        original_resource.update_function_code(updated_props["Code"])
        return original_resource

    @staticmethod
    def _create_zipfile_from_plaintext_code(code: str) -> bytes:
        zip_output = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
        zip_file.writestr("index.py", code)
        # This should really be part of the 'lambci' docker image
        from moto.packages.cfnresponse import cfnresponse

        with open(cfnresponse.__file__) as cfn:
            zip_file.writestr("cfnresponse.py", cfn.read())
        zip_file.close()
        zip_output.seek(0)
        return zip_output.read()

    def delete(self, account_id: str, region: str) -> None:
        lambda_backends[account_id][region].delete_function(self.function_name)

    def delete_alias(self, name: str) -> None:
        self._aliases.pop(name, None)

    def get_alias(self, name: str) -> LambdaAlias:
        if name in self._aliases:
            return self._aliases[name]
        arn = f"arn:aws:lambda:{self.region}:{self.account_id}:function:{self.function_name}:{name}"
        raise UnknownAliasException(arn)

    def has_alias(self, alias_name: str) -> bool:
        try:
            return self.get_alias(alias_name) is not None
        except UnknownAliasException:
            return False

    def put_alias(
        self, name: str, description: str, function_version: str, routing_config: str
    ) -> LambdaAlias:
        alias = LambdaAlias(
            account_id=self.account_id,
            region=self.region,
            name=name,
            function_name=self.function_name,
            function_version=function_version,
            description=description,
            routing_config=routing_config,
        )
        self._aliases[name] = alias
        return alias

    def update_alias(
        self, name: str, description: str, function_version: str, routing_config: str
    ) -> LambdaAlias:
        alias = self.get_alias(name)
        alias.update(description, function_version, routing_config)
        return alias

    def create_url_config(self, config: Dict[str, Any]) -> "FunctionUrlConfig":
        self.url_config = FunctionUrlConfig(function=self, config=config)
        return self.url_config  # type: ignore[return-value]

    def delete_url_config(self) -> None:
        self.url_config = None

    def get_url_config(self) -> "FunctionUrlConfig":
        if not self.url_config:
            raise FunctionUrlConfigNotFound()
        return self.url_config

    def update_url_config(self, config: Dict[str, Any]) -> "FunctionUrlConfig":
        self.url_config.update(config)  # type: ignore[union-attr]
        return self.url_config  # type: ignore[return-value]


class FunctionUrlConfig:
    def __init__(self, function: LambdaFunction, config: Dict[str, Any]):
        self.function = function
        self.config = config
        self.url = f"https://{random.uuid4().hex}.lambda-url.{function.region}.on.aws"
        self.created = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        self.last_modified = self.created

    def to_dict(self) -> Dict[str, Any]:
        return {
            "FunctionUrl": self.url,
            "FunctionArn": self.function.function_arn,
            "AuthType": self.config.get("AuthType"),
            "Cors": self.config.get("Cors"),
            "CreationTime": self.created,
            "LastModifiedTime": self.last_modified,
        }

    def update(self, new_config: Dict[str, Any]) -> None:
        if new_config.get("Cors"):
            self.config["Cors"] = new_config["Cors"]
        if new_config.get("AuthType"):
            self.config["AuthType"] = new_config["AuthType"]
        self.last_modified = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


class EventSourceMapping(CloudFormationModel):
    def __init__(self, spec: Dict[str, Any]):
        # required
        self.function_name = spec["FunctionName"]
        self.event_source_arn = spec["EventSourceArn"]

        # optional
        self.batch_size = spec.get("BatchSize")  # type: ignore[assignment]
        self.starting_position = spec.get("StartingPosition", "TRIM_HORIZON")
        self.enabled = spec.get("Enabled", True)
        self.starting_position_timestamp = spec.get("StartingPositionTimestamp", None)

        self.function_arn = spec["FunctionArn"]
        self.uuid = str(random.uuid4())
        self.last_modified = time.mktime(datetime.datetime.utcnow().timetuple())

    def _get_service_source_from_arn(self, event_source_arn: str) -> str:
        return event_source_arn.split(":")[2].lower()

    def _validate_event_source(self, event_source_arn: str) -> bool:
        valid_services = ("dynamodb", "kinesis", "sqs")
        service = self._get_service_source_from_arn(event_source_arn)
        return service in valid_services

    @property
    def event_source_arn(self) -> str:
        return self._event_source_arn

    @event_source_arn.setter
    def event_source_arn(self, event_source_arn: str) -> None:
        if not self._validate_event_source(event_source_arn):
            raise ValueError(
                "InvalidParameterValueException", "Unsupported event source type"
            )
        self._event_source_arn = event_source_arn

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @batch_size.setter
    def batch_size(self, batch_size: Optional[int]) -> None:
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
            error_message = (
                f"BatchSize {batch_size} exceeds the max of {batch_size_for_source[1]}"
            )
            raise ValueError("InvalidParameterValueException", error_message)
        else:
            self._batch_size = int(batch_size)

    def get_configuration(self) -> Dict[str, Any]:
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

    def delete(self, account_id: str, region_name: str) -> None:
        lambda_backend = lambda_backends[account_id][region_name]
        lambda_backend.delete_event_source_mapping(self.uuid)

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-eventsourcemapping.html
        return "AWS::Lambda::EventSourceMapping"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "EventSourceMapping":
        properties = cloudformation_json["Properties"]
        lambda_backend = lambda_backends[account_id][region_name]
        return lambda_backend.create_event_source_mapping(properties)

    @classmethod
    def update_from_cloudformation_json(  # type: ignore[misc]
        cls,
        original_resource: Any,
        new_resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
    ) -> "EventSourceMapping":
        properties = cloudformation_json["Properties"]
        event_source_uuid = original_resource.uuid
        lambda_backend = lambda_backends[account_id][region_name]
        return lambda_backend.update_event_source_mapping(event_source_uuid, properties)

    @classmethod
    def delete_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
    ) -> None:
        properties = cloudformation_json["Properties"]
        lambda_backend = lambda_backends[account_id][region_name]
        esms = lambda_backend.list_event_source_mappings(
            event_source_arn=properties["EventSourceArn"],
            function_name=properties["FunctionName"],
        )

        for esm in esms:
            if esm.uuid == resource_name:
                esm.delete(account_id, region_name)

    @property
    def physical_resource_id(self) -> str:
        return self.uuid


class LambdaVersion(CloudFormationModel):
    def __init__(self, spec: Dict[str, Any]):
        self.version = spec["Version"]

    def __repr__(self) -> str:
        return str(self.logical_resource_id)  # type: ignore[attr-defined]

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-version.html
        return "AWS::Lambda::Version"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "LambdaVersion":
        properties = cloudformation_json["Properties"]
        function_name = properties["FunctionName"]
        func = lambda_backends[account_id][region_name].publish_function(function_name)
        spec = {"Version": func.version}
        return LambdaVersion(spec)


class LambdaStorage(object):
    def __init__(self, region_name: str, account_id: str):
        # Format 'func_name' {'versions': []}
        self._functions: Dict[str, Any] = {}
        self._arns: weakref.WeakValueDictionary[
            str, LambdaFunction
        ] = weakref.WeakValueDictionary()
        self.region_name = region_name
        self.account_id = account_id

    def _get_latest(self, name: str) -> LambdaFunction:
        return self._functions[name]["latest"]

    def _get_version(self, name: str, version: str) -> Optional[LambdaFunction]:
        for config in self._functions[name]["versions"]:
            if str(config.version) == version or config.has_alias(version):
                return config
        return None

    def delete_alias(self, name: str, function_name: str) -> None:
        fn = self.get_function_by_name_or_arn(function_name)
        return fn.delete_alias(name)

    def get_alias(self, name: str, function_name: str) -> LambdaAlias:
        fn = self.get_function_by_name_or_arn(function_name)
        return fn.get_alias(name)

    def put_alias(
        self,
        name: str,
        function_name: str,
        function_version: str,
        description: str,
        routing_config: str,
    ) -> LambdaAlias:
        fn = self.get_function_by_name_or_arn(function_name)
        return fn.put_alias(name, description, function_version, routing_config)

    def update_alias(
        self,
        name: str,
        function_name: str,
        function_version: str,
        description: str,
        routing_config: str,
    ) -> LambdaAlias:
        fn = self.get_function_by_name_or_arn(function_name)
        return fn.update_alias(name, description, function_version, routing_config)

    def get_function_by_name(
        self, name: str, qualifier: Optional[str] = None
    ) -> Optional[LambdaFunction]:
        if name not in self._functions:
            return None

        if qualifier is None:
            return self._get_latest(name)

        if qualifier.lower() == "$latest":
            return self._functions[name]["latest"]

        return self._get_version(name, qualifier)

    def list_versions_by_function(self, name: str) -> Iterable[LambdaFunction]:
        if name not in self._functions:
            return []

        latest = copy.copy(self._functions[name]["latest"])
        latest.function_arn += ":$LATEST"
        return [latest] + self._functions[name]["versions"]

    def get_arn(self, arn: str) -> Optional[LambdaFunction]:
        # Function ARN may contain an alias
        # arn:aws:lambda:region:account_id:function:<fn_name>:<alias_name>
        if ":" in arn.split(":function:")[-1]:
            # arn = arn:aws:lambda:region:account_id:function:<fn_name>
            arn = ":".join(arn.split(":")[0:-1])
        return self._arns.get(arn, None)

    def get_function_by_name_or_arn(
        self, name_or_arn: str, qualifier: Optional[str] = None
    ) -> LambdaFunction:
        fn = self.get_function_by_name(name_or_arn, qualifier) or self.get_arn(
            name_or_arn
        )
        if fn is None:
            if name_or_arn.startswith("arn:aws"):
                arn = name_or_arn
            else:
                arn = make_function_arn(self.region_name, self.account_id, name_or_arn)
            if qualifier:
                arn = f"{arn}:{qualifier}"
            raise UnknownFunctionException(arn)
        return fn

    def put_function(self, fn: LambdaFunction) -> None:
        valid_role = re.match(InvalidRoleFormat.pattern, fn.role)
        if valid_role:
            account = valid_role.group(2)
            if account != self.account_id:
                raise CrossAccountNotAllowed()
            try:
                iam_backend = iam_backends[self.account_id]["global"]
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
            self._functions[fn.function_name] = {"latest": fn, "versions": []}
        # instantiate a new policy for this version of the lambda
        fn.policy = Policy(fn)
        self._arns[fn.function_arn] = fn

    def publish_function(
        self, name_or_arn: str, description: str = ""
    ) -> Optional[LambdaFunction]:
        function = self.get_function_by_name_or_arn(name_or_arn)
        name = function.function_name
        if name not in self._functions:
            return None
        if not self._functions[name]["latest"]:
            return None

        new_version = len(self._functions[name]["versions"]) + 1
        fn = copy.copy(self._functions[name]["latest"])
        fn.set_version(new_version)
        if description:
            fn.description = description

        self._functions[name]["versions"].append(fn)
        self._arns[fn.function_arn] = fn
        return fn

    def del_function(self, name_or_arn: str, qualifier: Optional[str] = None) -> None:
        function = self.get_function_by_name_or_arn(name_or_arn, qualifier)
        name = function.function_name
        if not qualifier:
            # Something is still reffing this so delete all arns
            latest = self._functions[name]["latest"].function_arn
            del self._arns[latest]

            for fn in self._functions[name]["versions"]:
                del self._arns[fn.function_arn]

            del self._functions[name]

        elif qualifier == "$LATEST":
            self._functions[name]["latest"] = None

            # If theres no functions left
            if (
                not self._functions[name]["versions"]
                and not self._functions[name]["latest"]
            ):
                del self._functions[name]

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

    def all(self) -> Iterable[LambdaFunction]:
        result = []

        for function_group in self._functions.values():
            latest = copy.deepcopy(function_group["latest"])
            latest.function_arn = f"{latest.function_arn}:$LATEST"
            result.append(latest)

            result.extend(function_group["versions"])

        return result

    def latest(self) -> Iterable[LambdaFunction]:
        """
        Return the list of functions with version @LATEST
        :return:
        """
        result = []
        for function_group in self._functions.values():
            if function_group["latest"] is not None:
                result.append(function_group["latest"])

        return result


class LayerStorage(object):
    def __init__(self) -> None:
        self._layers: Dict[str, Layer] = {}
        self._arns: weakref.WeakValueDictionary[
            str, LambdaFunction
        ] = weakref.WeakValueDictionary()

    def put_layer_version(self, layer_version: LayerVersion) -> None:
        """
        :param layer_version: LayerVersion
        """
        if layer_version.name not in self._layers:
            self._layers[layer_version.name] = Layer(layer_version)
        self._layers[layer_version.name].attach_version(layer_version)

    def list_layers(self) -> Iterable[Dict[str, Any]]:
        return [
            layer.to_dict() for layer in self._layers.values() if layer.layer_versions
        ]

    def delete_layer_version(self, layer_name: str, layer_version: str) -> None:
        self._layers[layer_name].delete_version(layer_version)

    def get_layer_version(self, layer_name: str, layer_version: str) -> LayerVersion:
        if layer_name not in self._layers:
            raise UnknownLayerException()
        for lv in self._layers[layer_name].layer_versions.values():
            if lv.version == int(layer_version):
                return lv
        raise UnknownLayerException()

    def get_layer_versions(self, layer_name: str) -> List[LayerVersion]:
        if layer_name in self._layers:
            return list(iter(self._layers[layer_name].layer_versions.values()))
        return []

    def get_layer_version_by_arn(
        self, layer_version_arn: str
    ) -> Optional[LayerVersion]:
        split_arn = split_layer_arn(layer_version_arn)
        if split_arn.layer_name in self._layers:
            return self._layers[split_arn.layer_name].layer_versions.get(
                split_arn.version, None
            )
        return None


class LambdaBackend(BaseBackend):
    """
    Implementation of the AWS Lambda endpoint.
    Invoking functions is supported - they will run inside a Docker container, emulating the real AWS behaviour as closely as possible.

    It is possible to connect from AWS Lambdas to other services, as long as you are running Moto in ServerMode.
    The Lambda has access to environment variables `MOTO_HOST` and `MOTO_PORT`, which can be used to build the url that MotoServer runs on:

    .. sourcecode:: python

        def lambda_handler(event, context):
            host = os.environ.get("MOTO_HOST")
            port = os.environ.get("MOTO_PORT")
            url = host + ":" + port
            ec2 = boto3.client('ec2', region_name='us-west-2', endpoint_url=url)

            # Or even simpler:
            full_url = os.environ.get("MOTO_HTTP_ENDPOINT")
            ec2 = boto3.client("ec2", region_name="eu-west-1", endpoint_url=full_url)

            ec2.do_whatever_inside_the_existing_moto_server()

    Moto will run on port 5000 by default. This can be overwritten by setting an environment variable when starting Moto:

    .. sourcecode:: bash

        # This env var will be propagated to the Docker container running the Lambda functions
        MOTO_PORT=5000 moto_server

    The Docker container uses the default network mode, `bridge`.
    The following environment variables are available for fine-grained control over the Docker connection options:

    .. sourcecode:: bash

        # Provide the name of a custom network to connect to
        MOTO_DOCKER_NETWORK_NAME=mycustomnetwork moto_server

        # Override the network mode
        # For example, network_mode=host would use the network of the host machine
        # Note that this option will be ignored if MOTO_DOCKER_NETWORK_NAME is also set
        MOTO_DOCKER_NETWORK_MODE=host moto_server

    The Docker images used by Moto are taken from the `lambci/lambda`-repo by default. Use the following environment variable to configure a different repo:

    .. sourcecode:: bash

        MOTO_DOCKER_LAMBDA_IMAGE=mLupin/docker-lambda

    .. note:: When using the decorators, a Docker container cannot reach Moto, as it does not run as a server. Any boto3-invocations used within your Lambda will try to connect to AWS.
    """

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self._lambdas = LambdaStorage(region_name=region_name, account_id=account_id)
        self._event_source_mappings: Dict[str, EventSourceMapping] = {}
        self._layers = LayerStorage()

    @staticmethod
    def default_vpc_endpoint_service(service_region: str, zones: List[str]) -> List[Dict[str, str]]:  # type: ignore[misc]
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "lambda"
        )

    def create_alias(
        self,
        name: str,
        function_name: str,
        function_version: str,
        description: str,
        routing_config: str,
    ) -> LambdaAlias:
        return self._lambdas.put_alias(
            name, function_name, function_version, description, routing_config
        )

    def delete_alias(self, name: str, function_name: str) -> None:
        return self._lambdas.delete_alias(name, function_name)

    def get_alias(self, name: str, function_name: str) -> LambdaAlias:
        return self._lambdas.get_alias(name, function_name)

    def update_alias(
        self,
        name: str,
        function_name: str,
        function_version: str,
        description: str,
        routing_config: str,
    ) -> LambdaAlias:
        """
        The RevisionId parameter is not yet implemented
        """
        return self._lambdas.update_alias(
            name, function_name, function_version, description, routing_config
        )

    def create_function(self, spec: Dict[str, Any]) -> LambdaFunction:
        """
        The Code.ImageUri is not validated by default. Set environment variable MOTO_LAMBDA_STUB_ECR=false if you want to validate the image exists in our mocked ECR.
        """
        function_name = spec.get("FunctionName", None)
        if function_name is None:
            raise RESTError("InvalidParameterValueException", "Missing FunctionName")

        fn = LambdaFunction(
            account_id=self.account_id,
            spec=spec,
            region=self.region_name,
            version="$LATEST",
        )

        self._lambdas.put_function(fn)

        if spec.get("Publish"):
            ver = self.publish_function(function_name)
            fn = copy.deepcopy(
                fn
            )  # We don't want to change the actual version - just the return value
            fn.version = ver.version  # type: ignore[union-attr]
        return fn

    def create_function_url_config(
        self, name_or_arn: str, config: Dict[str, Any]
    ) -> FunctionUrlConfig:
        """
        The Qualifier-parameter is not yet implemented.
        Function URLs are not yet mocked, so invoking them will fail
        """
        function = self._lambdas.get_function_by_name_or_arn(name_or_arn)
        return function.create_url_config(config)

    def delete_function_url_config(self, name_or_arn: str) -> None:
        """
        The Qualifier-parameter is not yet implemented
        """
        function = self._lambdas.get_function_by_name_or_arn(name_or_arn)
        function.delete_url_config()

    def get_function_url_config(self, name_or_arn: str) -> FunctionUrlConfig:
        """
        The Qualifier-parameter is not yet implemented
        """
        function = self._lambdas.get_function_by_name_or_arn(name_or_arn)
        if not function:
            raise UnknownFunctionException(arn=name_or_arn)
        return function.get_url_config()

    def update_function_url_config(
        self, name_or_arn: str, config: Dict[str, Any]
    ) -> FunctionUrlConfig:
        """
        The Qualifier-parameter is not yet implemented
        """
        function = self._lambdas.get_function_by_name_or_arn(name_or_arn)
        return function.update_url_config(config)

    def create_event_source_mapping(self, spec: Dict[str, Any]) -> EventSourceMapping:
        required = ["EventSourceArn", "FunctionName"]
        for param in required:
            if not spec.get(param):
                raise RESTError("InvalidParameterValueException", f"Missing {param}")

        # Validate function name
        func = self._lambdas.get_function_by_name_or_arn(spec.get("FunctionName", ""))
        if not func:
            raise RESTError("ResourceNotFoundException", "Invalid FunctionName")

        # Validate queue
        sqs_backend = sqs_backends[self.account_id][self.region_name]
        for queue in sqs_backend.queues.values():
            if queue.queue_arn == spec["EventSourceArn"]:
                if queue.lambda_event_source_mappings.get("func.function_arn"):
                    # TODO: Correct exception?
                    raise RESTError(
                        "ResourceConflictException", "The resource already exists."
                    )
                if queue.fifo_queue:
                    raise RESTError(
                        "InvalidParameterValueException", f"{queue.queue_arn} is FIFO"
                    )
                else:
                    spec.update({"FunctionArn": func.function_arn})
                    esm = EventSourceMapping(spec)
                    self._event_source_mappings[esm.uuid] = esm

                    # Set backend function on queue
                    queue.lambda_event_source_mappings[esm.function_arn] = esm

                    return esm
        ddbstream_backend = dynamodbstreams_backends[self.account_id][self.region_name]
        ddb_backend = dynamodb_backends[self.account_id][self.region_name]
        for stream in json.loads(ddbstream_backend.list_streams())["Streams"]:
            if stream["StreamArn"] == spec["EventSourceArn"]:
                spec.update({"FunctionArn": func.function_arn})
                esm = EventSourceMapping(spec)
                self._event_source_mappings[esm.uuid] = esm
                table_name = stream["TableName"]
                table = ddb_backend.get_table(table_name)
                table.lambda_event_source_mappings[esm.function_arn] = esm
                return esm
        raise RESTError("ResourceNotFoundException", "Invalid EventSourceArn")

    def publish_layer_version(self, spec: Dict[str, Any]) -> LayerVersion:
        required = ["LayerName", "Content"]
        for param in required:
            if not spec.get(param):
                raise InvalidParameterValueException(f"Missing {param}")
        layer_version = LayerVersion(
            spec, account_id=self.account_id, region=self.region_name
        )
        self._layers.put_layer_version(layer_version)
        return layer_version

    def list_layers(self) -> Iterable[Dict[str, Any]]:
        return self._layers.list_layers()

    def delete_layer_version(self, layer_name: str, layer_version: str) -> None:
        return self._layers.delete_layer_version(layer_name, layer_version)

    def get_layer_version(self, layer_name: str, layer_version: str) -> LayerVersion:
        return self._layers.get_layer_version(layer_name, layer_version)

    def get_layer_versions(self, layer_name: str) -> Iterable[LayerVersion]:
        return self._layers.get_layer_versions(layer_name)

    def layers_versions_by_arn(self, layer_version_arn: str) -> Optional[LayerVersion]:
        return self._layers.get_layer_version_by_arn(layer_version_arn)

    def publish_function(
        self, function_name: str, description: str = ""
    ) -> Optional[LambdaFunction]:
        return self._lambdas.publish_function(function_name, description)

    def get_function(
        self, function_name_or_arn: str, qualifier: Optional[str] = None
    ) -> LambdaFunction:
        return self._lambdas.get_function_by_name_or_arn(
            function_name_or_arn, qualifier
        )

    def list_versions_by_function(self, function_name: str) -> Iterable[LambdaFunction]:
        return self._lambdas.list_versions_by_function(function_name)

    def get_event_source_mapping(self, uuid: str) -> Optional[EventSourceMapping]:
        return self._event_source_mappings.get(uuid)

    def delete_event_source_mapping(self, uuid: str) -> Optional[EventSourceMapping]:
        return self._event_source_mappings.pop(uuid, None)

    def update_event_source_mapping(
        self, uuid: str, spec: Dict[str, Any]
    ) -> Optional[EventSourceMapping]:
        esm = self.get_event_source_mapping(uuid)
        if not esm:
            return None

        for key in spec.keys():
            if key == "FunctionName":
                func = self._lambdas.get_function_by_name_or_arn(spec[key])
                esm.function_arn = func.function_arn
            elif key == "BatchSize":
                esm.batch_size = spec[key]
            elif key == "Enabled":
                esm.enabled = spec[key]

        esm.last_modified = time.mktime(datetime.datetime.utcnow().timetuple())
        return esm

    def list_event_source_mappings(
        self, event_source_arn: str, function_name: str
    ) -> Iterable[EventSourceMapping]:
        esms = list(self._event_source_mappings.values())
        if event_source_arn:
            esms = list(filter(lambda x: x.event_source_arn == event_source_arn, esms))
        if function_name:
            esms = list(filter(lambda x: x.function_name == function_name, esms))
        return esms

    def get_function_by_arn(self, function_arn: str) -> Optional[LambdaFunction]:
        return self._lambdas.get_arn(function_arn)

    def delete_function(
        self, function_name: str, qualifier: Optional[str] = None
    ) -> None:
        self._lambdas.del_function(function_name, qualifier)

    def list_functions(
        self, func_version: Optional[str] = None
    ) -> Iterable[LambdaFunction]:
        if func_version == "ALL":
            return self._lambdas.all()
        return self._lambdas.latest()

    def send_sqs_batch(self, function_arn: str, messages: Any, queue_arn: str) -> bool:
        success = True
        for message in messages:
            func = self.get_function_by_arn(function_arn)
            result = self._send_sqs_message(func, message, queue_arn)  # type: ignore[arg-type]
            if not result:
                success = False
        return success

    def _send_sqs_message(
        self, func: LambdaFunction, message: Any, queue_arn: str
    ) -> bool:
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

        request_headers: Dict[str, Any] = {}
        response_headers: Dict[str, Any] = {}
        func.invoke(json.dumps(event), request_headers, response_headers)
        return "x-amz-function-error" not in response_headers

    def send_sns_message(
        self,
        function_name: str,
        message: str,
        subject: Optional[str] = None,
        qualifier: Optional[str] = None,
    ) -> None:
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
        func.invoke(json.dumps(event), {}, {})  # type: ignore[union-attr]

    def send_dynamodb_items(
        self, function_arn: str, items: List[Any], source: str
    ) -> Union[str, bytes]:
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
        return func.invoke(json.dumps(event), {}, {})  # type: ignore[union-attr]

    def send_log_event(
        self,
        function_arn: str,
        filter_name: str,
        log_group_name: str,
        log_stream_name: str,
        log_events: Any,
    ) -> None:
        data = {
            "messageType": "DATA_MESSAGE",
            "owner": self.account_id,
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
        func.invoke(json.dumps(event), {}, {})  # type: ignore[union-attr]

    def list_tags(self, resource: str) -> Dict[str, str]:
        return self._lambdas.get_function_by_name_or_arn(resource).tags

    def tag_resource(self, resource: str, tags: Dict[str, str]) -> None:
        fn = self._lambdas.get_function_by_name_or_arn(resource)
        fn.tags.update(tags)

    def untag_resource(self, resource: str, tagKeys: List[str]) -> None:
        fn = self._lambdas.get_function_by_name_or_arn(resource)
        for key in tagKeys:
            fn.tags.pop(key, None)

    def add_permission(
        self, function_name: str, qualifier: str, raw: str
    ) -> Dict[str, Any]:
        fn = self.get_function(function_name, qualifier)
        return fn.policy.add_statement(raw, qualifier)  # type: ignore[union-attr]

    def remove_permission(
        self, function_name: str, sid: str, revision: str = ""
    ) -> None:
        fn = self.get_function(function_name)
        fn.policy.del_statement(sid, revision)  # type: ignore[union-attr]

    def get_code_signing_config(self, function_name: str) -> Dict[str, Any]:
        fn = self.get_function(function_name)
        return fn.get_code_signing_config()

    def get_policy(self, function_name: str) -> str:
        fn = self.get_function(function_name)
        if not fn:
            raise UnknownFunctionException(function_name)
        return fn.policy.wire_format()  # type: ignore[union-attr]

    def update_function_code(
        self, function_name: str, qualifier: str, body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        fn: LambdaFunction = self.get_function(function_name, qualifier)

        if body.get("Publish", False):
            fn = self.publish_function(function_name)  # type: ignore[assignment]

        return fn.update_function_code(body)

    def update_function_configuration(
        self, function_name: str, qualifier: str, body: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        fn = self.get_function(function_name, qualifier)

        return fn.update_configuration(body) if fn else None

    def invoke(
        self,
        function_name: str,
        qualifier: str,
        body: Any,
        headers: Any,
        response_headers: Any,
    ) -> Optional[Union[str, bytes]]:
        """
        Invoking a Function with PackageType=Image is not yet supported.
        """
        fn = self.get_function(function_name, qualifier)
        if fn:
            payload = fn.invoke(body, headers, response_headers)
            response_headers["Content-Length"] = str(len(payload))
            return payload
        else:
            return None

    def put_function_concurrency(
        self, function_name: str, reserved_concurrency: str
    ) -> str:
        fn = self.get_function(function_name)
        fn.reserved_concurrency = reserved_concurrency
        return fn.reserved_concurrency

    def delete_function_concurrency(self, function_name: str) -> Optional[str]:
        fn = self.get_function(function_name)
        fn.reserved_concurrency = None
        return fn.reserved_concurrency

    def get_function_concurrency(self, function_name: str) -> str:
        fn = self.get_function(function_name)
        return fn.reserved_concurrency


def do_validate_s3() -> bool:
    return os.environ.get("VALIDATE_LAMBDA_S3", "") in ["", "1", "true"]


lambda_backends = BackendDict(LambdaBackend, "lambda")
