import functools
import re

from httpretty import HTTPretty
from .responses import metadata_response
from .utils import convert_regex_to_flask_path


class MockAWS(object):
    nested_count = 0

    def __init__(self, backend):
        self.backend = backend

        if self.__class__.nested_count == 0:
            HTTPretty.reset()

    def __call__(self, func):
        return self.decorate_callable(func)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self):
        self.__class__.nested_count += 1
        self.backend.reset()

        if not HTTPretty.is_enabled():
            HTTPretty.enable()

        for method in HTTPretty.METHODS:
            for key, value in self.backend.urls.iteritems():
                HTTPretty.register_uri(
                    method=method,
                    uri=re.compile(key),
                    body=value,
                )

            # Mock out localhost instance metadata
            HTTPretty.register_uri(
                method=method,
                uri=re.compile('http://169.254.169.254/latest/meta-data/.*'),
                body=metadata_response
            )

    def stop(self):
        self.__class__.nested_count -= 1

        if self.__class__.nested_count < 0:
            raise RuntimeError('Called stop() before start().')

        if self.__class__.nested_count == 0:
            HTTPretty.disable()

    def decorate_callable(self, func):
        def wrapper(*args, **kwargs):
            with self:
                result = func(*args, **kwargs)
            return result
        functools.update_wrapper(wrapper, func)
        wrapper.__wrapped__ = func
        return wrapper


class Model(type):
    def __new__(self, clsname, bases, namespace):
        cls = super(Model, self).__new__(self, clsname, bases, namespace)
        cls.__models__ = {}
        for name, value in namespace.iteritems():
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


class BaseBackend(object):
    def reset(self):
        self.__dict__ = {}
        self.__init__()

    @property
    def _url_module(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(backend_urls_module_name, fromlist=['url_bases', 'url_paths'])
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
            for url_path, handler in unformatted_paths.iteritems():
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
        for unformatted_path, handler in unformatted_paths.iteritems():
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
        for url_path, handler in self.url_paths.iteritems():
            url_path = convert_regex_to_flask_path(url_path)
            paths[url_path] = handler

        return paths

    def decorator(self, func=None):
        if func:
            return MockAWS(self)(func)
        else:
            return MockAWS(self)
