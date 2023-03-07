import docker
import pytest
from docker.errors import DockerException


def validate_docker_is_available() -> bool:
    try:
        docker.from_env()
        return True
    except DockerException:
        return False


requires_docker = pytest.mark.skipif(
    not validate_docker_is_available(), reason="running docker required"
)
