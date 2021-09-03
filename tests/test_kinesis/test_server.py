import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_kinesis


@mock_kinesis
def test_list_streams():
    backend = server.create_backend_app("kinesis")
    test_client = backend.test_client()

    res = test_client.get("/?Action=ListStreams")

    json_data = json.loads(res.data.decode("utf-8"))
    json_data.should.equal({"HasMoreStreams": False, "StreamNames": []})
