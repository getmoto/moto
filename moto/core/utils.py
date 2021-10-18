from __future__ import unicode_literals
from functools import wraps

import binascii
import datetime
import inspect
import random
import re
import string
from botocore.exceptions import ClientError
from urllib.parse import urlparse


REQUEST_ID_LONG = string.digits + string.ascii_uppercase


def camelcase_to_underscores(argument):
    """Converts a camelcase param like theNewAttribute to the equivalent
    python underscore variable like the_new_attribute"""
    result = ""
    prev_char_title = True
    if not argument:
        return argument
    for index, char in enumerate(argument):
        try:
            next_char_title = argument[index + 1].istitle()
        except IndexError:
            next_char_title = True

        upper_to_lower = char.istitle() and not next_char_title
        lower_to_upper = char.istitle() and not prev_char_title

        if index and (upper_to_lower or lower_to_upper):
            # Only add underscore if char is capital, not first letter, and next
            # char is not capital
            result += "_"
        prev_char_title = char.istitle()
        if not char.isspace():  # Only add non-whitespace
            result += char.lower()
    return result


def underscores_to_camelcase(argument):
    """Converts a camelcase param like the_new_attribute to the equivalent
    camelcase version like theNewAttribute. Note that the first letter is
    NOT capitalized by this function"""
    result = ""
    previous_was_underscore = False
    for char in argument:
        if char != "_":
            if previous_was_underscore:
                result += char.upper()
            else:
                result += char
        previous_was_underscore = char == "_"
    return result


def pascal_to_camelcase(argument):
    """Converts a PascalCase param to the camelCase equivalent"""
    return argument[0].lower() + argument[1:]


def camelcase_to_pascal(argument):
    """Converts a camelCase param to the PascalCase equivalent"""
    return argument[0].upper() + argument[1:]


def method_names_from_class(clazz):
    predicate = inspect.isfunction
    return [x[0] for x in inspect.getmembers(clazz, predicate=predicate)]


def get_random_hex(length=8):
    chars = list(range(10)) + ["a", "b", "c", "d", "e", "f"]
    return "".join(str(random.choice(chars)) for x in range(length))


def get_random_message_id():
    return "{0}-{1}-{2}-{3}-{4}".format(
        get_random_hex(8),
        get_random_hex(4),
        get_random_hex(4),
        get_random_hex(4),
        get_random_hex(12),
    )


def convert_regex_to_flask_path(url_path):
    """
    Converts a regex matching url to one that can be used with flask
    """
    for token in ["$"]:
        url_path = url_path.replace(token, "")

    def caller(reg):
        match_name, match_pattern = reg.groups()
        return '<regex("{0}"):{1}>'.format(match_pattern, match_name)

    url_path = re.sub(r"\(\?P<(.*?)>(.*?)\)", caller, url_path)

    if url_path.endswith("/?"):
        # Flask does own handling of trailing slashes
        url_path = url_path.rstrip("/?")
    return url_path


class convert_httpretty_response(object):
    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.__self__.__class__.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, request, url, headers, **kwargs):
        result = self.callback(request, url, headers)
        status, headers, response = result
        if "server" not in headers:
            headers["server"] = "amazon.com"
        return status, headers, response


class convert_flask_to_httpretty_response(object):
    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.__self__.__class__.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, args=None, **kwargs):
        from flask import request, Response

        try:
            result = self.callback(request, request.url, {})
        except ClientError as exc:
            result = 400, {}, exc.response["Error"]["Message"]
        # result is a status, headers, response tuple
        if len(result) == 3:
            status, headers, content = result
        else:
            status, headers, content = 200, {}, result

        response = Response(response=content, status=status, headers=headers)
        if request.method == "HEAD" and "content-length" in headers:
            response.headers["Content-Length"] = headers["content-length"]
        return response


class convert_flask_to_responses_response(object):
    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.__self__.__class__.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, request, *args, **kwargs):
        for key, val in request.headers.items():
            if isinstance(val, bytes):
                request.headers[key] = val.decode("utf-8")

        result = self.callback(request, request.url, request.headers)
        status, headers, response = result
        return status, headers, response


def iso_8601_datetime_with_milliseconds(datetime):
    return datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Even Python does not support nanoseconds, other languages like Go do (needed for Terraform)
def iso_8601_datetime_with_nanoseconds(datetime):
    return datetime.strftime("%Y-%m-%dT%H:%M:%S.%f000Z")


def iso_8601_datetime_without_milliseconds(datetime):
    return None if datetime is None else datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_8601_datetime_without_milliseconds_s3(datetime):
    return None if datetime is None else datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")


RFC1123 = "%a, %d %b %Y %H:%M:%S GMT"


def rfc_1123_datetime(datetime):
    return datetime.strftime(RFC1123)


def str_to_rfc_1123_datetime(str):
    return datetime.datetime.strptime(str, RFC1123)


def unix_time(dt=None):
    dt = dt or datetime.datetime.utcnow()
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return (delta.days * 86400) + (delta.seconds + (delta.microseconds / 1e6))


def unix_time_millis(dt=None):
    return unix_time(dt) * 1000.0


def gen_amz_crc32(response, headerdict=None):
    if not isinstance(response, bytes):
        response = response.encode("utf-8")

    crc = binascii.crc32(response)

    if headerdict is not None and isinstance(headerdict, dict):
        headerdict.update({"x-amz-crc32": str(crc)})

    return crc


