import functools
import re

from moto.packages.httpretty import HTTPretty


class MockAWS(object):
    def __init__(self, backend):
        self.backend = backend

    def __call__(self, func):
        return self.decorate_callable(func)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self):
        self.backend.reset()
        HTTPretty.enable()

        for method in HTTPretty.METHODS:
            for key, value in self.backend.urls.iteritems():
                HTTPretty.register_uri(
                    method=method,
                    uri=re.compile(key),
                    body=value,
                )

    def stop(self):
        HTTPretty.disable()

    def decorate_callable(self, func):
        def wrapper(*args, **kwargs):
            with self:
                result = func(*args, **kwargs)
            return result
        functools.update_wrapper(wrapper, func)
        return wrapper


class BaseBackend(object):

    def reset(self):
        self.__dict__ = {}
        self.__init__()

    @property
    def urls(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(backend_urls_module_name, fromlist=['urls'])
        urls = backend_urls_module.urls
        return urls

    def decorator(self, func=None):
        if func:
            return MockAWS(self)(func)
        else:
            return MockAWS(self)
