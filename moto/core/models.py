import functools
import inspect
import itertools
import os
import re
import unittest
from threading import Lock
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ContextManager,
    Dict,
    Optional,
    Set,
    TypeVar,
)
from unittest.mock import patch

import boto3
import botocore
import responses
from botocore.config import Config
from botocore.handlers import BUILTIN_HANDLERS

import moto.backend_index as backend_index
from moto import settings

from .botocore_stubber import BotocoreStubber
from .custom_responses_mock import (
    CallbackResponse,
    get_response_mock,
    not_implemented_callback,
    reset_responses_mock,
)
from .model_instances import reset_model_data

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")


DEFAULT_ACCOUNT_ID = "123456789012"
T = TypeVar("T")


class MockAWS(ContextManager["MockAWS"]):
    nested_count = 0
    mocks_active = False
    mock_init_lock = Lock()

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.FAKE_KEYS = {
            "AWS_ACCESS_KEY_ID": "FOOBARKEY",
            "AWS_SECRET_ACCESS_KEY": "FOOBARSECRET",
        }
        self.ORIG_KEYS: Dict[str, Optional[str]] = {}
        self.default_session_mock = patch("boto3.DEFAULT_SESSION", None)
        current_user_config = default_user_config.copy()
        current_user_config.update(config or {})
        self.user_config_mock = patch.dict(default_user_config, current_user_config)

    def __call__(
        self, func: "Callable[P, T]", reset: bool = True, remove_data: bool = True
    ) -> "Callable[P, T]":
        if inspect.isclass(func):
            return self.decorate_class(func)
        return self.decorate_callable(func, reset, remove_data)

    def __enter__(self) -> "MockAWS":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()

    def start(self, reset: bool = True) -> None:
        with MockAWS.mock_init_lock:
            if not self.__class__.mocks_active:
                self.mock_env_variables()
                self.__class__.mocks_active = True
                self.default_session_mock.start()

            self.__class__.nested_count += 1

            if self.__class__.nested_count == 1:
                self.enable_patching(reset=reset)

    def stop(self, remove_data: bool = True) -> None:
        with MockAWS.mock_init_lock:
            self.__class__.nested_count -= 1

            if self.__class__.nested_count < 0:
                raise RuntimeError("Called stop() before start().")

            if self.__class__.nested_count == 0:
                if self.__class__.mocks_active:
                    self.default_session_mock.stop()
                    self.unmock_env_variables()
                    self.__class__.mocks_active = False
                self.disable_patching(remove_data)

    def decorate_callable(
        self, func: "Callable[P, T]", reset: bool, remove_data: bool
    ) -> "Callable[P, T]":
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self.start(reset=reset)
            try:
                result = func(*args, **kwargs)
            finally:
                self.stop(remove_data=remove_data)
            return result

        functools.update_wrapper(wrapper, func)
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper

    def decorate_class(self, klass: "Callable[P, T]") -> "Callable[P, T]":
        assert inspect.isclass(klass)  # Keep mypy happy
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
                should_remove_data = False
                if attr in ["setUp", "setup_method"]:
                    should_reset = True
                elif not has_setup_method and is_test_method:
                    should_reset = True
                    should_remove_data = True
                else:
                    # Method is unrelated to the test setup
                    # Method is a test, but was already reset while executing the setUp-method
                    pass
                kwargs = {"reset": should_reset, "remove_data": should_remove_data}
                setattr(klass, attr, self(attr_value, **kwargs))
            except TypeError:
                # Sometimes we can't set this for built-in types
                continue
        return klass

    def mock_env_variables(self) -> None:
        # "Mock" the AWS credentials as they can't be mocked in Botocore currently
        # self.env_variables_mocks = mock.patch.dict(os.environ, FAKE_KEYS)
        # self.env_variables_mocks.start()
        for k, v in self.FAKE_KEYS.items():
            self.ORIG_KEYS[k] = os.environ.get(k, None)
            os.environ[k] = v

    def unmock_env_variables(self) -> None:
        # This doesn't work in Python2 - for some reason, unmocking clears the entire os.environ dict
        # Obviously bad user experience, and also breaks pytest - as it uses PYTEST_CURRENT_TEST as an env var
        # self.env_variables_mocks.stop()
        for k, v in self.ORIG_KEYS.items():
            if v:
                os.environ[k] = v
            else:
                del os.environ[k]

    def reset(self) -> None:
        botocore_stubber.reset()
        reset_responses_mock(responses_mock)

    def enable_patching(
        self, reset: bool = True  # pylint: disable=unused-argument
    ) -> None:
        botocore_stubber.enabled = True
        if reset:
            self.reset()
        responses_mock.start()
        self.user_config_mock.start()

        for method in RESPONSES_METHODS:
            for _, pattern in backend_index.backend_url_patterns:
                responses_mock.add(
                    CallbackResponse(
                        method=method,
                        url=pattern,
                        callback=botocore_stubber.process_request,
                    )
                )
            responses_mock.add(
                CallbackResponse(
                    method=method,
                    url=re.compile(r"https?://.+\.amazonaws.com/.*"),
                    callback=not_implemented_callback,
                )
            )

    def disable_patching(self, remove_data: bool) -> None:
        botocore_stubber.enabled = False
        if remove_data:
            self.reset()
            reset_model_data()

        try:
            responses_mock.stop()
        except RuntimeError:
            pass
        self.user_config_mock.stop()


