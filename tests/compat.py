try:
    from unittest.mock import mock, patch
except ImportError:
    # for python 2.7
    from mock import mock, patch
