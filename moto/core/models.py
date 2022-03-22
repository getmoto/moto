import botocore
import boto3
import functools
import inspect
import itertools
import os
import random
import re
import string
from abc import abstractmethod
from io import BytesIO
from collections import defaultdict

from botocore.config import Config
from botocore.handlers import BUILTIN_HANDLERS
from botocore.awsrequest import AWSResponse
from types import FunctionType

from moto import settings
from moto.core.exceptions import HTTPException
import responses
import unittest
from unittest.mock import patch
from .custom_responses_mock import (
    get_response_mock,
    CallbackResponse,
    not_implemented_callback,
    reset_responses_mock,
)
from .utils import convert_regex_to_flask_path, convert_flask_to_responses_response


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
        if "us-east-1" in self.backends:
            # We only need to know the URL for a single region
            # They will be the same everywhere
            self.backends_for_urls["us-east-1"] = self.backends["us-east-1"]
        else:
            # If us-east-1 is not available, it's probably a global service
            # Global services will only have a single region anyway
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

        self.enable_patching(reset)

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
        direct_methods = get_direct_methods_of(klass)
        defined_classes = set(
            x for x, y in klass.__dict__.items() if inspect.isclass(y)
        )

        # Get a list of all userdefined superclasses
        superclasses = [
            c for c in klass.__mro__ if c not in [unittest.TestCase, object]
        ]
        # Get a list of all userdefined methods
        supermethods = list(
            itertools.chain(*[get_direct_methods_of(c) for c in superclasses])
        )
        # Check whether the user has overridden the setUp-method
        has_setup_method = (
            ("setUp" in supermethods and unittest.TestCase in klass.__mro__)
            or "setup" in supermethods
            or "setup_method" in supermethods
        )

        for attr in itertools.chain(direct_methods, defined_classes):
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
                # Special case for UnitTests-class
                is_test_method = attr.startswith(unittest.TestLoader.testMethodPrefix)
                should_reset = False
                if attr in ["setUp", "setup_method"]:
                    should_reset = True
                elif not has_setup_method and is_test_method:
                    should_reset = True
                else:
                    # Method is unrelated to the test setup
                    # Method is a test, but was already reset while executing the setUp-method
                    pass
                setattr(klass, attr, self(attr_value, reset=should_reset))
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


def get_direct_methods_of(klass):
    return set(
        x
        for x, y in klass.__dict__.items()
        if isinstance(y, (FunctionType, classmethod, staticmethod))
    )


RESPONSES_METHODS = [
    responses.GET,
    responses.DELETE,
    responses.HEAD,
    responses.OPTIONS,
    responses.PATCH,
    responses.POST,
    responses.PUT,
]


botocore_mock = responses.RequestsMock(
    assert_all_requests_are_fired=False,
    target="botocore.vendored.requests.adapters.HTTPAdapter.send",
)

responses_mock = get_response_mock()


BOTOCORE_HTTP_METHODS = ["GET", "DELETE", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]


class MockRawResponse(BytesIO):
    def __init__(self, response_input):
        if isinstance(response_input, str):
            response_input = response_input.encode("utf-8")
        super().__init__(response_input)

    def stream(self, **kwargs):  # pylint: disable=unused-argument
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
            try:
                status, headers, body = response_callback(
                    request, request.url, request.headers
                )
            except HTTPException as e:
                status = e.code
                headers = e.get_headers()
                body = e.get_body()
            body = MockRawResponse(body)
            response = AWSResponse(request.url, status, headers, body)

        return response


botocore_stubber = BotocoreStubber()
BUILTIN_HANDLERS.append(("before-send", botocore_stubber))


def patch_client(client):
    """
    Explicitly patch a boto3-client
    """
    """
    Adding the botocore_stubber to the BUILTIN_HANDLERS, as above, will mock everything as long as the import ordering is correct
     - user:   start mock_service decorator
     - system: imports core.model
     - system: adds the stubber to the BUILTIN_HANDLERS
     - user:   create a boto3 client - which will use the BUILTIN_HANDLERS

    But, if for whatever reason the imports are wrong and the client is created first, it doesn't know about our stub yet
    This method can be used to tell a client that it needs to be mocked, and append the botocore_stubber after creation
    :param client:
    :return:
    """
    if isinstance(client, botocore.client.BaseClient):
        client.meta.events.register("before-send", botocore_stubber)
    else:
        raise Exception(f"Argument {client} should be of type boto3.client")


