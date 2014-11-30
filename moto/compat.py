try:
    from collections import OrderedDict  # flake8: noqa
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # flake8: noqa
