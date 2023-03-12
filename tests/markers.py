import pytest

from moto import settings

requires_docker = pytest.mark.requires_docker

if settings.SKIP_REQUIRES_DOCKER:
    requires_docker = pytest.mark.skip(reason="running docker required")
