# -*- coding: utf-8 -*-
import functools
import inspect
import os
import random
import re
import string
import types
from abc import abstractmethod
from io import BytesIO
from collections import defaultdict

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version

from botocore.config import Config
from botocore.handlers import BUILTIN_HANDLERS
from botocore.awsrequest import AWSResponse
from distutils.version import LooseVersion
from http.client import responses as http_responses
from urllib.parse import urlparse
from werkzeug.wrappers import Request

from moto import settings
import responses
from moto.packages.httpretty import HTTPretty
from unittest.mock import patch
from .utils import (
    convert_httpretty_response,
    convert_regex_to_flask_path,
    convert_flask_to_responses_response,
)

ACCOUNT_ID = os.environ.get("MOTO_ACCOUNT_ID", "123456789012")


class BaseMockAWS:
    nested_count = 0
    mocks_active = False

    def __init__(self, backends):
        from moto.instance_metadata import instance_metadata_backend
        from moto.core import moto_api_backend

        self.backends = backends

        self.backends_for_urls = {}
        default_backends = {
            "instance_metadata": instance_metadata_backend,
            "moto_api": moto_api_backend,
        }
        self.backends_for_urls.update(self.backends)
        self.backends_for_urls.update(default_backends)

        self.FAKE_KEYS = {
            "AWS_ACCESS_KEY_ID": "foobar_key",
            "AWS_SECRET_ACCESS_KEY": "foobar_secret",
        }
        self.ORIG_KEYS = {}
        self.default_session_mock = patch("boto3.DEFAULT_SESSION", None)

        if self.__class__.nested_count == 0:
            self.reset()

    def __call__(self, func, reset=True):
        if inspect.isclass(func):
            return self.decorate_class(func)
        return self.decorate_callable(func, reset)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self, reset=True):
        if not self.__class__.mocks_active:
            self.default_session_mock.start()
            self.mock_env_variables()
            self.__class__.mocks_active = True

        self.__class__.nested_count += 1
        if reset:
            for backend in self.backends.values():
                backend.reset()

        self.enable_patching()

    def stop(self):
        self.__class__.nested_count -= 1

        if self.__class__.nested_count < 0:
            raise RuntimeError("Called stop() before start().")

        if self.__class__.nested_count == 0:
            if self.__class__.mocks_active:
                try:
                    self.default_session_mock.stop()
                except RuntimeError:
                    # We only need to check for this exception in Python 3.6 and 3.7
                    # https://bugs.python.org/issue36366
                    pass
                self.unmock_env_variables()
                self.__class__.mocks_active = False
            self.disable_patching()

    def decorate_callable(self, func, reset):
        def wrapper(*args, **kwargs):
            self.start(reset=reset)
            try:
                result = func(*args, **kwargs)
            finally:
                self.stop()
            return result

        functools.update_wrapper(wrapper, func)
        wrapper.__wrapped__ = func
        return wrapper

    def decorate_class(self, klass):
        for attr in dir(klass):
            if attr.startswith("_"):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue
            if not hasattr(attr_value, "__name__"):
                continue

            # Check if this is a classmethod. If so, skip patching
            if inspect.ismethod(attr_value) and attr_value.__self__ is klass:
                continue

            # Check if this is a staticmethod. If so, skip patching
            for cls in inspect.getmro(klass):
                if attr_value.__name__ not in cls.__dict__:
                    continue
                bound_attr_value = cls.__dict__[attr_value.__name__]
                if not isinstance(bound_attr_value, staticmethod):
                    break
            else:
                # It is a staticmethod, skip patching
                continue

            try:
                setattr(klass, attr, self(attr_value, reset=False))
            except TypeError:
                # Sometimes we can't set this for built-in types
                continue
        return klass

    def mock_env_variables(self):
        # "Mock" the AWS credentials as they can't be mocked in Botocore currently
        # self.env_variables_mocks = mock.patch.dict(os.environ, FAKE_KEYS)
        # self.env_variables_mocks.start()
        for k, v in self.FAKE_KEYS.items():
            self.ORIG_KEYS[k] = os.environ.get(k, None)
            os.environ[k] = v

    def unmock_env_variables(self):
        # This doesn't work in Python2 - for some reason, unmocking clears the entire os.environ dict
        # Obviously bad user experience, and also breaks pytest - as it uses PYTEST_CURRENT_TEST as an env var
        # self.env_variables_mocks.stop()
        for k, v in self.ORIG_KEYS.items():
            if v:
                os.environ[k] = v
            else:
                del os.environ[k]


