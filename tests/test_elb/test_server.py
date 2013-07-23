import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("elb")


def test_elb_describe_instances():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=DescribeLoadBalancers')

    res.data.should.contain('DescribeLoadBalancersResponse')
    res.data.should.contain('LoadBalancerName')
