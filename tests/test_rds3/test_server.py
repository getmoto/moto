from __future__ import unicode_literals

import sure  # noqa

import moto.server as server


def test_list_databases():
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()
    # TODO: Need to figure out how to call this with boto3.client (change url?)
    # or figure out how to put the request together properly with Flask client.
    resp = test_client.action_data("DescribeDBInstances")
    resp.should.contain("DescribeDBInstancesResponse")
