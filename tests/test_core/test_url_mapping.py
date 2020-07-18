from __future__ import unicode_literals
import sure  # noqa

from moto.core.utils import convert_regex_to_flask_path


def test_flask_path_converting_simple():
    convert_regex_to_flask_path("/").should.equal("/")
    convert_regex_to_flask_path("/$").should.equal("/")

    convert_regex_to_flask_path("/foo").should.equal("/foo")

    convert_regex_to_flask_path("/foo/bar/").should.equal("/foo/bar/")


def test_flask_path_converting_regex():
    convert_regex_to_flask_path("/(?P<key_name>[a-zA-Z0-9\-_]+)").should.equal(
        '/<regex("[a-zA-Z0-9\-_]+"):key_name>'
    )

    convert_regex_to_flask_path("(?P<account_id>\d+)/(?P<queue_name>.*)$").should.equal(
        '<regex("\d+"):account_id>/<regex(".*"):queue_name>'
    )
