from functools import wraps

import binascii
import datetime
import inspect
import random
import re
import string
from botocore.exceptions import ClientError
from boto3 import Session
from moto.settings import allow_unknown_region
from threading import RLock
from urllib.parse import urlparse


REQUEST_ID_LONG = string.digits + string.ascii_uppercase
HEX_CHARS = list(range(10)) + ["a", "b", "c", "d", "e", "f"]


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
    return "".join(str(random.choice(HEX_CHARS)) for _ in range(length))


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


class convert_to_flask_response(object):
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
            result = self.callback(request, request.url, dict(request.headers))
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


def str_to_rfc_1123_datetime(value):
    return datetime.datetime.strptime(value, RFC1123)


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


def tags_from_query_string(
    querystring_dict, prefix="Tag", key_suffix="Key", value_suffix="Value"
):
    response_values = {}
    for key in querystring_dict.keys():
        if key.startswith(prefix) and key.endswith(key_suffix):
            tag_index = key.replace(prefix + ".", "").replace("." + key_suffix, "")
            tag_key = querystring_dict.get(
                "{prefix}.{index}.{key_suffix}".format(
                    prefix=prefix, index=tag_index, key_suffix=key_suffix
                )
            )[0]
            tag_value_key = "{prefix}.{index}.{value_suffix}".format(
                prefix=prefix, index=tag_index, value_suffix=value_suffix
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


def aws_api_matches(pattern, string):
    """
    AWS API can match a value based on a glob, or an exact match
    """
    # use a negative lookback regex to match stars that are not prefixed with a backslash
    # and replace all stars not prefixed w/ a backslash with '.*' to take this from "glob" to PCRE syntax
    pattern, _ = re.subn(r"(?<!\\)\*", r".*", pattern)

    # ? in the AWS glob form becomes .? in regex
    # also, don't substitute it if it is prefixed w/ a backslash
    pattern, _ = re.subn(r"(?<!\\)\?", r".?", pattern)

    # aws api seems to anchor
    anchored_pattern = f"^{pattern}$"

    if re.match(anchored_pattern, str(string)):
        return True
    else:
        return False


def extract_region_from_aws_authorization(string):
    auth = string or ""
    region = re.sub(r".*Credential=[^/]+/[^/]+/([^/]+)/.*", r"\1", auth)
    if region == auth:
        return None
    return region


backend_lock = RLock()


class BackendDict(dict):
    """
    Data Structure to store everything related to a specific service.
    Format:
      [account_id: str]: AccountSpecificBackend
      [account_id: str][region: str] = BaseBackend

    Full multi-account support is not yet available. We will always return account_id 123456789012, regardless of the input.

    To not break existing usage patterns, the following data access pattern is also supported:
      [region: str] = BaseBackend

    This will automatically resolve to:
      [default_account_id][region: str] = BaseBackend
    """

    def __init__(
        self, backend, service_name, use_boto3_regions=True, additional_regions=None
    ):
        self.backend = backend
        self.service_name = service_name
        self._use_boto3_regions = use_boto3_regions
        self._additional_regions = additional_regions

    def __contains__(self, account_id_or_region):
        """
        Possible data access patterns:
          backend_dict[account_id][region_name]
          backend_dict[region_name]
          backend_dict[unknown_region]

        The latter two will be phased out in the future, and we can remove this method.
        """
        if re.match(r"[0-9]+", account_id_or_region):
            self._create_account_specific_backend("123456789012")
            return True
        else:
            region = account_id_or_region
            self._create_account_specific_backend("123456789012")
            return region in self["123456789012"]

    def get(self, account_id_or_region, if_none=None):
        if self.__contains__(account_id_or_region):
            return self.__getitem__(account_id_or_region)
        return if_none

    def __getitem__(self, account_id_or_region):
        """
        Possible data access patterns:
          backend_dict[account_id][region_name]
          backend_dict[region_name]
          backend_dict[unknown_region]

        The latter two will be phased out in the future.
        """
        if re.match(r"[0-9]+", account_id_or_region):
            self._create_account_specific_backend("123456789012")
            return super().__getitem__("123456789012")
        else:
            region_name = account_id_or_region
            return self["123456789012"][region_name]

    def _create_account_specific_backend(self, account_id):
        with backend_lock:
            if account_id not in self.keys():
                self[account_id] = AccountSpecificBackend(
                    service_name=self.service_name,
                    account_id=account_id,
                    backend=self.backend,
                    use_boto3_regions=self._use_boto3_regions,
                    additional_regions=self._additional_regions,
                )


class AccountSpecificBackend(dict):
    """
    Dictionary storing the data for a service in a specific account.
    Data access pattern:
      account_specific_backend[region: str] = backend: BaseBackend
    """

    def __init__(
        self, service_name, account_id, backend, use_boto3_regions, additional_regions
    ):
        self.service_name = service_name
        self.account_id = account_id
        self.backend = backend
        self.regions = []
        if use_boto3_regions:
            sess = Session()
            self.regions.extend(sess.get_available_regions(service_name))
            self.regions.extend(
                sess.get_available_regions(service_name, partition_name="aws-us-gov")
            )
            self.regions.extend(
                sess.get_available_regions(service_name, partition_name="aws-cn")
            )
        self.regions.extend(additional_regions or [])

    def reset(self):
        for region_specific_backend in self.values():
            region_specific_backend.reset()

    def __contains__(self, region):
        return region in self.regions or region in self.keys()

    def __getitem__(self, region_name):
        if region_name in self.keys():
            return super().__getitem__(region_name)
        # Create the backend for a specific region
        with backend_lock:
            if region_name in self.regions and region_name not in self.keys():
                super().__setitem__(
                    region_name, self.backend(region_name, account_id=self.account_id)
                )
            if region_name not in self.regions and allow_unknown_region():
                super().__setitem__(
                    region_name, self.backend(region_name, account_id=self.account_id)
                )
        return super().__getitem__(region_name)
