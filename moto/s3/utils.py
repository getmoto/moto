from __future__ import unicode_literals
import logging

import re
import six
from six.moves.urllib.parse import urlparse, unquote, quote
from requests.structures import CaseInsensitiveDict
import sys
from moto.settings import S3_IGNORE_SUBDOMAIN_BUCKETNAME


log = logging.getLogger(__name__)


bucket_name_regex = re.compile("(.+).s3(.*).amazonaws.com")
user_settable_fields = {
    "content-md5",
    "content-language",
    "content-type",
    "content-encoding",
    "cache-control",
    "expires",
    "content-disposition",
    "x-robots-tag",
}


def bucket_name_from_url(url):
    if S3_IGNORE_SUBDOMAIN_BUCKETNAME:
        return None
    domain = urlparse(url).netloc

    if domain.startswith("www."):
        domain = domain[4:]

    if "amazonaws.com" in domain:
        bucket_result = bucket_name_regex.search(domain)
        if bucket_result:
            return bucket_result.groups()[0]
    else:
        if "." in domain:
            return domain.split(".")[0]
        else:
            # No subdomain found.
            return None


# 'owi-common-cf', 'snippets/test.json' = bucket_and_name_from_url('s3://owi-common-cf/snippets/test.json')
def bucket_and_name_from_url(url):
    prefix = "s3://"
    if url.startswith(prefix):
        bucket_name = url[len(prefix) : url.index("/", len(prefix))]
        key = url[url.index("/", len(prefix)) + 1 :]
        return bucket_name, key
    else:
        return None, None


REGION_URL_REGEX = re.compile(
    r"^https?://(s3[-\.](?P<region1>.+)\.amazonaws\.com/(.+)|"
    r"(.+)\.s3[-\.](?P<region2>.+)\.amazonaws\.com)/?"
)


def parse_region_from_url(url):
    match = REGION_URL_REGEX.search(url)
    if match:
        region = match.group("region1") or match.group("region2")
    else:
        region = "us-east-1"
    return region


def metadata_from_headers(headers):
    metadata = CaseInsensitiveDict()
    meta_regex = re.compile(r"^x-amz-meta-([a-zA-Z0-9\-_.]+)$", flags=re.IGNORECASE)
    for header, value in headers.items():
        if isinstance(header, six.string_types):
            result = meta_regex.match(header)
            meta_key = None
            if result:
                # Check for extra metadata
                meta_key = result.group(0).lower()
            elif header.lower() in user_settable_fields:
                # Check for special metadata that doesn't start with x-amz-meta
                meta_key = header
            if meta_key:
                metadata[meta_key] = (
                    headers[header][0]
                    if type(headers[header]) == list
                    else headers[header]
                )
    return metadata


def clean_key_name(key_name):
    if six.PY2:
        return unquote(key_name.encode("utf-8")).decode("utf-8")
    return unquote(key_name)


def undo_clean_key_name(key_name):
    if six.PY2:
        return quote(key_name.encode("utf-8")).decode("utf-8")
    return quote(key_name)


class _VersionedKeyStore(dict):

    """A simplified/modified version of Django's `MultiValueDict` taken from:
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

    def item_size(self):
        size = 0
        for val in self.values():
            size += sys.getsizeof(val)
        return size

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
