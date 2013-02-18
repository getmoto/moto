import functools
import re

from httpretty import HTTPretty


class BaseBackend(object):
    base_url = None

    def reset(self):
        self = self.__class__()

    @property
    def urls(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(backend_urls_module_name, fromlist=['urls'])
        urls = backend_urls_module.urls
        return urls

    def decorator(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            self.reset()

            HTTPretty.reset()
            HTTPretty.enable()

            for method in HTTPretty.METHODS:
                for key, value in self.urls.iteritems():
                    HTTPretty.register_uri(
                        method=method,
                        uri=re.compile(self.base_url + key),
                        body=value,
                    )
            try:
                return func(*args, **kw)
            finally:
                HTTPretty.disable()
        return wrapper
