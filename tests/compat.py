try:
    from unittest.mock import patch
except ImportError:
    # for python 2.7
    from mock import patch
