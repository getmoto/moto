import moto.server as server

"""
Test the different server responses
"""


def test_describe_jobflows():
    backend = server.create_backend_app("emr")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeJobFlows")

    assert b"<DescribeJobFlowsResult>" in res.data
    assert b"<JobFlows>" in res.data
