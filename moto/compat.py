try:
    from collections import OrderedDict  # pylint: disable=unused-import
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # pylint: disable=unused-import
