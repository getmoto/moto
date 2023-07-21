import moto.server as server

"""
Test the different server responses
"""


def test_elb_describe_instances():
    backend = server.create_backend_app("elb")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeLoadBalancers&Version=2015-12-01")

    assert b"DescribeLoadBalancersResponse" in res.data
