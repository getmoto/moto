from __future__ import unicode_literals
import datetime
import json
import logging
import re

import pytz
from boto.exception import JSONResponseError

from jinja2 import Environment, DictLoader, TemplateNotFound

import six
from six.moves.urllib.parse import parse_qs, urlparse

import xmltodict
from pkg_resources import resource_filename
from werkzeug.exceptions import HTTPException
from moto.compat import OrderedDict
from moto.core.utils import camelcase_to_underscores, method_names_from_class


log = logging.getLogger(__name__)


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
    aws_service_spec = None

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
            if 'json' in request.headers.get('content-type', []) and self.aws_service_spec:
                if isinstance(self.body, six.binary_type):
                    decoded = json.loads(self.body.decode('utf-8'))
                else:
                    decoded = json.loads(self.body)

                target = request.headers.get('x-amz-target') or request.headers.get('X-Amz-Target')
                service, method = target.split('.')
                input_spec = self.aws_service_spec.input_spec(method)
                flat = flatten_json_request_body('', decoded, input_spec)
                for key, value in flat.items():
                    querystring[key] = [value]
            else:
                querystring.update(parse_qs(self.body, keep_blank_values=True))
        if not querystring:
            querystring.update(headers)

        querystring = _decode_dict(querystring)

        self.uri = full_url
        self.path = urlparse(full_url).path
        self.querystring = querystring
        self.method = request.method
        self.region = self.get_region_from_url(full_url)

        self.headers = request.headers
        self.response_headers = headers

    def get_region_from_url(self, full_url):
        match = re.search(self.region_regex, full_url)
        if match:
            region = match.group(1)
        else:
            region = self.default_region
        return region

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

    def _get_param(self, param_name, if_none=None):
        val = self.querystring.get(param_name)
        if val is not None:
            return val[0]
        return if_none

    def _get_int_param(self, param_name, if_none=None):
        val = self._get_param(param_name)
        if val is not None:
            return int(val)
        return if_none

    def _get_bool_param(self, param_name, if_none=None):
        val = self._get_param(param_name)
        if val is not None:
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
        return if_none

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

    def _get_map_prefix(self, param_prefix):
        results = {}
        param_index = 1
        while 1:
            index_prefix = '{0}.{1}.'.format(param_prefix, param_index)

            k, v = None, None
            for key, value in self.querystring.items():
                if key.startswith(index_prefix):
                    if key.endswith('.key'):
                        k = value[0]
                    elif key.endswith('.value'):
                        v = value[0]

            if not (k and v):
                break

            results[k] = v
            param_index += 1

        return results

    @property
    def request_json(self):
        return 'JSON' in self.querystring.get('ContentType', [])

    def is_not_dryrun(self, action):
        if 'true' in self.querystring.get('DryRun', ['false']):
            raise JSONResponseError(400, 'DryRunOperation', body={'message': 'An error occurred (DryRunOperation) when calling the %s operation: Request would have succeeded, but DryRun flag is set' % action})
        return True

def metadata_response(request, full_url, headers):
    """
    Mock response for localhost metadata

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AESDG-chapter-instancedata.html
    """
    parsed_url = urlparse(full_url)
    tomorrow = datetime.datetime.utcnow() + datetime.timedelta(days=1)
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


class _RecursiveDictRef(object):
    """Store a recursive reference to dict."""
    def __init__(self):
        self.key = None
        self.dic = {}

    def __repr__(self):
        return '{!r}'.format(self.dic)

    def __getattr__(self, key):
        return self.dic.__getattr__(key)

    def set_reference(self, key, dic):
        """Set the RecursiveDictRef object to keep reference to dict object
        (dic) at the key.

        """
        self.key = key
        self.dic = dic


class AWSServiceSpec(object):
    """Parse data model from botocore. This is used to recover type info
    for fields in AWS API XML response.

    """

    def __init__(self, path):
        self.path = resource_filename('botocore', path)
        with open(self.path) as f:
            spec = json.load(f)
        self.metadata = spec['metadata']
        self.operations = spec['operations']
        self.shapes = spec['shapes']

    def input_spec(self, operation):
        try:
            op = self.operations[operation]
        except KeyError:
            raise ValueError('Invalid operation: {}'.format(operation))
        if 'input' not in op:
            return {}
        shape = self.shapes[op['input']['shape']]
        return self._expand(shape)

    def output_spec(self, operation):
        """Produce a JSON with a valid API response syntax for operation, but
        with type information. Each node represented by a key has the
        value containing field type, e.g.,

          output_spec["SomeBooleanNode"] => {"type": "boolean"}

        """
        try:
            op = self.operations[operation]
        except KeyError:
            raise ValueError('Invalid operation: {}'.format(operation))
        if 'output' not in op:
            return {}
        shape = self.shapes[op['output']['shape']]
        return self._expand(shape)

    def _expand(self, shape):
        def expand(dic, seen=None):
            seen = seen or {}
            if dic['type'] == 'structure':
                nodes = {}
                for k, v in dic['members'].items():
                    seen_till_here = dict(seen)
                    if k in seen_till_here:
                        nodes[k] = seen_till_here[k]
                        continue
                    seen_till_here[k] = _RecursiveDictRef()
                    nodes[k] = expand(self.shapes[v['shape']], seen_till_here)
                    seen_till_here[k].set_reference(k, nodes[k])
                nodes['type'] = 'structure'
                return nodes

            elif dic['type'] == 'list':
                seen_till_here = dict(seen)
                shape = dic['member']['shape']
                if shape in seen_till_here:
                    return seen_till_here[shape]
                seen_till_here[shape] = _RecursiveDictRef()
                expanded = expand(self.shapes[shape], seen_till_here)
                seen_till_here[shape].set_reference(shape, expanded)
                return {'type': 'list', 'member': expanded}

            elif dic['type'] == 'map':
                seen_till_here = dict(seen)
                node = {'type': 'map'}

                if 'shape' in dic['key']:
                    shape = dic['key']['shape']
                    seen_till_here[shape] = _RecursiveDictRef()
                    node['key'] = expand(self.shapes[shape], seen_till_here)
                    seen_till_here[shape].set_reference(shape, node['key'])
                else:
                    node['key'] = dic['key']['type']

                if 'shape' in dic['value']:
                    shape = dic['value']['shape']
                    seen_till_here[shape] = _RecursiveDictRef()
                    node['value'] = expand(self.shapes[shape], seen_till_here)
                    seen_till_here[shape].set_reference(shape, node['value'])
                else:
                    node['value'] = dic['value']['type']

                return node

            else:
                return {'type': dic['type']}

        return expand(shape)


