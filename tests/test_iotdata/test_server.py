from __future__ import unicode_literals

from urllib.parse import quote

import pytest
import sure  # noqa

import moto.server as server
from moto import mock_iotdata

"""
Test the different server responses
"""


@mock_iotdata
def test_iotdata_list():
    backend = server.create_backend_app("iot-data")
    test_client = backend.test_client()

    # just making sure that server is up
    thing_name = "nothing"
    res = test_client.get("/things/{}/shadow".format(thing_name))
    res.status_code.should.equal(404)


@pytest.mark.parametrize(
    "url_encode_topic",
    [
        pytest.param(True, id="Topic in Path is URL encoded"),
        pytest.param(False, id="Topic in Path is *not* URL encoded"),
    ],
)
@mock_iotdata
def test_publish(url_encode_topic):
    backend = server.create_backend_app("iot-data")
    test_client = backend.test_client()

    topic = "test/topic"
    topic_for_path = quote(topic, safe="") if url_encode_topic else topic

    result = test_client.post("/topics/{}".format(topic_for_path))
    result.status_code.should.equal(200)
