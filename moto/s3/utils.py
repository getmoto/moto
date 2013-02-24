import re

bucket_name_regex = re.compile("(.+).s3.amazonaws.com")


def bucket_name_from_hostname(hostname):
    bucket_result = bucket_name_regex.search(hostname)
    return bucket_result.groups()[0]
