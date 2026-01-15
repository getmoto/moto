import moto.server as server
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1


def test_describe_trusted_advisor_checks_returns_check_names():
    """Check that the correct names of checks are returned."""

    backend = server.create_backend_app("support")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "AWSSupport_20130415.DescribeTrustedAdvisorChecks",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)

    assert b"Low Utilization Amazon EC2 Instances" in res.data
    assert b"ELB Application Load Balancers" in res.data


def test_describe_trusted_advisor_checks_does_not_return_wrong_check_names():
    """Check that the wrong names of checks are not returned."""

    backend = server.create_backend_app("support")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "AWSSupport_20130415.DescribeTrustedAdvisorChecks",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)

    assert b"Low Utilization Amazon Foo Instances" not in res.data
    assert b"ELB Application Bar Balancers" not in res.data


def test_describe_trusted_advisor_checks_returns_check_ids():
    """Check that some random ids of checks are returned."""
    backend = server.create_backend_app("support")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "AWSSupport_20130415.DescribeTrustedAdvisorChecks",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)
    assert b"DAvU99Dc4C" in res.data
    assert b"zXCkfM1nI3" in res.data


def test_describe_trusted_advisor_checks_does_not_return_wrong_id():
    """Check that some wrong ids of checks are not returned."""
    backend = server.create_backend_app("support")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "AWSSupport_20130415.DescribeTrustedAdvisorChecks",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)
    assert b"DAvU99DcBAR" not in res.data
    assert b"zXCkfM1nFOO" not in res.data
