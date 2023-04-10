from moto import server as server


def test_list_tags():
    test_client = server.create_backend_app("scheduler").test_client()
    res = test_client.get(
        "/tags/arn%3Aaws%3Ascheduler%3Aus-east-1%3A123456789012%3Aschedule%2Fdefault%2Fmy-schedule"
    )

    assert res.data == b'{"Tags": []}'
