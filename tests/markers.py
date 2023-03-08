import docker
import pytest
from docker.errors import DockerException

from moto import settings


def _docker_is_available() -> bool:
    try:
        docker.from_env()
        return True
    except DockerException:
        return False


requires_docker = pytest.mark.xfail(
    not _docker_is_available() and settings.SKIP_DOCKER_REQUIRED,
    reason="running docker required",
)
