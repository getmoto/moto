# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from collections import defaultdict
import functools
import inspect
import re
import six

from moto import settings
from moto.packages.responses import responses
from moto.packages.httpretty import HTTPretty
from .utils import (
    convert_httpretty_response,
    convert_regex_to_flask_path,
    convert_flask_to_responses_response,
)


class BaseMockAWS(object):
    nested_count = 0

    def __init__(self, backends):
        self.backends = backends

        self.backends_for_urls = {}
        from moto.backends import BACKENDS
        default_backends = {
            "instance_metadata": BACKENDS['instance_metadata']['global'],
            "moto_api": BACKENDS['moto_api']['global'],
        }
        self.backends_for_urls.update(self.backends)
        self.backends_for_urls.update(default_backends)

        if self.__class__.nested_count == 0:
            self.reset()

    def __call__(self, func, reset=True):
        if inspect.isclass(func):
            return self.decorate_class(func)
        return self.decorate_callable(func, reset)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self, reset=True):
        self.__class__.nested_count += 1
        if reset:
            for backend in self.backends.values():
                backend.reset()

        self.enable_patching()

    def stop(self):
        self.__class__.nested_count -= 1

        if self.__class__.nested_count < 0:
            raise RuntimeError('Called stop() before start().')

        if self.__class__.nested_count == 0:
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

            # Check if this is a classmethod. If so, skip patching
            if inspect.ismethod(attr_value) and attr_value.__self__ is klass:
                continue

            try:
                setattr(klass, attr, self(attr_value, reset=False))
            except TypeError:
                # Sometimes we can't set this for built-in types
                continue
        return klass


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


RESPONSES_METHODS = [responses.GET, responses.DELETE, responses.HEAD,
                     responses.OPTIONS, responses.PATCH, responses.POST, responses.PUT]


class ResponsesMockAWS(BaseMockAWS):

    def reset(self):
        responses.reset()

    def enable_patching(self):
        responses.start()
        for method in RESPONSES_METHODS:
            for backend in self.backends_for_urls.values():
                for key, value in backend.urls.items():
                    responses.add_callback(
                        method=method,
                        url=re.compile(key),
                        callback=convert_flask_to_responses_response(value),
                    )

        for pattern in responses.mock._urls:
            pattern['stream'] = True

    def disable_patching(self):
        try:
            responses.stop()
        except AttributeError:
            pass
        responses.reset()


MockAWS = ResponsesMockAWS


class ServerModeMockAWS(BaseMockAWS):

    def reset(self):
        import requests
        requests.post("http://localhost:5000/moto-api/reset")

    def enable_patching(self):
        if self.__class__.nested_count == 1:
            # Just started
            self.reset()

        from boto3 import client as real_boto3_client, resource as real_boto3_resource
        import mock

        def fake_boto3_client(*args, **kwargs):
            if 'endpoint_url' not in kwargs:
                kwargs['endpoint_url'] = "http://localhost:5000"
            return real_boto3_client(*args, **kwargs)

        def fake_boto3_resource(*args, **kwargs):
            if 'endpoint_url' not in kwargs:
                kwargs['endpoint_url'] = "http://localhost:5000"
            return real_boto3_resource(*args, **kwargs)

        def fake_httplib_send_output(self, message_body=None, *args, **kwargs):
            def _convert_to_bytes(mixed_buffer):
                bytes_buffer = []
                for chunk in mixed_buffer:
                    if isinstance(chunk, six.text_type):
                        bytes_buffer.append(chunk.encode('utf-8'))
                    else:
                        bytes_buffer.append(chunk)
                msg = b"\r\n".join(bytes_buffer)
                return msg

            self._buffer.extend((b"", b""))
            msg = _convert_to_bytes(self._buffer)
            del self._buffer[:]
            if isinstance(message_body, bytes):
                msg += message_body
                message_body = None
            self.send(msg)
            # if self._expect_header_set:
            #     read, write, exc = select.select([self.sock], [], [self.sock], 1)
            #     if read:
            #         self._handle_expect_response(message_body)
            #         return
            if message_body is not None:
                self.send(message_body)

        self._client_patcher = mock.patch('boto3.client', fake_boto3_client)
        self._resource_patcher = mock.patch('boto3.resource', fake_boto3_resource)
        if six.PY2:
            self._httplib_patcher = mock.patch('httplib.HTTPConnection._send_output', fake_httplib_send_output)

        self._client_patcher.start()
        self._resource_patcher.start()
        if six.PY2:
            self._httplib_patcher.start()

    def disable_patching(self):
        if self._client_patcher:
            self._client_patcher.stop()
            self._resource_patcher.stop()
            if six.PY2:
                self._httplib_patcher.stop()


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
        """ decorator to mark a class method as returning model values """
        def dec(f):
            f.__returns_model__ = model_name
            return f
        return dec


model_data = defaultdict(dict)


class InstanceTrackerMeta(type):
    def __new__(meta, name, bases, dct):
        cls = super(InstanceTrackerMeta, meta).__new__(meta, name, bases, dct)
        if name == 'BaseModel':
            return cls

        service = cls.__module__.split(".")[1]
        if name not in model_data[service]:
            model_data[service][name] = cls
        cls.instances = []
        return cls


@six.add_metaclass(InstanceTrackerMeta)
class BaseModel(object):
    def __new__(cls, *args, **kwargs):
        instance = super(BaseModel, cls).__new__(cls)
        cls.instances.append(instance)
        return instance


class BaseBackend(object):

    def reset(self):
        for service, models in model_data.items():
            for model_name, model in models.items():
                model.instances = []
        self.__dict__ = {}
        self.__init__()

    @property
    def _url_module(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(backend_urls_module_name, fromlist=[
                                         'url_bases', 'url_paths'])
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

    def decorator(self, func=None):
        if settings.TEST_SERVER_MODE:
            mocked_backend = ServerModeMockAWS({'global': self})
        else:
            mocked_backend = MockAWS({'global': self})

        if func:
            return mocked_backend(func)
        else:
            return mocked_backend

    def deprecated_decorator(self, func=None):
        if func:
            return HttprettyMockAWS({'global': self})(func)
        else:
            return HttprettyMockAWS({'global': self})


class base_decorator(object):
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
        from moto.backends import BACKENDS
        for name, backends in BACKENDS.items():
            if name == "moto_api":
                continue
            for region_name, backend in backends.items():
                backend.reset()
        self.__init__()


moto_api_backend = MotoAPIBackend()
