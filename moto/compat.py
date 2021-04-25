try:
    from collections import OrderedDict  # noqa
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # noqa

try:
    import collections.abc as collections_abc  # noqa
except ImportError:
    import collections as collections_abc  # noqa

try:
    from unittest.mock import patch  # noqa
except ImportError:
    # for python 2.7
    from mock import patch  # noqa
