import random
import string
import json
import yaml


def create_id():
    size = 10
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def deserialize_body(body, content_type=None):
    if content_type and content_type == "application/json":
        api_doc = json.loads(body)
    elif content_type and content_type == "application/yaml":
        api_doc = yaml.safe_load(body)
    else:
        try:
            api_doc = json.loads(body)
        except ValueError:  # Python 2.7 compat
            api_doc = yaml.safe_load(body)
        except json.JSONDecodeError:
            api_doc = yaml.safe_load(body)

    if "openapi" in api_doc or "swagger" in api_doc:
        return api_doc

    return None


def to_path(prop):
    return "/" + prop
