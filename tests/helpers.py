from __future__ import unicode_literals
import boto
from nose.plugins.skip import SkipTest
import six


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


# Note: See https://github.com/spulec/moto/issues/201 for why this is a
# separate method.
def skip_test():
    raise SkipTest


class requires_boto_gte(object):
    """Decorator for requiring boto version greater than or equal to 'version'"""

    def __init__(self, version):
        self.version = version

    def __call__(self, test):
        boto_version = version_tuple(boto.__version__)
        required = version_tuple(self.version)
        if boto_version >= required:
            return test
        return skip_test


class disable_on_py3(object):

    def __call__(self, test):
        if not six.PY3:
            return test
        return skip_test
