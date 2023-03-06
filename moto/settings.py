import json
import os
import pathlib

from functools import lru_cache
from typing import Optional


TEST_SERVER_MODE = os.environ.get("TEST_SERVER_MODE", "0").lower() == "true"
INITIAL_NO_AUTH_ACTION_COUNT = float(
    os.environ.get("INITIAL_NO_AUTH_ACTION_COUNT", float("inf"))
)
DEFAULT_CONTAINER_REGISTRY = os.environ.get("DEFAULT_CONTAINER_REGISTRY", "docker.io")

S3_IGNORE_SUBDOMAIN_BUCKETNAME = os.environ.get(
    "S3_IGNORE_SUBDOMAIN_BUCKETNAME", ""
) in ["1", "true"]

# How many seconds to wait before we "validate" a new certificate in ACM.
ACM_VALIDATION_WAIT = int(os.environ.get("MOTO_ACM_VALIDATION_WAIT", "60"))

EC2_ENABLE_INSTANCE_TYPE_VALIDATION = bool(
    os.environ.get("MOTO_EC2_ENABLE_INSTANCE_TYPE_VALIDATION", False)
)

ENABLE_KEYPAIR_VALIDATION = bool(
    os.environ.get("MOTO_ENABLE_KEYPAIR_VALIDATION", False)
)

ENABLE_AMI_VALIDATION = bool(os.environ.get("MOTO_ENABLE_AMI_VALIDATION", False))


PRETTIFY_RESPONSES = bool(os.environ.get("MOTO_PRETTIFY_RESPONSES", False))


def get_sf_execution_history_type():
    """
    Determines which execution history events `get_execution_history` returns
    :returns: str representing the type of Step Function Execution Type events should be
        returned. Default value is SUCCESS, currently supports (SUCCESS || FAILURE)
    """
    return os.environ.get("SF_EXECUTION_HISTORY_TYPE", "SUCCESS")


def get_s3_custom_endpoints():
    endpoints = os.environ.get("MOTO_S3_CUSTOM_ENDPOINTS")
    if endpoints:
        return endpoints.split(",")
    return []


S3_UPLOAD_PART_MIN_SIZE = 5242880


def get_s3_default_key_buffer_size():
    return int(
        os.environ.get(
            "MOTO_S3_DEFAULT_KEY_BUFFER_SIZE", S3_UPLOAD_PART_MIN_SIZE - 1024
        )
    )


def ecs_new_arn_format() -> bool:
    # True by default - only the value 'false' will return false
    return os.environ.get("MOTO_ECS_NEW_ARN", "true").lower() != "false"


def allow_unknown_region() -> bool:
    return os.environ.get("MOTO_ALLOW_NONEXISTENT_REGION", "false").lower() == "true"


def lambda_stub_ecr() -> bool:
    # Whether to stub or mock ecr backend when deploying image based lambdas.
    # True => don't requiring image presence in moto ecr backend for `create_function`.
    # False => require image presence in moto ecr backend for `create_function`
    return os.environ.get("MOTO_LAMBDA_STUB_ECR", "TRUE").lower() != "false"


def moto_server_port() -> str:
    return os.environ.get("MOTO_PORT") or "5000"


@lru_cache()
def moto_server_host() -> str:
    if is_docker():
        return get_docker_host()
    else:
        return "http://host.docker.internal"


def moto_lambda_image() -> str:
    return os.environ.get("MOTO_DOCKER_LAMBDA_IMAGE", "mlupin/docker-lambda")


def moto_network_name() -> str:
    return os.environ.get("MOTO_DOCKER_NETWORK_NAME")


def moto_network_mode() -> str:
    return os.environ.get("MOTO_DOCKER_NETWORK_MODE")


def test_server_mode_endpoint() -> str:
    return os.environ.get(
        "TEST_SERVER_MODE_ENDPOINT", f"http://localhost:{moto_server_port()}"
    )


def is_docker() -> bool:
    path = pathlib.Path("/proc/self/cgroup")
    return (
        os.path.exists("/.dockerenv")
        or path.is_file()
        and any("docker" in line for line in path.read_text())
    )


def get_docker_host() -> str:
    try:
        cmd = "curl -s --unix-socket /run/docker.sock http://docker/containers/$HOSTNAME/json"
        container_info = os.popen(cmd).read()
        network_settings = json.loads(container_info)["NetworkSettings"]
        network_name = moto_network_name()
        if network_name and network_name in network_settings["Networks"]:
            _ip = network_settings["Networks"][network_name]["IPAddress"]
        else:
            _ip = network_settings["IPAddress"]
            if network_name:
                print(  # noqa
                    f"WARNING - Moto couldn't find network '{network_name}' - defaulting to {_ip}"
                )
        return f"http://{_ip}"
    except Exception as e:  # noqa
        print(  # noqa
            "WARNING - Unable to parse Docker API response. Defaulting to 'host.docker.internal'"
        )
        print(f"{type(e)}::{e}")  # noqa
        return "http://host.docker.internal"


def get_cognito_idp_user_pool_id_strategy() -> Optional[str]:
    return os.environ.get("MOTO_COGNITO_IDP_USER_POOL_ID_STRATEGY")
