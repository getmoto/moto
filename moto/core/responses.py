from __future__ import unicode_literals
import datetime
import json
import re

import six
from six.moves.urllib.parse import parse_qs, urlparse

from werkzeug.exceptions import HTTPException
from moto.core.utils import camelcase_to_underscores, method_names_from_class


def _decode_dict(d):
    decoded = {}
    for key, value in d.items():
        if isinstance(key, six.binary_type):
            newkey = key.decode("utf-8")
        elif isinstance(key, (list, tuple)):
            newkey = []
            for k in key:
                if isinstance(k, six.binary_type):
                    newkey.append(k.decode('utf-8'))
                else:
                    newkey.append(k)
        else:
            newkey = key

        if isinstance(value, six.binary_type):
            newvalue = value.decode("utf-8")
        elif isinstance(value, (list, tuple)):
            newvalue = []
            for v in value:
                if isinstance(v, six.binary_type):
                    newvalue.append(v.decode('utf-8'))
                else:
                    newvalue.append(v)
        else:
            newvalue = value

        decoded[newkey] = newvalue
    return decoded


class BaseResponse(object):

    default_region = 'us-east-1'
    region_regex = r'\.(.+?)\.amazonaws\.com'

    def dispatch(self, request, full_url, headers):
        querystring = {}

        if hasattr(request, 'body'):
            # Boto
            self.body = request.body
        else:
            # Flask server

            # FIXME: At least in Flask==0.10.1, request.data is an empty string
            # and the information we want is in request.form. Keeping self.body
            # definition for back-compatibility
            self.body = request.data

            querystring = {}
            for key, value in request.form.items():
                querystring[key] = [value, ]

        if not querystring:
            querystring.update(parse_qs(urlparse(full_url).query, keep_blank_values=True))
        if not querystring:
            querystring.update(parse_qs(self.body, keep_blank_values=True))
        if not querystring:
            querystring.update(headers)

        querystring = _decode_dict(querystring)

        self.uri = full_url
        self.path = urlparse(full_url).path
        self.querystring = querystring
        self.method = request.method
        region = re.search(self.region_regex, full_url)
        if region:
            self.region = region.group(1)
        else:
            self.region = self.default_region

        self.headers = dict(request.headers)
        self.response_headers = headers
        return self.call_action()

    def call_action(self):
        headers = self.response_headers
        action = self.querystring.get('Action', [""])[0]
        action = camelcase_to_underscores(action)
        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            try:
                response = method()
            except HTTPException as http_error:
                response = http_error.description, dict(status=http_error.code)
            if isinstance(response, six.string_types):
                return 200, headers, response
            else:
                body, new_headers = response
                status = new_headers.get('status', 200)
                headers.update(new_headers)
                return status, headers, body
        raise NotImplementedError("The {0} action has not been implemented".format(action))

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def _get_multi_param(self, param_prefix):
        if param_prefix.endswith("."):
            prefix = param_prefix
        else:
            prefix = param_prefix + "."
        values = []
        index = 1
        while True:
            try:
                values.append(self.querystring[prefix + str(index)][0])
            except KeyError:
                break
            else:
                index += 1
        return values


def metadata_response(request, full_url, headers):
    """
    Mock response for localhost metadata

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AESDG-chapter-instancedata.html
    """
    parsed_url = urlparse(full_url)
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    credentials = dict(
        AccessKeyId="test-key",
        SecretAccessKey="test-secret-key",
        Token="test-session-token",
        Expiration=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    path = parsed_url.path

    meta_data_prefix = "/latest/meta-data/"
    # Strip prefix if it is there
    if path.startswith(meta_data_prefix):
        path = path[len(meta_data_prefix):]

    if path == '':
        result = 'iam'
    elif path == 'iam':
        result = json.dumps({
            'security-credentials': {
                'default-role': credentials
            }
        })
    elif path == 'iam/security-credentials/':
        result = 'default-role'
    elif path == 'iam/security-credentials/default-role':
        result = json.dumps(credentials)
    else:
        raise NotImplementedError("The {0} metadata path has not been implemented".format(path))
    return 200, headers, result