def gen_amzn_requestid_long(headerdict=None):
    req_id = "".join([random.choice(REQUEST_ID_LONG) for _ in range(0, 52)])

    if headerdict is not None and isinstance(headerdict, dict):
        headerdict.update({"x-amzn-requestid": req_id})

    return req_id


def amz_crc32(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        response = f(*args, **kwargs)

        headers = {}
        status = 200

        if isinstance(response, str):
            body = response
        else:
            if len(response) == 2:
                body, new_headers = response
                status = new_headers.get("status", 200)
            else:
                status, new_headers, body = response
            headers.update(new_headers)
            # Cast status to string
            if "status" in headers:
                headers["status"] = str(headers["status"])

        try:
            # Doesnt work on python2 for some odd unicode strings
            gen_amz_crc32(body, headers)
        except Exception:
            pass

        return status, headers, body

    return _wrapper


def amzn_request_id(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        response = f(*args, **kwargs)

        headers = {}
        status = 200

        if isinstance(response, str):
            body = response
        else:
            if len(response) == 2:
                body, new_headers = response
                status = new_headers.get("status", 200)
            else:
                status, new_headers, body = response
            headers.update(new_headers)

        request_id = gen_amzn_requestid_long(headers)

        # Update request ID in XML
        try:
            body = re.sub(r"(?<=<RequestId>).*(?=<\/RequestId>)", request_id, body)
        except Exception:  # Will just ignore if it cant work on bytes (which are str's on python2)
            pass

        return status, headers, body

    return _wrapper


def path_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    if not path:
        path = "/"
    if parsed_url.query:
        path = path + "?" + parsed_url.query
    return path


def py2_strip_unicode_keys(blob):
    """For Python 2 Only -- this will convert unicode keys in nested Dicts, Lists, and Sets to standard strings."""
    if type(blob) == unicode:  # noqa
        return str(blob)

    elif type(blob) == dict:
        for key in list(blob.keys()):
            value = blob.pop(key)
            blob[str(key)] = py2_strip_unicode_keys(value)

    elif type(blob) == list:
        for i in range(0, len(blob)):
            blob[i] = py2_strip_unicode_keys(blob[i])

    elif type(blob) == set:
        new_set = set()
        for value in blob:
            new_set.add(py2_strip_unicode_keys(value))

        blob = new_set

    return blob


def tags_from_query_string(
    querystring_dict, prefix="Tag", key_suffix="Key", value_suffix="Value"
):
    response_values = {}
    for key, value in querystring_dict.items():
        if key.startswith(prefix) and key.endswith(key_suffix):
            tag_index = key.replace(prefix + ".", "").replace("." + key_suffix, "")
            tag_key = querystring_dict.get(
                "{prefix}.{index}.{key_suffix}".format(
                    prefix=prefix, index=tag_index, key_suffix=key_suffix,
                )
            )[0]
            tag_value_key = "{prefix}.{index}.{value_suffix}".format(
                prefix=prefix, index=tag_index, value_suffix=value_suffix,
            )
            if tag_value_key in querystring_dict:
                response_values[tag_key] = querystring_dict.get(tag_value_key)[0]
            else:
                response_values[tag_key] = None
    return response_values


def tags_from_cloudformation_tags_list(tags_list):
    """Return tags in dict form from cloudformation resource tags form (list of dicts)"""
    tags = {}
    for entry in tags_list:
        key = entry["Key"]
        value = entry["Value"]
        tags[key] = value

    return tags


def remap_nested_keys(root, key_transform):
    """This remap ("recursive map") function is used to traverse and
    transform the dictionary keys of arbitrarily nested structures.
    List comprehensions do not recurse, making it tedious to apply
    transforms to all keys in a tree-like structure.

    A common issue for `moto` is changing the casing of dict keys:

    >>> remap_nested_keys({'KeyName': 'Value'}, camelcase_to_underscores)
    {'key_name': 'Value'}

    Args:
        root: The target data to traverse. Supports iterables like
            :class:`list`, :class:`tuple`, and :class:`dict`.
        key_transform (callable): This function is called on every
            dictionary key found in *root*.
    """
    if isinstance(root, (list, tuple)):
        return [remap_nested_keys(item, key_transform) for item in root]
    if isinstance(root, dict):
        return {
            key_transform(k): remap_nested_keys(v, key_transform)
            for k, v in root.items()
        }
    return root


def merge_dicts(dict1, dict2, remove_nulls=False):
    """Given two arbitrarily nested dictionaries, merge the second dict into the first.

    :param dict dict1: the dictionary to be updated.
    :param dict dict2: a dictionary of keys/values to be merged into dict1.

    :param bool remove_nulls: If true, updated values equal to None or an empty dictionary
        will be removed from dict1.
    """
    for key in dict2:
        if isinstance(dict2[key], dict):
            if key in dict1 and key in dict2:
                merge_dicts(dict1[key], dict2[key], remove_nulls)
            else:
                dict1[key] = dict2[key]
            if dict1[key] == {} and remove_nulls:
                dict1.pop(key)
        else:
            dict1[key] = dict2[key]
            if dict1[key] is None and remove_nulls:
                dict1.pop(key)


def glob_matches(pattern, string):
    """AWS API-style globbing regexes"""
    pattern, n = re.subn(r"[^\\]\*", r".*", pattern)
    pattern, m = re.subn(r"[^\\]\?", r".?", pattern)

    pattern = ".*" + pattern + ".*"

    if re.match(pattern, str(string)):
        return True
    return False
