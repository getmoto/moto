import sure  # noqa # pylint: disable=unused-import

import moto.server as server

"""
Test the different server responses
"""


def test_describe_autoscaling_groups():
    backend = server.create_backend_app("autoscaling")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeLaunchConfigurations")

    res.data.should.contain(b"<DescribeLaunchConfigurationsResponse")
    res.data.should.contain(b"<LaunchConfigurations>")
