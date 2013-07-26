import sys
import argparse

from flask import Flask
from werkzeug.routing import BaseConverter

from moto.backends import BACKENDS
from moto.core.utils import convert_flask_to_httpretty_response

app = Flask(__name__)
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]


class RegexConverter(BaseConverter):
    # http://werkzeug.pocoo.org/docs/routing/#custom-converters
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def configure_urls(service):
    backend = BACKENDS[service]
    from werkzeug.routing import Map
    # Reset view functions to reset the app
    app.view_functions = {}
    app.url_map = Map()
    app.url_map.converters['regex'] = RegexConverter
    for url_path, handler in backend.flask_paths.iteritems():
        app.route(url_path, methods=HTTP_METHODS)(convert_flask_to_httpretty_response(handler))


def main(argv=sys.argv[1:]):
    available_services = BACKENDS.keys()

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
