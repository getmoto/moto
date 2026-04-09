import json

import moto.server as server
from moto import mock_aws
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1


@mock_aws
def test_list_streams():
    backend = server.create_backend_app("kinesis")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "Kinesis_20131202.ListStreams",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data == {
        "HasMoreStreams": False,
        "StreamNames": [],
        "StreamSummaries": [],
    }