class HttprettyMockAWS(BaseMockAWS):
    def reset(self):
        HTTPretty.reset()

    def enable_patching(self):
        if not HTTPretty.is_enabled():
            HTTPretty.enable()

        for method in HTTPretty.METHODS:
            for backend in self.backends_for_urls.values():
                for key, value in backend.urls.items():
                    HTTPretty.register_uri(
                        method=method,
                        uri=re.compile(key),
                        body=convert_httpretty_response(value),
                    )

    def disable_patching(self):
        HTTPretty.disable()
        HTTPretty.reset()


RESPONSES_METHODS = [
    responses.GET,
    responses.DELETE,
    responses.HEAD,
    responses.OPTIONS,
    responses.PATCH,
    responses.POST,
    responses.PUT,
]


class CallbackResponse(responses.CallbackResponse):
    """
    Need to subclass so we can change a couple things
    """

    def get_response(self, request):
        """
        Need to override this so we can pass decode_content=False
        """
        if not isinstance(request, Request):
            url = urlparse(request.url)
            if request.body is None:
                body = None
            elif isinstance(request.body, str):
                body = BytesIO(request.body.encode("UTF-8"))
            elif hasattr(request.body, "read"):
                body = BytesIO(request.body.read())
            else:
                body = BytesIO(request.body)
            req = Request.from_values(
                path="?".join([url.path, url.query]),
                input_stream=body,
                content_length=request.headers.get("Content-Length"),
                content_type=request.headers.get("Content-Type"),
                method=request.method,
                base_url="{scheme}://{netloc}".format(
                    scheme=url.scheme, netloc=url.netloc
                ),
                headers=[(k, v) for k, v in request.headers.items()],
            )
            request = req
        headers = self.get_headers()

        result = self.callback(request)
        if isinstance(result, Exception):
            raise result

        status, r_headers, body = result
        body = responses._handle_body(body)
        headers.update(r_headers)

        return responses.HTTPResponse(
            status=status,
            reason=http_responses.get(status),
            body=body,
            headers=headers,
            preload_content=False,
            # Need to not decode_content to mimic requests
            decode_content=False,
        )

    def _url_matches(self, url, other, match_querystring=False):
        """
        Need to override this so we can fix querystrings breaking regex matching
        """
        if not match_querystring:
            other = other.split("?", 1)[0]

        if responses._is_string(url):
            if responses._has_unicode(url):
                url = responses._clean_unicode(url)
                if not isinstance(other, str):
                    other = other.encode("ascii").decode("utf8")
            return self._url_matches_strict(url, other)
        elif isinstance(url, responses.Pattern) and url.match(other):
            return True
        else:
            return False


botocore_mock = responses.RequestsMock(
    assert_all_requests_are_fired=False,
    target="botocore.vendored.requests.adapters.HTTPAdapter.send",
)

responses_mock = responses.RequestsMock(assert_all_requests_are_fired=False)
# Add passthrough to allow any other requests to work
# Since this uses .startswith, it applies to http and https requests.
responses_mock.add_passthru("http")


def _find_first_match_legacy(self, request):
    matches = []
    for i, match in enumerate(self._matches):
        if match.matches(request):
            matches.append(match)

    # Look for implemented callbacks first
    implemented_matches = [
        m
        for m in matches
        if type(m) is not CallbackResponse or m.callback != not_implemented_callback
    ]
    if implemented_matches:
        return implemented_matches[0]
    elif matches:
        # We had matches, but all were of type not_implemented_callback
        return matches[0]
    return None


def _find_first_match(self, request):
    matches = []
    match_failed_reasons = []
    for i, match in enumerate(self._matches):
        match_result, reason = match.matches(request)
        if match_result:
            matches.append(match)
        else:
            match_failed_reasons.append(reason)

    # Look for implemented callbacks first
    implemented_matches = [
        m
        for m in matches
        if type(m) is not CallbackResponse or m.callback != not_implemented_callback
    ]
    if implemented_matches:
        return implemented_matches[0], []
    elif matches:
        # We had matches, but all were of type not_implemented_callback
        return matches[0], match_failed_reasons

    return None, match_failed_reasons


