from __future__ import unicode_literals

import sure  # noqa

import moto.server as server

"""
Test the different server responses
"""


def test_resourcegroupstaggingapi_list():
    backend = server.create_backend_app("resourcegroupstaggingapi")
    test_client = backend.test_client()
    # do test

    headers = {
        "X-Amz-Target": "ResourceGroupsTaggingAPI_20170126.GetResources",
        "X-Amz-Date": "20171114T234623Z",
    }
    resp = test_client.post("/", headers=headers, data="{}")

    assert resp.status_code == 200
    assert b"ResourceTagMappingList" in resp.data
