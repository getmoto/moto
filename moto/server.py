import argparse
import io
import json
import os
import signal
import sys
from functools import partial
from threading import Lock

from flask import Flask
from flask_cors import CORS
from flask.testing import FlaskClient

from urllib.parse import urlencode
from werkzeug.routing import BaseConverter
from werkzeug.serving import run_simple

import moto.backends as backends
import moto.backend_index as backend_index
from moto.core.utils import convert_flask_to_httpretty_response

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"]


DEFAULT_SERVICE_REGION = ("s3", "us-east-1")

# Map of unsigned calls to service-region as per AWS API docs
# https://docs.aws.amazon.com/cognito/latest/developerguide/resource-permissions.html#amazon-cognito-signed-versus-unsigned-apis
UNSIGNED_REQUESTS = {
    "AWSCognitoIdentityService": ("cognito-identity", "us-east-1"),
    "AWSCognitoIdentityProviderService": ("cognito-idp", "us-east-1"),
}
UNSIGNED_ACTIONS = {
    "AssumeRoleWithSAML": ("sts", "us-east-1"),
    "AssumeRoleWithWebIdentity": ("sts", "us-east-1"),
}

# Some services have v4 signing names that differ from the backend service name/id.
SIGNING_ALIASES = {
    "eventbridge": "events",
    "execute-api": "iot",
    "iotdata": "data.iot",
}

# Some services are only recognizable by the version
SERVICE_BY_VERSION = {"2009-04-15": "sdb"}