def get_direct_methods_of(klass: object) -> Set[str]:
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

responses_mock = get_response_mock()

BOTOCORE_HTTP_METHODS = ["GET", "DELETE", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]


botocore_stubber = BotocoreStubber()
BUILTIN_HANDLERS.append(("before-send", botocore_stubber))

default_user_config = {"batch": {"use_docker": True}, "lambda": {"use_docker": True}}


def patch_client(client: botocore.client.BaseClient) -> None:
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
        # Check if our event handler was already registered
        try:
            event_emitter = client._ruleset_resolver._event_emitter._emitter  # type: ignore[attr-defined]
            all_handlers = event_emitter._handlers._root["children"]
            handler_trie = list(all_handlers["before-send"].values())[1]
            handlers_list = handler_trie.first + handler_trie.middle + handler_trie.last
            if botocore_stubber in handlers_list:
                # No need to patch - this client already has the botocore_stubber registered
                return
        except:  # noqa: E722 Do not use bare except
            # Because we're accessing all kinds of private methods, the API may change and newer versions of botocore may throw an exception
            # One of our tests will fail if this happens (test_patch_can_be_called_on_a_mocked_client)
            # If this happens for a user, just continue and hope for the best
            #  - in 99% of the cases there are no duplicate event handlers, so it doesn't matter if the check fails
            pass

        client.meta.events.register("before-send", botocore_stubber)
    else:
        raise Exception(f"Argument {client} should be of type boto3.client")


def patch_resource(resource: Any) -> None:
    """
    Explicitly patch a boto3-resource
    """
    if hasattr(resource, "meta") and isinstance(
        resource.meta, boto3.resources.factory.ResourceMeta
    ):
        patch_client(resource.meta.client)
    else:
        raise Exception(f"Argument {resource} should be of type boto3.resource")


def override_responses_real_send(user_mock: Optional[responses.RequestsMock]) -> None:
    """
    Moto creates it's own Responses-object responsible for intercepting AWS requests
    If a custom Responses-object is created by the user, Moto will hijack any of the pass-thru's set

    Call this method to ensure any requests unknown to Moto are passed through the custom Responses-object.

    Set the user_mock argument to None to reset this behaviour.

    Note that this is only supported from Responses>=0.24.0
    """
    if user_mock is None:
        responses_mock._real_send = responses._real_send
    else:
        responses_mock._real_send = user_mock.unbound_on_send()