# Modify behaviour of the matcher to only/always return the first match
# Default behaviour is to return subsequent matches for subsequent requests, which leads to https://github.com/spulec/moto/issues/2567
#  - First request matches on the appropriate S3 URL
#  - Same request, executed again, will be matched on the subsequent match, which happens to be the catch-all, not-yet-implemented, callback
# Fix: Always return the first match
RESPONSES_VERSION = version("responses")
if LooseVersion(RESPONSES_VERSION) < LooseVersion("0.12.1"):
    responses_mock._find_match = types.MethodType(
        _find_first_match_legacy, responses_mock
    )
else:
    responses_mock._find_match = types.MethodType(_find_first_match, responses_mock)


BOTOCORE_HTTP_METHODS = ["GET", "DELETE", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]


class MockRawResponse(BytesIO):
    def __init__(self, input):
        if isinstance(input, str):
            input = input.encode("utf-8")
        super(MockRawResponse, self).__init__(input)

    def stream(self, **kwargs):
        contents = self.read()
        while contents:
            yield contents
            contents = self.read()


class BotocoreStubber:
    def __init__(self):
        self.enabled = False
        self.methods = defaultdict(list)

    def reset(self):
        self.methods.clear()

    def register_response(self, method, pattern, response):
        matchers = self.methods[method]
        matchers.append((pattern, response))

    def __call__(self, event_name, request, **kwargs):
        if not self.enabled:
            return None
        response = None
        response_callback = None
        found_index = None
        matchers = self.methods.get(request.method)

        base_url = request.url.split("?", 1)[0]
        for i, (pattern, callback) in enumerate(matchers):
            if pattern.match(base_url):
                if found_index is None:
                    found_index = i
                    response_callback = callback
                else:
                    matchers.pop(found_index)
                    break

        if response_callback is not None:
            for header, value in request.headers.items():
                if isinstance(value, bytes):
                    request.headers[header] = value.decode("utf-8")
            status, headers, body = response_callback(
                request, request.url, request.headers
            )
            body = MockRawResponse(body)
            response = AWSResponse(request.url, status, headers, body)

        return response


botocore_stubber = BotocoreStubber()
BUILTIN_HANDLERS.append(("before-send", botocore_stubber))


def not_implemented_callback(request):
    status = 400
    headers = {}
    response = "The method is not implemented"

    return status, headers, response


class BotocoreEventMockAWS(BaseMockAWS):
    def reset(self):
        botocore_stubber.reset()
        responses_mock.reset()

    def enable_patching(self):
        botocore_stubber.enabled = True
        for method in BOTOCORE_HTTP_METHODS:
            for backend in self.backends_for_urls.values():
                for key, value in backend.urls.items():
                    pattern = re.compile(key)
                    botocore_stubber.register_response(method, pattern, value)

        if not hasattr(responses_mock, "_patcher") or not hasattr(
            responses_mock._patcher, "target"
        ):
            responses_mock.start()

        for method in RESPONSES_METHODS:
            # for backend in default_backends.values():
            for backend in self.backends_for_urls.values():
                for key, value in backend.urls.items():
                    responses_mock.add(
                        CallbackResponse(
                            method=method,
                            url=re.compile(key),
                            callback=convert_flask_to_responses_response(value),
                            stream=True,
                            match_querystring=False,
                        )
                    )
            responses_mock.add(
                CallbackResponse(
                    method=method,
                    url=re.compile(r"https?://.+\.amazonaws.com/.*"),
                    callback=not_implemented_callback,
                    stream=True,
                    match_querystring=False,
                )
            )
            botocore_mock.add(
                CallbackResponse(
                    method=method,
                    url=re.compile(r"https?://.+\.amazonaws.com/.*"),
                    callback=not_implemented_callback,
                    stream=True,
                    match_querystring=False,
                )
            )

    def disable_patching(self):
        botocore_stubber.enabled = False
        self.reset()

        try:
            responses_mock.stop()
        except RuntimeError:
            pass


MockAWS = BotocoreEventMockAWS


