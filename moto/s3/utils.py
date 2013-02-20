import re

bucket_name_regex = re.compile("(.+).s3.amazonaws.com")


def bucket_name_from_hostname(hostname):
    bucket_result = bucket_name_regex.search(hostname)
    return bucket_result.groups()[0]


def headers_to_dict(headers):
    result = {}
    for header in headers.split("\r\n"):
        if ':' in header:
            key, value = header.split(":", 1)
            result[key.strip()] = value.strip()

    return result
