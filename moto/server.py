import sys
import argparse

from flask import Flask
from werkzeug.routing import BaseConverter

from moto.dynamodb import dynamodb_backend  # flake8: noqa
from moto.ec2 import ec2_backend  # flake8: noqa
from moto.elb import elb_backend  # flake8: noqa
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


def main(argv=sys.argv):
    # Yes, I'm using those imports in the beginning of the file to create a
    # dynamic list of available services to be shown in the help text when the
    # user tries to interact with moto_server.
    available_services = [
        x.split('_')[0] for x in globals() if x.endswith('_backend')]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'service', type=str,
        choices=available_services,
        help='Choose which mechanism you want to run')
    parser.add_argument(
        '-H', '--host', type=str,
        help='Which host to bind',
        default='0.0.0.0')
    parser.add_argument(
        '-p', '--port', type=int,
        help='Port number to use for connection',
        default=5000)

    args = parser.parse_args(argv)

    configure_urls(args.service)

    app.testing = True
    app.run(host=args.host, port=args.port)

if __name__ == '__main__':
    main()
