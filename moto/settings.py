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


def ssm_should_load_global_parameters():
    """
    SSM: Should we load the Global Infrastructure parameters
    https://aws.amazon.com/blogs/aws/new-query-for-aws-regions-endpoints-and-more-using-aws-systems-manager-parameter-store/
    :return:
    """
    return os.environ.get("MOTO_SSM_LOAD_GLOBAL_PARAMS", "0").lower() == "true"


def get_sf_execution_history_type():
    """
    Determines which execution history events `get_execution_history` returns
    :returns: str representing the type of Step Function Execution Type events should be
        returned. Default value is SUCCESS, currently supports (SUCCESS || FAILURE)
    """
    return os.environ.get("SF_EXECUTION_HISTORY_TYPE", "SUCCESS")
