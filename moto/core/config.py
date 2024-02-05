import re
from typing import List, TypedDict


class _docker_config(TypedDict, total=False):
    use_docker: bool


class _passthrough_config(TypedDict, total=False):
    services: List[str]
    urls: List[str]


class _core_config(TypedDict, total=False):
    mock_credentials: bool
    passthrough: _passthrough_config
    reset_boto3_session: bool


class _iam_config(TypedDict, total=False):
    load_aws_managed_policies: bool


DefaultConfig = TypedDict(
    "DefaultConfig",
    {
        "batch": _docker_config,
        "core": _core_config,
        "lambda": _docker_config,
        "iam": _iam_config,
    },
    total=False,
)

default_user_config: DefaultConfig = {
    "batch": {"use_docker": True},
    "lambda": {"use_docker": True},
    "core": {
        "mock_credentials": True,
        "passthrough": {"urls": [], "services": []},
        "reset_boto3_session": True,
    },
    "iam": {"load_aws_managed_policies": False},
}


def passthrough_service(service: str) -> bool:
    passthrough_services = (
        default_user_config.get("core", {}).get("passthrough", {}).get("services", [])
    )
    return service in passthrough_services


def passthrough_url(clean_url: str) -> bool:
    passthrough_urls = (
        default_user_config.get("core", {}).get("passthrough", {}).get("urls", [])
    )
    return any([re.match(url, clean_url) for url in passthrough_urls])


def mock_credentials() -> bool:
    return (
        default_user_config.get("core", {}).get("mock_credentials", True) is not False
    )
