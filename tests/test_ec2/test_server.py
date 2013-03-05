import re
import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("ec2")


def test_ec2_server_get():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=RunInstances&ImageId=ami-60a54009')

    groups = re.search("<instanceId>(.*)</instanceId>", res.data)
    instance_id = groups.groups()[0]

    res = test_client.get('/?Action=DescribeInstances')
    res.data.should.contain(instance_id)
