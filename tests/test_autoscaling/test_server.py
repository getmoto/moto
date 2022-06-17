import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from tests import DEFAULT_ACCOUNT_ID

"""
Test the different server responses
"""


def test_describe_autoscaling_groups():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="autoscaling"
    )
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeLaunchConfigurations")

    res.data.should.contain(b"<DescribeLaunchConfigurationsResponse")
    res.data.should.contain(b"<LaunchConfigurations>")
