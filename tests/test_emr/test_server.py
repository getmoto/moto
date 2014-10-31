from __future__ import unicode_literals
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_describe_jobflows():
    backend = server.create_backend_app("emr")
    test_client = backend.test_client()

    res = test_client.get('/?Action=DescribeJobFlows')

    res.data.should.contain(b'<DescribeJobFlowsResult>')
    res.data.should.contain(b'<JobFlows>')