class DomainDispatcherApplication(object):
    """
    Dispatch requests to different applications based on the "Host:" header
    value. We'll match the host header value with the url_bases of each backend.
    """

    def __init__(self, create_app, service=None):
        self.create_app = create_app
        self.lock = Lock()
        self.app_instances = {}
        self.service = service
        self.backend_url_patterns = backend_index.backend_url_patterns

    def get_backend_for_host(self, host):

        if host == "moto_api":
            return host

        if self.service:
            return self.service

        if host in backends.BACKENDS:
            return host

        for backend, pattern in self.backend_url_patterns:
            if pattern.match("http://%s" % host):
                return backend

        if "amazonaws.com" in host:
            print(
                "Unable to find appropriate backend for {}."
                "Remember to add the URL to urls.py, and run scripts/update_backend_index.py to index it.".format(
                    host
                )
            )

    def infer_service_region_host(self, body, environ):
        auth = environ.get("HTTP_AUTHORIZATION")
        target = environ.get("HTTP_X_AMZ_TARGET")
        service = None
        if auth:
            # Signed request
            # Parse auth header to find service assuming a SigV4 request
            # https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html
            # ['Credential=sdffdsa', '20170220', 'us-east-1', 'sns', 'aws4_request']
            try:
                credential_scope = auth.split(",")[0].split()[1]
                _, _, region, service, _ = credential_scope.split("/")
                service = SIGNING_ALIASES.get(service.lower(), service)
                service = service.lower()
            except ValueError:
                # Signature format does not match, this is exceptional and we can't
                # infer a service-region. A reduced set of services still use
                # the deprecated SigV2, ergo prefer S3 as most likely default.
                # https://docs.aws.amazon.com/general/latest/gr/signature-version-2.html
                service, region = DEFAULT_SERVICE_REGION
        else:
            # Unsigned request
            action = self.get_action_from_body(body)
            if target:
                service, _ = target.split(".", 1)
                service, region = UNSIGNED_REQUESTS.get(service, DEFAULT_SERVICE_REGION)
            elif action and action in UNSIGNED_ACTIONS:
                # See if we can match the Action to a known service
                service, region = UNSIGNED_ACTIONS.get(action)
            if not service:
                service, region = self.get_service_from_body(body, environ)
            if not service:
                service, region = self.get_service_from_path(environ)
            if not service:
                # S3 is the last resort when the target is also unknown
                service, region = DEFAULT_SERVICE_REGION

        if service in ["budgets", "cloudfront"]:
            # Global Services - they do not have/expect a region
            host = f"{service}.amazonaws.com"
        elif service == "mediastore" and not target:
            # All MediaStore API calls have a target header
            # If no target is set, assume we're trying to reach the mediastore-data service
            host = "data.{service}.{region}.amazonaws.com".format(
                service=service, region=region
            )
        elif service == "dynamodb":
            if environ["HTTP_X_AMZ_TARGET"].startswith("DynamoDBStreams"):
                host = "dynamodbstreams"
            else:
                dynamo_api_version = (
                    environ["HTTP_X_AMZ_TARGET"].split("_")[1].split(".")[0]
                )
                # If Newer API version, use dynamodb2
                if dynamo_api_version > "20111205":
                    host = "dynamodb2"
        elif service == "sagemaker":
            host = "api.{service}.{region}.amazonaws.com".format(
                service=service, region=region
            )
        elif service == "timestream":
            host = "ingest.{service}.{region}.amazonaws.com".format(
                service=service, region=region
            )
        else:
            host = "{service}.{region}.amazonaws.com".format(
                service=service, region=region
            )

        return host

    def get_application(self, environ):
        path_info = environ.get("PATH_INFO", "")

        # The URL path might contain non-ASCII text, for instance unicode S3 bucket names
        if isinstance(path_info, bytes):
            path_info = path_info.decode("utf-8")

        if path_info.startswith("/moto-api") or path_info == "/favicon.ico":
            host = "moto_api"
        elif path_info.startswith("/latest/meta-data/"):
            host = "instance_metadata"
        else:
            host = environ["HTTP_HOST"].split(":")[0]

        with self.lock:
            backend = self.get_backend_for_host(host)
            if not backend:
                # No regular backend found; try parsing body/other headers
                body = self._get_body(environ)
                host = self.infer_service_region_host(body, environ)
                backend = self.get_backend_for_host(host)

            app = self.app_instances.get(backend, None)
            if app is None:
                app = self.create_app(backend)
                self.app_instances[backend] = app
            return app

    def _get_body(self, environ):
        body = None
        try:
            # AWS requests use querystrings as the body (Action=x&Data=y&...)
            simple_form = environ["CONTENT_TYPE"].startswith(
                "application/x-www-form-urlencoded"
            )
            request_body_size = int(environ["CONTENT_LENGTH"])
            if simple_form and request_body_size:
                body = environ["wsgi.input"].read(request_body_size).decode("utf-8")
        except (KeyError, ValueError):
            pass
        finally:
            if body:
                # We've consumed the body = need to reset it
                environ["wsgi.input"] = io.StringIO(body)
        return body

    def get_service_from_body(self, body, environ):
        # Some services have the SDK Version in the body
        # If the version is unique, we can derive the service from it
        version = self.get_version_from_body(body)
        if version and version in SERVICE_BY_VERSION:
            # Boto3/1.20.7 Python/3.8.10 Linux/5.11.0-40-generic Botocore/1.23.7 region/eu-west-1
            region = environ.get("HTTP_USER_AGENT", "").split("/")[-1]
            return SERVICE_BY_VERSION[version], region
        return None, None

    def get_version_from_body(self, body):
        try:
            body_dict = dict(x.split("=") for x in body.split("&"))
            return body_dict["Version"]
        except (AttributeError, KeyError, ValueError):
            return None

    def get_action_from_body(self, body):
        try:
            # AWS requests use querystrings as the body (Action=x&Data=y&...)
            body_dict = dict(x.split("=") for x in body.split("&"))
            return body_dict["Action"]
        except (AttributeError, KeyError, ValueError):
            return None

    def get_service_from_path(self, environ):
        # Moto sometimes needs to send a HTTP request to itself
        # In which case it will send a request to 'http://localhost/service_region/whatever'
        try:
            path_info = environ.get("PATH_INFO", "/")
            service, region = path_info[1 : path_info.index("/", 1)].split("_")
            return service, region
        except (AttributeError, KeyError, ValueError):
            return None, None

    def __call__(self, environ, start_response):
        backend_app = self.get_application(environ)
        return backend_app(environ, start_response)


class RegexConverter(BaseConverter):
    # http://werkzeug.pocoo.org/docs/routing/#custom-converters

    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


