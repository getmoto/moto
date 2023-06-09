import moto.server as server

"""
Test the different server responses
"""


def test_describe_autoscaling_groups():
    backend = server.create_backend_app("autoscaling")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeLaunchConfigurations")

    assert b"<DescribeLaunchConfigurationsResponse" in res.data
    assert b"<LaunchConfigurations>" in res.data
