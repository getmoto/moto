"""Test the different server responses for support."""
import moto.server as server


def test_describe_trusted_advisor_checks_returns_check_names():
    """Check that the correct names of checks are returned."""

    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")

    assert b"Low Utilization Amazon EC2 Instances" in res.data
    assert b"ELB Application Load Balancers" in res.data


def test_describe_trusted_advisor_checks_does_not_return_wrong_check_names():
    """Check that the wrong names of checks are not returned."""

    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")

    assert b"Low Utilization Amazon Foo Instances" not in res.data
    assert b"ELB Application Bar Balancers" not in res.data


def test_describe_trusted_advisor_checks_returns_check_ids():
    """Check that some random ids of checks are returned."""
    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")
    assert b"DAvU99Dc4C" in res.data
    assert b"zXCkfM1nI3" in res.data


def test_describe_trusted_advisor_checks_does_not_return_wrong_id():
    """Check that some wrong ids of checks are not returned."""
    backend = server.create_backend_app("support")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeTrustedAdvisorChecks&Version=2015-12-01")
    assert b"DAvU99DcBAR" not in res.data
    assert b"zXCkfM1nFOO" not in res.data
