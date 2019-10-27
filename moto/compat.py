try:
    from collections import OrderedDict  # noqa
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # noqa
