"""Test different server responses."""
import sure  # noqa # pylint: disable=unused-import

import moto.server as server


def test_emrserverless_list():
    backend = server.create_backend_app("emr-serverless")
    test_client = backend.test_client()

    resp = test_client.get("/applications")
    resp.status_code.should.equal(200)
    str(resp.data).should.contain("applications")
