from __future__ import unicode_literals
import boto
import six
from nose.plugins.skip import SkipTest


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


class requires_boto_gte(object):
    """Decorator for requiring boto version greater than or equal to 'version'"""
    def __init__(self, version):
        self.version = version

    def __call__(self, test):
        boto_version = version_tuple(boto.__version__)
        required = version_tuple(self.version)
        if boto_version >= required:
            return test
        raise SkipTest


class py3_requires_boto_gte(object):
    """Decorator for requiring boto version greater than or equal to 'version'
    when running on Python 3. (Not all of boto is Python 3 compatible.)"""
    def __init__(self, version):
        self.version = version

    def __call__(self, test):
        if not six.PY3:
            return test
        boto_version = version_tuple(boto.__version__)
        required = version_tuple(self.version)
        if boto_version >= required:
            return test
        raise SkipTest
