import sure  # noqa # pylint: disable=unused-import

import moto.server as server

"""
Test the different server responses
"""


def test_elbv2_describe_load_balancers():
    backend = server.create_backend_app("elbv2")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeLoadBalancers&Version=2015-12-01")

    res.data.should.contain(b"DescribeLoadBalancersResponse")
