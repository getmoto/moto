import re
import urlparse

bucket_name_regex = re.compile("(.+).s3.amazonaws.com")


def bucket_name_from_hostname(hostname):
    if 'amazonaws.com' in hostname:
        bucket_result = bucket_name_regex.search(hostname)
        if bucket_result:
            return bucket_result.groups()[0]
    else:
        # In server mode. Use left-most part of subdomain for bucket name
        split_url = urlparse.urlparse(hostname)

        # If 'www' prefixed, strip it.
        clean_hostname = split_url.netloc.lstrip("www.")

        if '.' in clean_hostname:
            return clean_hostname.split(".")[0]
        else:
            # No subdomain found.
            return None
