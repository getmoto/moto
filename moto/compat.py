import sys

try:
    from collections import OrderedDict  # flake8: noqa
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # flake8: noqa

try:
    from urlparse import urlparse  # flake8: noqa
except ImportError:
    from urllib.parse import urlparse  # flake8: noqa


def load_module(module_name, path):  # flake8: noqa
    if sys.version_info >= (3, 5):
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    elif sys.version_info >= (3, 3):
        from importlib.machinery import SourceFileLoader
        mod = SourceFileLoader(module_name, path).load_module()
    else:
        import imp
        mod = imp.load_source(module_name, path)
    return mod
