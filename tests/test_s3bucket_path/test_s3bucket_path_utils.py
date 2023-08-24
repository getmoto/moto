from moto.s3bucket_path.utils import bucket_name_from_url


def test_base_url():
    assert bucket_name_from_url("https://s3.amazonaws.com/") is None


def test_localhost_bucket():
    assert bucket_name_from_url("https://localhost:5000/wfoobar/abc") == "wfoobar"


def test_localhost_without_bucket():
    assert bucket_name_from_url("https://www.localhost:5000") is None
