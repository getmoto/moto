import re
import sys
import argparse

from threading import Lock

from flask import Flask
from werkzeug.routing import BaseConverter
from werkzeug.serving import run_simple

from moto.backends import BACKENDS
from moto.core.utils import convert_flask_to_httpretty_response

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]


class DomainDispatcherApplication(object):
    """
    Dispatch requests to different applications based on the "Host:" header
    value. We'll match the host header value with the url_bases of each backend.
    """

    def __init__(self, create_app):
        self.create_app = create_app
        self.lock = Lock()
        self.app_instances = {}

    def get_backend_for_host(self, host):
        for backend in BACKENDS.itervalues():
            for url_base in backend.url_bases:
                if re.match(url_base, 'http://%s' % host):
                    return backend

        raise RuntimeError('Invalid host: "%s"' % host)

    def get_application(self, host):
        host = host.split(':')[0]
        with self.lock:
            backend = self.get_backend_for_host(host)
            app = self.app_instances.get(backend, None)
            if app is None:
                app = self.create_app(backend)
                self.app_instances[backend] = app
            return app

    def __call__(self, environ, start_response):
        backend_app = self.get_application(environ['HTTP_HOST'])
        return backend_app(environ, start_response)


class RegexConverter(BaseConverter):
    # http://werkzeug.pocoo.org/docs/routing/#custom-converters
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def create_backend_app(backend):
    from werkzeug.routing import Map

    # Create the backend_app
    backend_app = Flask(__name__)
    backend_app.debug = True

    # Reset view functions to reset the app
    backend_app.view_functions = {}
    backend_app.url_map = Map()
    backend_app.url_map.converters['regex'] = RegexConverter
    for url_path, handler in backend.flask_paths.iteritems():
        backend_app.route(url_path, methods=HTTP_METHODS)(convert_flask_to_httpretty_response(handler))

    return backend_app


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-H', '--host', type=str,
        help='Which host to bind',
        default='0.0.0.0')
    parser.add_argument(
        '-p', '--port', type=int,
        help='Port number to use for connection',
        default=5000)

    args = parser.parse_args(argv)

    # Wrap the main application
    main_app = DomainDispatcherApplication(create_backend_app)
    main_app.debug = True

    run_simple(args.host, args.port, main_app)

if __name__ == '__main__':
    main()
