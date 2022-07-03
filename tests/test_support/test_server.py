import sure  # noqa # pylint: disable=unused-import

import moto.server as server

"""
Test the different server responses for support
"""


def test_describe_trusted_advisor_checks_returns_check_names():
    """
    Check that the correct names of checks are returned
    """

    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")

    res.data.should.contain(b"Low Utilization Amazon EC2 Instances")
    res.data.should.contain(b"ELB Application Load Balancers")


def test_describe_trusted_advisor_checks_does_not_return_wrong_check_names():
    """
    Check that the wrong names of checks are not returned
    """

    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")

    res.data.doesnot.contain(b"Low Utilization Amazon Foo Instances")
    res.data.doesnot.contain(b"ELB Application Bar Balancers")


def test_describe_trusted_advisor_checks_returns_check_ids():
    """
    Check that some random ids of checks are returned
    """
    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")
    res.data.should.contain(b"DAvU99Dc4C")
    res.data.should.contain(b"zXCkfM1nI3")


def test_describe_trusted_advisor_checks_does_not_return_wrong_id():
    """
    Check that some wrong ids of checks are not returned
    """
    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")
    res.data.doesnot.contain(b"DAvU99DcBAR")
    res.data.doesnot.contain(b"zXCkfM1nFOO")
