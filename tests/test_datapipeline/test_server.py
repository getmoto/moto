import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_datapipeline
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


@mock_datapipeline
def test_list_streams():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="datapipeline"
    )
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        data={"pipelineIds": ["ASdf"]},
        headers={"X-Amz-Target": "DataPipeline.DescribePipelines"},
    )

    json_data = json.loads(res.data.decode("utf-8"))
    json_data.should.equal({"pipelineDescriptionList": []})
