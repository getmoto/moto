import sure  # noqa # pylint: disable=unused-import

import moto.server as server


def test_elasticache_describe_users():
    backend = server.create_backend_app("elasticache")
    test_client = backend.test_client()

    data = "Action=DescribeUsers"
    headers = {"Host": "elasticache.us-east-1.amazonaws.com"}
    resp = test_client.post("/", data=data, headers=headers)
    resp.status_code.should.equal(200)
    str(resp.data).should.contain("<UserId>default</UserId>")
