import os

TEST_SERVER_MODE = os.environ.get("TEST_SERVER_MODE", "0").lower() == "true"
INITIAL_NO_AUTH_ACTION_COUNT = float(
    os.environ.get("INITIAL_NO_AUTH_ACTION_COUNT", float("inf"))
)


def get_sf_execution_history_type():
    """
    Determines which execution history events `get_execution_history` returns
    :returns: str representing the type of Step Function Execution Type events should be
        returned. Default value is SUCCESS, currently supports (SUCCESS || FAILURE)
    """
    return os.environ.get("SF_EXECUTION_HISTORY_TYPE", "SUCCESS")
