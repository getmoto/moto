from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_rds

'''
Test the different server responses
'''


@mock_rds
def test_list_databases():
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()

    res = test_client.get('/?Action=DescribeDBInstances')

    res.data.decode("utf-8").should.contain("<DescribeDBInstancesResult>")
