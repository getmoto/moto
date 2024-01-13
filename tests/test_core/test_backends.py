from moto.backends import get_service_from_url


def test_get_service_from_url() -> None:
    assert get_service_from_url("https://s3.amazonaws.com") == "s3"
    assert get_service_from_url("https://bucket.s3.amazonaws.com") == "s3"
    assert get_service_from_url("https://unknown.com") is None
