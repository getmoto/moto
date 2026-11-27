"""Test the different server responses."""

import moto.server as server


def test_resourcegroupstaggingapi_list():
    backend = server.create_backend_app("resourcegroupstaggingapi")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "ResourceGroupsTaggingAPI_20170126.GetResources",
        "Content-Type": "application/x-amz-json-1.1",
    }
    resp = test_client.post("/", headers=headers, json={})
    assert resp.status_code == 200
    assert b"ResourceTagMappingList" in resp.data