class AWSTestHelper(FlaskClient):
    def action_data(self, action_name, **kwargs):
        """
        Method calls resource with action_name and returns data of response.
        """
        opts = {"Action": action_name}
        opts.update(kwargs)
        res = self.get(
            "/?{0}".format(urlencode(opts)),
            headers={
                "Host": "{0}.us-east-1.amazonaws.com".format(self.application.service)
            },
        )
        return res.data.decode("utf-8")

    def action_json(self, action_name, **kwargs):
        """
        Method calls resource with action_name and returns object obtained via
        deserialization of output.
        """
        return json.loads(self.action_data(action_name, **kwargs))


def create_backend_app(service):
    from werkzeug.routing import Map

    # Create the backend_app
    backend_app = Flask(__name__)
    backend_app.debug = True
    backend_app.service = service
    CORS(backend_app)

    # Reset view functions to reset the app
    backend_app.view_functions = {}
    backend_app.url_map = Map()
    backend_app.url_map.converters["regex"] = RegexConverter
    backend = list(backends.get_backend(service).values())[0]
    for url_path, handler in backend.flask_paths.items():
        view_func = convert_flask_to_httpretty_response(handler)
        if handler.__name__ == "dispatch":
            endpoint = "{0}.dispatch".format(handler.__self__.__name__)
        else:
            endpoint = view_func.__name__

        original_endpoint = endpoint
        index = 2
        while endpoint in backend_app.view_functions:
            # HACK: Sometimes we map the same view to multiple url_paths. Flask
            # requires us to have different names.
            endpoint = original_endpoint + str(index)
            index += 1

        # Some services do not provide a URL path
        # I.e., boto3 sends a request to 'https://ingest.timestream.amazonaws.com'
        # Which means we have a empty url_path to catch this request - but Flask can't handle that
        if url_path:
            backend_app.add_url_rule(
                url_path,
                endpoint=endpoint,
                methods=HTTP_METHODS,
                view_func=view_func,
                strict_slashes=False,
            )

    backend_app.test_client_class = AWSTestHelper
    return backend_app


def signal_handler(reset_server_port, signum, frame):
    if reset_server_port:
        del os.environ["MOTO_PORT"]
    sys.exit(0)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()

    # Keep this for backwards compat
    parser.add_argument(
        "service",
        type=str,
        nargs="?",  # http://stackoverflow.com/a/4480202/731592
        default=os.environ.get("MOTO_SERVICE"),
    )
    parser.add_argument(
        "-H", "--host", type=str, help="Which host to bind", default="127.0.0.1"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port number to use for connection",
        default=int(os.environ.get("MOTO_PORT", 5000)),
    )
    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Reload server on a file change",
        default=False,
    )
    parser.add_argument(
        "-s",
        "--ssl",
        action="store_true",
        help="Enable SSL encrypted connection with auto-generated certificate (use https://... URL)",
        default=False,
    )
    parser.add_argument(
        "-c", "--ssl-cert", type=str, help="Path to SSL certificate", default=None
    )
    parser.add_argument(
        "-k", "--ssl-key", type=str, help="Path to SSL private key", default=None
    )

    args = parser.parse_args(argv)

    reset_server_port = False
    if "MOTO_PORT" not in os.environ:
        reset_server_port = True
        os.environ["MOTO_PORT"] = f"{args.port}"

    try:
        signal.signal(signal.SIGINT, partial(signal_handler, reset_server_port))
        signal.signal(signal.SIGTERM, partial(signal_handler, reset_server_port))
    except Exception:
        pass  # ignore "ValueError: signal only works in main thread"

    # Wrap the main application
    main_app = DomainDispatcherApplication(create_backend_app, service=args.service)
    main_app.debug = True

    ssl_context = None
    if args.ssl_key and args.ssl_cert:
        ssl_context = (args.ssl_cert, args.ssl_key)
    elif args.ssl:
        ssl_context = "adhoc"

    run_simple(
        args.host,
        args.port,
        main_app,
        threaded=True,
        use_reloader=args.reload,
        ssl_context=ssl_context,
    )


if __name__ == "__main__":
    main()
