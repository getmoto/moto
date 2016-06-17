from __future__ import unicode_literals
import datetime
import json
import re

from jinja2 import Environment, DictLoader, TemplateNotFound

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


class DynamicDictLoader(DictLoader):
    """
      Note: There's a bug in jinja2 pre-2.7.3 DictLoader where caching does not work.
        Including the fixed (current) method version here to ensure performance benefit
        even for those using older jinja versions.
    """
    def get_source(self, environment, template):
        if template in self.mapping:
            source = self.mapping[template]
            return source, None, lambda: source == self.mapping.get(template)
        raise TemplateNotFound(template)

    def update(self, mapping):
        self.mapping.update(mapping)

    def contains(self, template):
        return bool(template in self.mapping)


class _TemplateEnvironmentMixin(object):

    def __init__(self):
        super(_TemplateEnvironmentMixin, self).__init__()
        self.loader = DynamicDictLoader({})
        self.environment = Environment(loader=self.loader, autoescape=self.should_autoescape)

    @property
    def should_autoescape(self):
        # Allow for subclass to overwrite
        return False

    def contains_template(self, template_id):
        return self.loader.contains(template_id)

    def response_template(self, source):
        template_id = id(source)
        if not self.contains_template(template_id):
            self.loader.update({template_id: source})
            self.environment = Environment(loader=self.loader, autoescape=self.should_autoescape, trim_blocks=True,
                                           lstrip_blocks=True)
        return self.environment.get_template(template_id)


class BaseResponse(_TemplateEnvironmentMixin):

    default_region = 'us-east-1'
    region_regex = r'\.(.+?)\.amazonaws\.com'

    @classmethod
    def dispatch(cls, *args, **kwargs):
        return cls()._dispatch(*args, **kwargs)

    def setup_class(self, request, full_url, headers):
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

        self.headers = request.headers
        self.response_headers = headers

    def _dispatch(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        return self.call_action()

    def call_action(self):
        headers = self.response_headers
        action = self.querystring.get('Action', [""])[0]
        if not action:  # Some services use a header for the action
            # Headers are case-insensitive. Probably a better way to do this.
            match = self.headers.get('x-amz-target') or self.headers.get('X-Amz-Target')
            if match:
                action = match.split(".")[-1]

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

    def _get_int_param(self, param_name):
        val = self._get_param(param_name)
        if val is not None:
            return int(val)

    def _get_bool_param(self, param_name):
        val = self._get_param(param_name)
        if val is not None:
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False

    def _get_multi_param(self, param_prefix):
        """
        Given a querystring of ?LaunchConfigurationNames.member.1=my-test-1&LaunchConfigurationNames.member.2=my-test-2
        this will return ['my-test-1', 'my-test-2']
        """
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

    def _get_dict_param(self, param_prefix):
        """
        Given a parameter dict of
        {
            'Instances.SlaveInstanceType': ['m1.small'],
            'Instances.InstanceCount': ['1']
        }

        returns
        {
            "SlaveInstanceType": "m1.small",
            "InstanceCount": "1",
        }
        """
        params = {}
        for key, value in self.querystring.items():
            if key.startswith(param_prefix):
                params[camelcase_to_underscores(key.replace(param_prefix, ""))] = value[0]
        return params

    def _get_list_prefix(self, param_prefix):
        """
        Given a query dict like
        {
            'Steps.member.1.Name': ['example1'],
            'Steps.member.1.ActionOnFailure': ['TERMINATE_JOB_FLOW'],
            'Steps.member.1.HadoopJarStep.Jar': ['streaming1.jar'],
            'Steps.member.2.Name': ['example2'],
            'Steps.member.2.ActionOnFailure': ['TERMINATE_JOB_FLOW'],
            'Steps.member.2.HadoopJarStep.Jar': ['streaming2.jar'],
        }

        returns
        [{
            'name': u'example1',
            'action_on_failure': u'TERMINATE_JOB_FLOW',
            'hadoop_jar_step._jar': u'streaming1.jar',
        }, {
            'name': u'example2',
            'action_on_failure': u'TERMINATE_JOB_FLOW',
            'hadoop_jar_step._jar': u'streaming2.jar',
        }]
        """
        results = []
        param_index = 1
        while True:
            index_prefix = "{0}.{1}.".format(param_prefix, param_index)
            new_items = {}
            for key, value in self.querystring.items():
                if key.startswith(index_prefix):
                    new_items[camelcase_to_underscores(key.replace(index_prefix, ""))] = value[0]
            if not new_items:
                break
            results.append(new_items)
            param_index += 1
        return results

    @property
    def request_json(self):
        return 'JSON' in self.querystring.get('ContentType', [])


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
