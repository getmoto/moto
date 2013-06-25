import sys

from flask import Flask
from werkzeug.routing import BaseConverter

from moto.dynamodb import dynamodb_backend  # flake8: noqa
from moto.ec2 import ec2_backend  # flake8: noqa
from moto.s3 import s3_backend  # flake8: noqa
from moto.ses import ses_backend  # flake8: noqa
from moto.sqs import sqs_backend  # flake8: noqa
from moto.sts import sts_backend  # flake8: noqa

from moto.core.utils import convert_flask_to_httpretty_response

app = Flask(__name__)
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]


class RegexConverter(BaseConverter):
    # http://werkzeug.pocoo.org/docs/routing/#custom-converters
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def configure_urls(service):
    module = sys.modules[__name__]
    backend = getattr(module, "{}_backend".format(service))
    from werkzeug.routing import Map
    # Reset view functions to reset the app
    app.view_functions = {}
    app.url_map = Map()
    app.url_map.converters['regex'] = RegexConverter
    for url_path, handler in backend.flask_paths.iteritems():
        app.route(url_path, methods=HTTP_METHODS)(convert_flask_to_httpretty_response(handler))


def main(args=sys.argv):
    if len(args) not in range(2, 4):
        print("Usage: moto_server <service> [port]")
        sys.exit(1)
    service_name = args[1]
    configure_urls(service_name)
    try:
        port = int(args[2])
    except IndexError:
        port = None

    app.testing = True
    app.run(port=port)

if __name__ == '__main__':
    main()
