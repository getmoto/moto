import moto.server as server


def test_elasticache_describe_users():
    backend = server.create_backend_app("elasticache")
    test_client = backend.test_client()

    data = "Action=DescribeUsers"
    headers = {"Host": "elasticache.us-east-1.amazonaws.com"}
    resp = test_client.post("/", data=data, headers=headers)
    assert resp.status_code == 200
    assert "<UserId>default</UserId>" in str(resp.data)
