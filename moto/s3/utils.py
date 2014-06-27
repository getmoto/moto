import re
import sys
import urllib2
import urlparse

bucket_name_regex = re.compile("(.+).s3.amazonaws.com")


def bucket_name_from_url(url):
    domain = urlparse.urlparse(url).netloc

    if domain.startswith('www.'):
        domain = domain[4:]

    if 'amazonaws.com' in domain:
        bucket_result = bucket_name_regex.search(domain)
        if bucket_result:
            return bucket_result.groups()[0]
    else:
        if '.' in domain:
            return domain.split(".")[0]
        else:
            # No subdomain found.
            return None


def clean_key_name(key_name):
    return urllib2.unquote(key_name)


class _VersionedKeyStore(dict):

    """ A simplified/modified version of Django's `MultiValueDict` taken from:
    https://github.com/django/django/blob/70576740b0bb5289873f5a9a9a4e1a26b2c330e5/django/utils/datastructures.py#L282
    """

    def __sgetitem__(self, key):
        return super(_VersionedKeyStore, self).__getitem__(key)

    def __getitem__(self, key):
        return self.__sgetitem__(key)[-1]

    def __setitem__(self, key, value):
        try:
            current = self.__sgetitem__(key)
            current.append(value)
        except (KeyError, IndexError):
            current = [value]

        super(_VersionedKeyStore, self).__setitem__(key, current)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            pass
        return default

    def getlist(self, key, default=None):
        try:
            return self.__sgetitem__(key)
        except (KeyError, IndexError):
            pass
        return default

    def setlist(self, key, list_):
        if isinstance(list_, tuple):
            list_ = list(list_)
        elif not isinstance(list_, list):
            list_ = [list_]

        super(_VersionedKeyStore, self).__setitem__(key, list_)

    def _iteritems(self):
        for key in self:
            yield key, self[key]

    def _itervalues(self):
        for key in self:
            yield self[key]

    def _iterlists(self):
        for key in self:
            yield key, self.getlist(key)

    items = iteritems = _iteritems
    lists = iterlists = _iterlists
    values = itervalues = _itervalues

    if sys.version_info[0] < 3:
        def items(self):
            return list(self.iteritems())

        def values(self):
            return list(self.itervalues())

        def lists(self):
            return list(self.iterlists())
