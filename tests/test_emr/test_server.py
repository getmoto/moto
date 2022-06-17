import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


def test_describe_jobflows():
    backend = server.create_backend_app(account_id=DEFAULT_ACCOUNT_ID, service="emr")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeJobFlows")

    res.data.should.contain(b"<DescribeJobFlowsResult>")
    res.data.should.contain(b"<JobFlows>")
