import re
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
