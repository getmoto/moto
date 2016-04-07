from __future__ import unicode_literals
from six.moves.urllib.parse import urlparse


def bucket_name_from_url(url):
    pth = urlparse(url).path.lstrip("/")

    l = pth.lstrip("/").split("/")
    if len(l) == 0 or l[0] == "":
        return None
    return l[0]


def parse_key_name(path):
    return "/".join(path.rstrip("/").split("/")[2:])


def is_delete_keys(request, path, bucket_name):
    return path == u'/' + bucket_name + u'/?delete' or (
        path == u'/' + bucket_name and
        getattr(request, "query_string", "") == "delete"
    )
