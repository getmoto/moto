from moto.core.utils import convert_regex_to_flask_path


def test_flask_path_converting_simple() -> None:
    assert convert_regex_to_flask_path("/") == "/"
    assert convert_regex_to_flask_path("/$") == "/"

    assert convert_regex_to_flask_path("/foo") == "/foo"

    assert convert_regex_to_flask_path("/foo/bar/") == "/foo/bar/"


def test_flask_path_converting_regex() -> None:
    assert (
        convert_regex_to_flask_path(r"/(?P<key_name>[a-zA-Z0-9\-_]+)")
        == r'/<regex("[a-zA-Z0-9\-_]+"):key_name>'
    )

    assert (
        convert_regex_to_flask_path(r"(?P<account_id>\d+)/(?P<queue_name>.*)$")
        == r'<regex("\d+"):account_id>/<regex(".*"):queue_name>'
    )
