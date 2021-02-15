from __future__ import unicode_literals

import json
from six.moves.urllib.parse import quote

import pytest
import sure  # noqa

import moto.server as server
from moto import mock_iot

"""
Test the different server responses
"""


@mock_iot
def test_iot_list():
    backend = server.create_backend_app("iot")
    test_client = backend.test_client()

    # just making sure that server is up
    res = test_client.get("/things")
    res.status_code.should.equal(200)


@pytest.mark.parametrize(
    "url_encode_arn",
    [
        pytest.param(True, id="Target Arn in Path is URL encoded"),
        pytest.param(False, id="Target Arn in Path is *not* URL encoded"),
    ],
)
@mock_iot
def test_list_attached_policies(url_encode_arn):
    backend = server.create_backend_app("iot")
    test_client = backend.test_client()

    result = test_client.post("/keys-and-certificate?setAsActive=true")
    result_dict = json.loads(result.data.decode("utf-8"))
    certificate_arn = result_dict["certificateArn"]

    test_client.post("/policies/my-policy", json={"policyDocument": {}})
    test_client.put("/target-policies/my-policy", json={"target": certificate_arn})

    if url_encode_arn:
        certificate_arn = quote(certificate_arn, safe="")

    result = test_client.post("/attached-policies/{}".format(certificate_arn))
    result.status_code.should.equal(200)
    result_dict = json.loads(result.data.decode("utf-8"))
    result_dict["policies"][0]["policyName"].should.equal("my-policy")
