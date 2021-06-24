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


def get_s3_default_key_buffer_size():
    return int(os.environ.get("MOTO_S3_DEFAULT_KEY_BUFFER_SIZE", 16 * 1024 * 1024))
