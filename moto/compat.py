try:
    from collections import OrderedDict  # noqa
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # noqa

try:
    import collections.abc as collections_abc  # noqa
except ImportError:
    import collections as collections_abc  # noqa
