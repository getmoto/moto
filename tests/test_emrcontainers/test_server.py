"""Test different server responses."""
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_emrcontainers


@mock_emrcontainers
def test_emrcontainers_list():
    backend = server.create_backend_app("emr-containers")
    test_client = backend.test_client()
    # do test