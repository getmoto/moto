import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_list_streams():
    backend = server.create_backend_app("kinesis")
    test_client = backend.test_client()

    res = test_client.get("/?Action=ListStreams")

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data == {
        "HasMoreStreams": False,
        "StreamNames": [],
        "StreamSummaries": [],
    }
