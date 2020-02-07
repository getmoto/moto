from __future__ import unicode_literals
import six
import random
import string
import json
import yaml


def create_id():
    size = 10
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(six.text_type(random.choice(chars)) for x in range(size))


def deserialize_body(body, content_type=None):
    if content_type and content_type == "application/json":
        return json.loads(body)
    elif content_type and content_type == "application/yaml":
        return yaml.loads(body)
    else:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return yaml.load(body)