class ServerModeMockAWS(BaseMockAWS):
    def reset(self):
        call_reset_api = os.environ.get("MOTO_CALL_RESET_API")
        if not call_reset_api or call_reset_api.lower() != "false":
            import requests

            requests.post("http://localhost:5000/moto-api/reset")

    def enable_patching(self):
        if self.__class__.nested_count == 1:
            # Just started
            self.reset()

        from boto3 import client as real_boto3_client, resource as real_boto3_resource

        def fake_boto3_client(*args, **kwargs):
            region = self._get_region(*args, **kwargs)
            if region:
                if "config" in kwargs:
                    kwargs["config"].__dict__["user_agent_extra"] += " region/" + region
                else:
                    config = Config(user_agent_extra="region/" + region)
                    kwargs["config"] = config
            if "endpoint_url" not in kwargs:
                kwargs["endpoint_url"] = "http://localhost:5000"
            return real_boto3_client(*args, **kwargs)

        def fake_boto3_resource(*args, **kwargs):
            if "endpoint_url" not in kwargs:
                kwargs["endpoint_url"] = "http://localhost:5000"
            return real_boto3_resource(*args, **kwargs)

        self._client_patcher = patch("boto3.client", fake_boto3_client)
        self._resource_patcher = patch("boto3.resource", fake_boto3_resource)
        self._client_patcher.start()
        self._resource_patcher.start()

    def _get_region(self, *args, **kwargs):
        if "region_name" in kwargs:
            return kwargs["region_name"]
        if type(args) == tuple and len(args) == 2:
            service, region = args
            return region
        return None

    def disable_patching(self):
        if self._client_patcher:
            self._client_patcher.stop()
            self._resource_patcher.stop()


class Model(type):
    def __new__(self, clsname, bases, namespace):
        cls = super(Model, self).__new__(self, clsname, bases, namespace)
        cls.__models__ = {}
        for name, value in namespace.items():
            model = getattr(value, "__returns_model__", False)
            if model is not False:
                cls.__models__[model] = name
        for base in bases:
            cls.__models__.update(getattr(base, "__models__", {}))
        return cls

    @staticmethod
    def prop(model_name):
        """decorator to mark a class method as returning model values"""

        def dec(f):
            f.__returns_model__ = model_name
            return f

        return dec


model_data = defaultdict(dict)


class InstanceTrackerMeta(type):
    def __new__(meta, name, bases, dct):
        cls = super(InstanceTrackerMeta, meta).__new__(meta, name, bases, dct)
        if name == "BaseModel":
            return cls

        service = cls.__module__.split(".")[1]
        if name not in model_data[service]:
            model_data[service][name] = cls
        cls.instances = []
        return cls


class BaseModel(metaclass=InstanceTrackerMeta):
    def __new__(cls, *args, **kwargs):
        instance = super(BaseModel, cls).__new__(cls)
        cls.instances.append(instance)
        return instance


# Parent class for every Model that can be instantiated by CloudFormation
# On subclasses, implement the two methods as @staticmethod to ensure correct behaviour of the CF parser
class CloudFormationModel(BaseModel):
    @staticmethod
    @abstractmethod
    def cloudformation_name_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-name.html
        # This must be implemented as a staticmethod with no parameters
        # Return None for resources that do not have a name property
        pass

    @staticmethod
    @abstractmethod
    def cloudformation_type():
        # This must be implemented as a staticmethod with no parameters
        # See for example https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html
        return "AWS::SERVICE::RESOURCE"

    @classmethod
    @abstractmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # This must be implemented as a classmethod with parameters:
        # cls, resource_name, cloudformation_json, region_name
        # Extract the resource parameters from the cloudformation json
        # and return an instance of the resource class
        pass

    @classmethod
    @abstractmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        # This must be implemented as a classmethod with parameters:
        # cls, original_resource, new_resource_name, cloudformation_json, region_name
        # Extract the resource parameters from the cloudformation json,
        # delete the old resource and return the new one. Optionally inspect
        # the change in parameters and no-op when nothing has changed.
        pass

    @classmethod
    @abstractmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # This must be implemented as a classmethod with parameters:
        # cls, resource_name, cloudformation_json, region_name
        # Extract the resource parameters from the cloudformation json
        # and delete the resource. Do not include a return statement.
        pass


