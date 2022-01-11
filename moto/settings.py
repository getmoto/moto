import json
import os

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


def ecs_new_arn_format():
    return os.environ.get("MOTO_ECS_NEW_ARN", "false").lower() == "true"


def allow_unknown_region():
    return os.environ.get("MOTO_ALLOW_NONEXISTENT_REGION", "false").lower() == "true"


def moto_server_port():
    return os.environ.get("MOTO_PORT") or "5000"


def moto_server_host():
    _port = moto_server_port()
    if is_docker():
        host = get_docker_host()
    else:
        host = "http://host.docker.internal"
    return f"{host}:{_port}"


def is_docker():
    path = "/proc/self/cgroup"
    return (
        os.path.exists("/.dockerenv")
        or os.path.isfile(path)
        and any("docker" in line for line in open(path))
    )


def get_docker_host():
    try:
        cmd = "curl -s --unix-socket /run/docker.sock http://docker/containers/$HOSTNAME/json"
        container_info = os.popen(cmd).read()
        _ip = json.loads(container_info)["NetworkSettings"]["IPAddress"]
        return f"http://{_ip}"
    except:  # noqa
        return "http://host.docker.internal"
