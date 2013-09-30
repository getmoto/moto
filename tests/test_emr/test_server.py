import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("emr")


def test_describe_jobflows():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=DescribeJobFlows')

    res.data.should.contain('<DescribeJobFlowsResult>')
    res.data.should.contain('<JobFlows>')