class BaseBackend:
    def _reset_model_refs(self):
        # Remove all references to the models stored
        for service, models in model_data.items():
            for model_name, model in models.items():
                model.instances = []

    def reset(self):
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__()

    @property
    def _url_module(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(
            backend_urls_module_name, fromlist=["url_bases", "url_paths"]
        )
        return backend_urls_module

    @property
    def urls(self):
        """
        A dictionary of the urls to be mocked with this service and the handlers
        that should be called in their place
        """
        url_bases = self._url_module.url_bases
        unformatted_paths = self._url_module.url_paths

        urls = {}
        for url_base in url_bases:
            for url_path, handler in unformatted_paths.items():
                url = url_path.format(url_base)
                urls[url] = handler

        return urls

    @property
    def url_paths(self):
        """
        A dictionary of the paths of the urls to be mocked with this service and
        the handlers that should be called in their place
        """
        unformatted_paths = self._url_module.url_paths

        paths = {}
        for unformatted_path, handler in unformatted_paths.items():
            path = unformatted_path.format("")
            paths[path] = handler

        return paths

    @property
    def url_bases(self):
        """
        A list containing the url_bases extracted from urls.py
        """
        return self._url_module.url_bases

    @property
    def flask_paths(self):
        """
        The url paths that will be used for the flask server
        """
        paths = {}
        for url_path, handler in self.url_paths.items():
            url_path = convert_regex_to_flask_path(url_path)
            paths[url_path] = handler

        return paths

    @staticmethod
    def default_vpc_endpoint_service(
        service_region, zones,
    ):  # pylint: disable=unused-argument
        """Invoke the factory method for any VPC endpoint(s) services."""
        return None

    @staticmethod
    def vpce_random_number():
        """Return random number for a VPC endpoint service ID."""
        return "".join([random.choice(string.hexdigits.lower()) for i in range(17)])

    @staticmethod
    def default_vpc_endpoint_service_factory(
        service_region,
        zones,
        service="",
        service_type="Interface",
        private_dns_names=True,
        special_service_name="",
        policy_supported=True,
        base_endpoint_dns_names=None,
    ):  # pylint: disable=too-many-arguments
        """List of dicts representing default VPC endpoints for this service."""
        if special_service_name:
            service_name = f"com.amazonaws.{service_region}.{special_service_name}"
        else:
            service_name = f"com.amazonaws.{service_region}.{service}"

        if not base_endpoint_dns_names:
            base_endpoint_dns_names = [f"{service}.{service_region}.vpce.amazonaws.com"]

        endpoint_service = {
            "AcceptanceRequired": False,
            "AvailabilityZones": zones,
            "BaseEndpointDnsNames": base_endpoint_dns_names,
            "ManagesVpcEndpoints": False,
            "Owner": "amazon",
            "ServiceId": f"vpce-svc-{BaseBackend.vpce_random_number()}",
            "ServiceName": service_name,
            "ServiceType": [{"ServiceType": service_type}],
            "Tags": [],
            "VpcEndpointPolicySupported": policy_supported,
        }

        # Don't know how private DNS names are different, so for now just
        # one will be added.
        if private_dns_names:
            endpoint_service[
                "PrivateDnsName"
            ] = f"{service}.{service_region}.amazonaws.com"
            endpoint_service["PrivateDnsNameVerificationState"] = "verified"
            endpoint_service["PrivateDnsNames"] = [
                {"PrivateDnsName": f"{service}.{service_region}.amazonaws.com"}
            ]
        return [endpoint_service]

    def decorator(self, func=None):
        if settings.TEST_SERVER_MODE:
            mocked_backend = ServerModeMockAWS({"global": self})
        else:
            mocked_backend = MockAWS({"global": self})

        if func:
            return mocked_backend(func)
        else:
            return mocked_backend

    def deprecated_decorator(self, func=None):
        if func:
            return HttprettyMockAWS({"global": self})(func)
        else:
            return HttprettyMockAWS({"global": self})

    # def list_config_service_resources(self, resource_ids, resource_name, limit, next_token):
    #     """For AWS Config. This will list all of the resources of the given type and optional resource name and region"""
    #     raise NotImplementedError()


class ConfigQueryModel:
    def __init__(self, backends):
        """Inits based on the resource type's backends (1 for each region if applicable)"""
        self.backends = backends

    def list_config_service_resources(
        self,
        resource_ids,
        resource_name,
        limit,
        next_token,
        backend_region=None,
        resource_region=None,
        aggregator=None,
    ):
        """For AWS Config. This will list all of the resources of the given type and optional resource name and region.

        This supports both aggregated and non-aggregated listing. The following notes the difference:

        - Non-Aggregated Listing -
        This only lists resources within a region. The way that this is implemented in moto is based on the region
        for the resource backend.

        You must set the `backend_region` to the region that the API request arrived from. resource_region can be set to `None`.

        - Aggregated Listing -
        This lists resources from all potential regional backends. For non-global resource types, this should collect a full
        list of resources from all the backends, and then be able to filter from the resource region. This is because an
        aggregator can aggregate resources from multiple regions. In moto, aggregated regions will *assume full aggregation
        from all resources in all regions for a given resource type*.

        The `backend_region` should be set to `None` for these queries, and the `resource_region` should optionally be set to
        the `Filters` region parameter to filter out resources that reside in a specific region.

        For aggregated listings, pagination logic should be set such that the next page can properly span all the region backends.
        As such, the proper way to implement is to first obtain a full list of results from all the region backends, and then filter
        from there. It may be valuable to make this a concatenation of the region and resource name.

        :param resource_ids:  A list of resource IDs
        :param resource_name: The individual name of a resource
        :param limit: How many per page
        :param next_token: The item that will page on
        :param backend_region: The region for the backend to pull results from. Set to `None` if this is an aggregated query.
        :param resource_region: The region for where the resources reside to pull results from. Set to `None` if this is a
                                non-aggregated query.
        :param aggregator: If the query is an aggregated query, *AND* the resource has "non-standard" aggregation logic (mainly, IAM),
                                you'll need to pass aggregator used. In most cases, this should be omitted/set to `None`. See the
                                conditional logic under `if aggregator` in the moto/iam/config.py for the IAM example.

        :return: This should return a list of Dicts that have the following fields:
            [
                {
                    'type': 'AWS::The AWS Config data type',
                    'name': 'The name of the resource',
                    'id': 'The ID of the resource',
                    'region': 'The region of the resource -- if global, then you may want to have the calling logic pass in the
                               aggregator region in for the resource region -- or just us-east-1 :P'
                }
                , ...
            ]
        """
        raise NotImplementedError()

    def get_config_resource(
        self, resource_id, resource_name=None, backend_region=None, resource_region=None
    ):
        """For AWS Config. This will query the backend for the specific resource type configuration.

        This supports both aggregated, and non-aggregated fetching -- for batched fetching -- the Config batching requests
        will call this function N times to fetch the N objects needing to be fetched.

        - Non-Aggregated Fetching -
        This only fetches a resource config within a region. The way that this is implemented in moto is based on the region
        for the resource backend.

        You must set the `backend_region` to the region that the API request arrived from. `resource_region` should be set to `None`.

        - Aggregated Fetching -
        This fetches resources from all potential regional backends. For non-global resource types, this should collect a full
        list of resources from all the backends, and then be able to filter from the resource region. This is because an
        aggregator can aggregate resources from multiple regions. In moto, aggregated regions will *assume full aggregation
        from all resources in all regions for a given resource type*.

        ...
        :param resource_id:
        :param resource_name:
        :param backend_region:
        :param resource_region:
        :return:
        """
        raise NotImplementedError()


class base_decorator:
    mock_backend = MockAWS

    def __init__(self, backends):
        self.backends = backends

    def __call__(self, func=None):
        if self.mock_backend != HttprettyMockAWS and settings.TEST_SERVER_MODE:
            mocked_backend = ServerModeMockAWS(self.backends)
        else:
            mocked_backend = self.mock_backend(self.backends)

        if func:
            return mocked_backend(func)
        else:
            return mocked_backend


class deprecated_base_decorator(base_decorator):
    mock_backend = HttprettyMockAWS


class MotoAPIBackend(BaseBackend):
    def reset(self):
        import moto.backends as backends

        for name, backends_ in backends.loaded_backends():
            if name == "moto_api":
                continue
            for region_name, backend in backends_.items():
                backend.reset()
        self.__init__()


moto_api_backend = MotoAPIBackend()
