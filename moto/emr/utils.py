from __future__ import unicode_literals
import random
import string
import six


def random_job_id(size=13):
    chars = list(range(10)) + list(string.ascii_uppercase)
    job_tag = ''.join(six.text_type(random.choice(chars)) for x in range(size))
    return 'j-{0}'.format(job_tag)


def random_instance_group_id(size=13):
    chars = list(range(10)) + list(string.ascii_uppercase)
    job_tag = ''.join(six.text_type(random.choice(chars)) for x in range(size))
    return 'i-{0}'.format(job_tag)


def tags_from_query_string(querystring_dict):
    prefix = 'Tags'
    suffix = 'Key'
    response_values = {}
    for key, value in querystring_dict.items():
        if key.startswith(prefix) and key.endswith(suffix):
            tag_index = key.replace(prefix + ".", "").replace("." + suffix, "")
            tag_key = querystring_dict.get("Tags.{0}.Key".format(tag_index))[0]
            tag_value_key = "Tags.{0}.Value".format(tag_index)
            if tag_value_key in querystring_dict:
                response_values[tag_key] = querystring_dict.get(tag_value_key)[0]
            else:
                response_values[tag_key] = None
    return response_values
