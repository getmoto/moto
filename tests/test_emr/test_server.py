import moto.server as server
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1

"""
Test the different server responses
"""


def test_describe_jobflows():
    backend = server.create_backend_app("emr")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "ElasticMapReduce.DescribeJobFlows",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)

    assert b"JobFlows" in res.data
