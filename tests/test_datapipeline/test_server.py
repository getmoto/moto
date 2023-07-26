import json

import moto.server as server
from moto import mock_datapipeline

"""
Test the different server responses
"""


@mock_datapipeline
def test_list_streams():
    backend = server.create_backend_app("datapipeline")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        data={"pipelineIds": ["ASdf"]},
        headers={"X-Amz-Target": "DataPipeline.DescribePipelines"},
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data == {"pipelineDescriptionList": []}