def patch_resource(resource):
    """
    Explicitly patch a boto3-resource
    """
    if hasattr(resource, "meta") and isinstance(
        resource.meta, boto3.resources.factory.ResourceMeta
    ):
        patch_client(resource.meta.client)
    else:
        raise Exception(f"Argument {resource} should be of type boto3.resource")


class BotocoreEventMockAWS(BaseMockAWS):
    def reset(self):
        botocore_stubber.reset()
        reset_responses_mock(responses_mock)

    def enable_patching(self, reset=True):  # pylint: disable=unused-argument
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
                        )
                    )
            responses_mock.add(
                CallbackResponse(
                    method=method,
                    url=re.compile(r"https?://.+\.amazonaws.com/.*"),
                    callback=not_implemented_callback,
                )
            )
            botocore_mock.add(
                CallbackResponse(
                    method=method,
                    url=re.compile(r"https?://.+\.amazonaws.com/.*"),
                    callback=not_implemented_callback,
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
    def __init__(self, *args, **kwargs):
        self.test_server_mode_endpoint = settings.test_server_mode_endpoint()
        super().__init__(*args, **kwargs)

    def reset(self):
        call_reset_api = os.environ.get("MOTO_CALL_RESET_API")
        if not call_reset_api or call_reset_api.lower() != "false":
            import requests

            requests.post(f"{self.test_server_mode_endpoint}/moto-api/reset")

    def enable_patching(self, reset=True):
        if self.__class__.nested_count == 1 and reset:
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
                kwargs["endpoint_url"] = self.test_server_mode_endpoint
            return real_boto3_client(*args, **kwargs)

        def fake_boto3_resource(*args, **kwargs):
            if "endpoint_url" not in kwargs:
                kwargs["endpoint_url"] = self.test_server_mode_endpoint
            return real_boto3_resource(*args, **kwargs)

        self._client_patcher = patch("boto3.client", fake_boto3_client)
        self._resource_patcher = patch("boto3.resource", fake_boto3_resource)
        self._client_patcher.start()
        self._resource_patcher.start()

    def _get_region(self, *args, **kwargs):
        if "region_name" in kwargs:
            return kwargs["region_name"]
        if type(args) == tuple and len(args) == 2:
            _, region = args
            return region
        return None

    def disable_patching(self):
        if self._client_patcher:
            self._client_patcher.stop()
            self._resource_patcher.stop()


class Model(type):
    def __new__(self, clsname, bases, namespace):
        cls = super().__new__(self, clsname, bases, namespace)
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
    def __new__(cls, *args, **kwargs):  # pylint: disable=unused-argument
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
    def has_cfn_attr(cls, attr):
        # Used for validation
        # If a template creates an Output for an attribute that does not exist, an error should be thrown
        return True

    @classmethod
    @abstractmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
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

    @abstractmethod
    def is_created(self):
        # Verify whether the resource was created successfully
        # Assume True after initialization
        # Custom resources may need time after init before they are created successfully
        return True


class BaseBackend:
    def _reset_model_refs(self):
        # Remove all references to the models stored
        for models in model_data.values():
            for model in models.values():
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
        url_bases = self.url_bases
        unformatted_paths = self._url_module.url_paths

        urls = {}
        for url_base in url_bases:
            # The default URL_base will look like: http://service.[..].amazonaws.com/...
            # This extension ensures support for the China regions
            cn_url_base = re.sub(r"amazonaws\\?.com$", "amazonaws.com.cn", url_base)
            for url_path, handler in unformatted_paths.items():
                url = url_path.format(url_base)
                urls[url] = handler
                cn_url = url_path.format(cn_url_base)
                urls[cn_url] = handler

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
        service_region, zones
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
        if settings.TEST_SERVER_MODE:
            mocked_backend = ServerModeMockAWS(self.backends)
        else:
            mocked_backend = self.mock_backend(self.backends)

        if func:
            return mocked_backend(func)
        else:
            return mocked_backend


class MotoAPIBackend(BaseBackend):
    def reset(self):
        import moto.backends as backends

        for name, backends_ in backends.loaded_backends():
            if name == "moto_api":
                continue
            for backend in backends_.values():
                backend.reset()
        self.__init__()


class CloudWatchMetricProvider(object):
    @staticmethod
    @abstractmethod
    def get_cloudwatch_metrics():
        pass


moto_api_backend = MotoAPIBackend()
