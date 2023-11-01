import logging

import pytest

from tests.markers import requires_docker

logger = logging.getLogger(__name__)


@requires_docker
@pytest.mark.order(0)
def test_docker_package_is_available():
    try:
        import docker  # noqa: F401   # pylint: disable=unused-import
    except ImportError as err:
        logger.error("error running docker: %s", err)
        assert False, (
            "Docker package cannot be imported. "
            + f"This causes various tests to fail. Err: {err}"
        )


@requires_docker
@pytest.mark.order(0)
def test_docker_is_running_and_available():
    import docker
    from docker.errors import DockerException

    try:
        docker.from_env()
    except DockerException as err:
        logger.error("error running docker: %s", err)
        assert False, (
            "Docker seems not to be running. "
            + f"This causes various tests to fail. Err: {err}"
        )
