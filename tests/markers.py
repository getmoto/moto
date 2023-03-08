import pytest

from moto import settings
from moto.core.exceptions import MotoDockerException

requires_docker = pytest.mark.requires_docker

if settings.SKIP_REQUIRES_DOCKER:
    requires_docker = pytest.mark.skip(reason="running docker required")
elif settings.RAISE_DOCKER_EXCEPTION:
    requires_docker = pytest.mark.xfail(
        raises=MotoDockerException,
        reason="running docker required",
    )