def to_str(value, spec):
    vtype = spec['type']
    if vtype == 'boolean':
        return 'true' if value else 'false'
    elif vtype == 'integer':
        return str(value)
    elif vtype == 'float':
        return str(value)
    elif vtype == 'timestamp':
        return datetime.datetime.utcfromtimestamp(
            value).replace(tzinfo=pytz.utc).isoformat()
    elif vtype == 'string':
        return str(value)
    elif value is None:
        return 'null'
    else:
        raise TypeError('Unknown type {}'.format(vtype))


def from_str(value, spec):
    vtype = spec['type']
    if vtype == 'boolean':
        return True if value == 'true' else False
    elif vtype == 'integer':
        return int(value)
    elif vtype == 'float':
        return float(value)
    elif vtype == 'timestamp':
        return value
    elif vtype == 'string':
        return value
    raise TypeError('Unknown type {}'.format(vtype))


def flatten_json_request_body(prefix, dict_body, spec):
    """Convert a JSON request body into query params."""
    if len(spec) == 1 and 'type' in spec:
        return {prefix: to_str(dict_body, spec)}

    flat = {}
    for key, value in dict_body.items():
        node_type = spec[key]['type']
        if node_type == 'list':
            for idx, v in enumerate(value, 1):
                pref = key + '.member.' + str(idx)
                flat.update(flatten_json_request_body(pref, v, spec[key]['member']))
        elif node_type == 'map':
            for idx, (k, v) in enumerate(value.items(), 1):
                pref = key + '.entry.' + str(idx)
                flat.update(flatten_json_request_body(pref + '.key', k, spec[key]['key']))
                flat.update(flatten_json_request_body(pref + '.value', v, spec[key]['value']))
        else:
            flat.update(flatten_json_request_body(key, value, spec[key]))

    if prefix:
        prefix = prefix + '.'
    return dict((prefix + k, v) for k, v in flat.items())


def xml_to_json_response(service_spec, operation, xml, result_node=None):
    """Convert rendered XML response to JSON for use with boto3."""

    def transform(value, spec):
        """Apply transformations to make the output JSON comply with the
        expected form. This function applies:

          (1) Type cast to nodes with "type" property (e.g., 'true' to
              True). XML field values are all in text so this step is
              necessary to convert it to valid JSON objects.

          (2) Squashes "member" nodes to lists.

        """
        if len(spec) == 1:
            return from_str(value, spec)

        od = OrderedDict()
        for k, v in value.items():
            if k.startswith('@'):
                continue

            if k not in spec:
                # this can happen when with an older version of
                # botocore for which the node in XML template is not
                # defined in service spec.
                log.warning('Field %s is not defined by the botocore version in use', k)
                continue

            if spec[k]['type'] == 'list':
                if v is None:
                    od[k] = []
                elif len(spec[k]['member']) == 1:
                    if isinstance(v['member'], list):
                        od[k] = transform(v['member'], spec[k]['member'])
                    else:
                        od[k] = [transform(v['member'], spec[k]['member'])]
                elif isinstance(v['member'], list):
                    od[k] = [transform(o, spec[k]['member']) for o in v['member']]
                elif isinstance(v['member'], OrderedDict):
                    od[k] = [transform(v['member'], spec[k]['member'])]
                else:
                    raise ValueError('Malformatted input')
            elif spec[k]['type'] == 'map':
                if v is None:
                    od[k] = {}
                else:
                    items = ([v['entry']] if not isinstance(v['entry'], list) else
                             v['entry'])
                    for item in items:
                        key = from_str(item['key'], spec[k]['key'])
                        val = from_str(item['value'], spec[k]['value'])
                        if k not in od:
                            od[k] = {}
                        od[k][key] = val
            else:
                if v is None:
                    od[k] = None
                else:
                    od[k] = transform(v, spec[k])
        return od

    dic = xmltodict.parse(xml)
    output_spec = service_spec.output_spec(operation)
    try:
        for k in (result_node or (operation + 'Response', operation + 'Result')):
            dic = dic[k]
    except KeyError:
        return None
    else:
        return transform(dic, output_spec)
    return None
