from __future__ import unicode_literals
import re
import sure  # noqa

import moto.server as server
from tests import EXAMPLE_AMI_ID

"""
Test the different server responses
"""


def test_ec2_server_get():
    backend = server.create_backend_app("ec2")
    test_client = backend.test_client()

    res = test_client.get(
        "/?Action=RunInstances&ImageId=" + EXAMPLE_AMI_ID,
        headers={"Host": "ec2.us-east-1.amazonaws.com"},
    )

    groups = re.search("<instanceId>(.*)</instanceId>", res.data.decode("utf-8"))
    instance_id = groups.groups()[0]

    res = test_client.get("/?Action=DescribeInstances")
    res.data.decode("utf-8").should.contain(instance_id)
