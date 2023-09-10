"""Test different server responses."""

import moto.server as server


def test_elasticbeanstalk_describe():
    backend = server.create_backend_app("elasticbeanstalk")
    test_client = backend.test_client()

    data = "Action=DescribeApplications"
    headers = {"Host": "elasticbeanstalk.us-east-1.amazonaws.com"}
    resp = test_client.post("/", data=data, headers=headers)

    assert resp.status_code == 200
    assert "<Applications></Applications>" in str(resp.data)
