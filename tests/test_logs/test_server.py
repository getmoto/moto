"""Test different server responses."""
import sure  # noqa # pylint: disable=unused-import

import moto.server as server


def test_logs_list():
    backend = server.create_backend_app("logs")
    test_client = backend.test_client()

    resp = test_client.get("/")
    resp.status_code.should.equal(200)
    str(resp.data).should.contain("?")
