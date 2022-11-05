import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server


def test_dax_list():
    backend = server.create_backend_app("dax")
    test_client = backend.test_client()

    resp = test_client.post(
        "/", headers={"X-Amz-Target": "AmazonDAXV3.DescribeClusters"}, data="{}"
    )
    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equal({"Clusters": [], "NextToken": None})