class ServerModeMockAWS(MockAWS):
    RESET_IN_PROGRESS = False

    def __init__(self, *args: Any, **kwargs: Any):
        self.test_server_mode_endpoint = settings.test_server_mode_endpoint()
        super().__init__(*args, **kwargs)

    def reset(self) -> None:
        call_reset_api = os.environ.get("MOTO_CALL_RESET_API")
        if not call_reset_api or call_reset_api.lower() != "false":
            if not ServerModeMockAWS.RESET_IN_PROGRESS:
                ServerModeMockAWS.RESET_IN_PROGRESS = True
                import requests

                requests.post(f"{self.test_server_mode_endpoint}/moto-api/reset")
                ServerModeMockAWS.RESET_IN_PROGRESS = False

    def enable_patching(self, reset: bool = True) -> None:
        if self.__class__.nested_count == 1 and reset:
            # Just started
            self.reset()

        from boto3 import client as real_boto3_client
        from boto3 import resource as real_boto3_resource

        def fake_boto3_client(*args: Any, **kwargs: Any) -> botocore.client.BaseClient:
            region = self._get_region(*args, **kwargs)
            if region:
                if "config" in kwargs:
                    user_agent = kwargs["config"].__dict__.get("user_agent_extra") or ""
                    kwargs["config"].__dict__[
                        "user_agent_extra"
                    ] = f"{user_agent} region/{region}"
                else:
                    config = Config(user_agent_extra="region/" + region)
                    kwargs["config"] = config
            if "endpoint_url" not in kwargs:
                kwargs["endpoint_url"] = self.test_server_mode_endpoint
            return real_boto3_client(*args, **kwargs)

        def fake_boto3_resource(*args: Any, **kwargs: Any) -> Any:
            if "endpoint_url" not in kwargs:
                kwargs["endpoint_url"] = self.test_server_mode_endpoint
            return real_boto3_resource(*args, **kwargs)

        self._client_patcher = patch("boto3.client", fake_boto3_client)
        self._resource_patcher = patch("boto3.resource", fake_boto3_resource)
        self._client_patcher.start()
        self._resource_patcher.start()

    def _get_region(self, *args: Any, **kwargs: Any) -> Optional[str]:
        if "region_name" in kwargs:
            return kwargs["region_name"]
        if type(args) is tuple and len(args) == 2:
            _, region = args
            return region
        return None

    def disable_patching(self, remove_data: bool) -> None:
        if self._client_patcher:
            self._client_patcher.stop()
            self._resource_patcher.stop()
        if remove_data:
            self.reset()


class ProxyModeMockAWS(MockAWS):

    RESET_IN_PROGRESS = False

    def __init__(self, *args: Any, **kwargs: Any):
        self.test_proxy_mode_endpoint = settings.test_proxy_mode_endpoint()
        super().__init__(*args, **kwargs)

    def reset(self) -> None:
        call_reset_api = os.environ.get("MOTO_CALL_RESET_API")
        if not call_reset_api or call_reset_api.lower() != "false":
            if not ProxyModeMockAWS.RESET_IN_PROGRESS:
                ProxyModeMockAWS.RESET_IN_PROGRESS = True
                import requests

                requests.post(f"{self.test_proxy_mode_endpoint}/moto-api/reset")
                ProxyModeMockAWS.RESET_IN_PROGRESS = False

    def enable_patching(self, reset: bool = True) -> None:
        if self.__class__.nested_count == 1 and reset:
            # Just started
            self.reset()

        from boto3 import client as real_boto3_client
        from boto3 import resource as real_boto3_resource

        def fake_boto3_client(*args: Any, **kwargs: Any) -> botocore.client.BaseClient:
            kwargs["verify"] = False
            proxy_endpoint = (
                f"http://localhost:{os.environ.get('MOTO_PROXY_PORT', 5005)}"
            )
            proxies = {"http": proxy_endpoint, "https": proxy_endpoint}
            if "config" in kwargs:
                kwargs["config"].__dict__["proxies"] = proxies
            else:
                config = Config(proxies=proxies)
                kwargs["config"] = config

            return real_boto3_client(*args, **kwargs)

        def fake_boto3_resource(*args: Any, **kwargs: Any) -> Any:
            kwargs["verify"] = False
            proxy_endpoint = (
                f"http://localhost:{os.environ.get('MOTO_PROXY_PORT', 5005)}"
            )
            proxies = {"http": proxy_endpoint, "https": proxy_endpoint}
            if "config" in kwargs:
                kwargs["config"].__dict__["proxies"] = proxies
            else:
                config = Config(proxies=proxies)
                kwargs["config"] = config
            return real_boto3_resource(*args, **kwargs)

        self._client_patcher = patch("boto3.client", fake_boto3_client)
        self._resource_patcher = patch("boto3.resource", fake_boto3_resource)
        self._client_patcher.start()
        self._resource_patcher.start()

    def disable_patching(self, remove_data: bool) -> None:
        if self._client_patcher:
            self._client_patcher.stop()
            self._resource_patcher.stop()
