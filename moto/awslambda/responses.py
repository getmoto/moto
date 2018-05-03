from __future__ import unicode_literals

import json

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from moto.core.utils import amz_crc32, amzn_request_id
from moto.core.responses import BaseResponse
from .models import lambda_backends


class LambdaResponse(BaseResponse):
    @property
    def json_body(self):
        """
        :return: JSON
        :rtype: dict
        """
        return json.loads(self.body)

    @property
    def lambda_backend(self):
        """
        Get backend
        :return: Lambda Backend
        :rtype: moto.awslambda.models.LambdaBackend
        """
        return lambda_backends[self.region]

    def root(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'GET':
            return self._list_functions(request, full_url, headers)
        elif request.method == 'POST':
            return self._create_function(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    def function(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'GET':
            return self._get_function(request, full_url, headers)
        elif request.method == 'DELETE':
            return self._delete_function(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    def versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'GET':
            # This is ListVersionByFunction
            raise ValueError("Cannot handle request")
        elif request.method == 'POST':
            return self._publish_function(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    @amz_crc32
    @amzn_request_id
    def invoke(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'POST':
            return self._invoke(request, full_url)
        else:
            raise ValueError("Cannot handle request")

    @amz_crc32
    @amzn_request_id
    def invoke_async(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'POST':
            return self._invoke_async(request, full_url)
        else:
            raise ValueError("Cannot handle request")

    def tag(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'GET':
            return self._list_tags(request, full_url)
        elif request.method == 'POST':
            return self._tag_resource(request, full_url)
        elif request.method == 'DELETE':
            return self._untag_resource(request, full_url)
        else:
            raise ValueError("Cannot handle {0} request".format(request.method))

    def policy(self, request, full_url, headers):
        if request.method == 'GET':
            return self._get_policy(request, full_url, headers)
        if request.method == 'POST':
            return self._add_policy(request, full_url, headers)

    def _add_policy(self, request, full_url, headers):
        path = request.path if hasattr(request, 'path') else request.path_url
        function_name = path.split('/')[-2]
        if self.lambda_backend.get_function(function_name):
            policy = request.body.decode('utf8')
            self.lambda_backend.add_policy(function_name, policy)
            return 200, {}, json.dumps(dict(Statement=policy))
        else:
            return 404, {}, "{}"

    def _get_policy(self, request, full_url, headers):
        path = request.path if hasattr(request, 'path') else request.path_url
        function_name = path.split('/')[-2]
        if self.lambda_backend.get_function(function_name):
            lambda_function = self.lambda_backend.get_function(function_name)
            return 200, {}, json.dumps(dict(Policy="{\"Statement\":[" + lambda_function.policy + "]}"))
        else:
            return 404, {}, "{}"

    def _invoke(self, request, full_url):
        response_headers = {}

        function_name = self.path.rsplit('/', 2)[-2]
        qualifier = self._get_param('qualifier')

        fn = self.lambda_backend.get_function(function_name, qualifier)
        if fn:
            payload = fn.invoke(self.body, self.headers, response_headers)
            response_headers['Content-Length'] = str(len(payload))
            return 202, response_headers, payload
        else:
            return 404, response_headers, "{}"

    def _invoke_async(self, request, full_url):
        response_headers = {}

        function_name = self.path.rsplit('/', 3)[-3]

        fn = self.lambda_backend.get_function(function_name, None)
        if fn:
            payload = fn.invoke(self.body, self.headers, response_headers)
            response_headers['Content-Length'] = str(len(payload))
            return 202, response_headers, payload
        else:
            return 404, response_headers, "{}"

    def _list_functions(self, request, full_url, headers):
        result = {
            'Functions': []
        }

        for fn in self.lambda_backend.list_functions():
            json_data = fn.get_configuration()

            result['Functions'].append(json_data)

        return 200, {}, json.dumps(result)

    def _create_function(self, request, full_url, headers):
        try:
            fn = self.lambda_backend.create_function(self.json_body)
        except ValueError as e:
            return 400, {}, json.dumps({"Error": {"Code": e.args[0], "Message": e.args[1]}})
        else:
            config = fn.get_configuration()
            return 201, {}, json.dumps(config)

    def _publish_function(self, request, full_url, headers):
        function_name = self.path.rsplit('/', 2)[-2]

        fn = self.lambda_backend.publish_function(function_name)
        if fn:
            config = fn.get_configuration()
            return 200, {}, json.dumps(config)
        else:
            return 404, {}, "{}"

    def _delete_function(self, request, full_url, headers):
        function_name = self.path.rsplit('/', 1)[-1]
        qualifier = self._get_param('Qualifier', None)

        if self.lambda_backend.delete_function(function_name, qualifier):
            return 204, {}, ""
        else:
            return 404, {}, "{}"

    def _get_function(self, request, full_url, headers):
        function_name = self.path.rsplit('/', 1)[-1]
        qualifier = self._get_param('Qualifier', None)

        fn = self.lambda_backend.get_function(function_name, qualifier)

        if fn:
            code = fn.get_code()

            return 200, {}, json.dumps(code)
        else:
            return 404, {}, "{}"

    def _get_aws_region(self, full_url):
        region = self.region_regex.search(full_url)
        if region:
            return region.group(1)
        else:
            return self.default_region

    def _list_tags(self, request, full_url):
        function_arn = unquote(self.path.rsplit('/', 1)[-1])

        fn = self.lambda_backend.get_function_by_arn(function_arn)
        if fn:
            return 200, {}, json.dumps({'Tags': fn.tags})
        else:
            return 404, {}, "{}"

    def _tag_resource(self, request, full_url):
        function_arn = unquote(self.path.rsplit('/', 1)[-1])

        if self.lambda_backend.tag_resource(function_arn, self.json_body['Tags']):
            return 200, {}, "{}"
        else:
            return 404, {}, "{}"

    def _untag_resource(self, request, full_url):
        function_arn = unquote(self.path.rsplit('/', 1)[-1])
        tag_keys = self.querystring['tagKeys']

        if self.lambda_backend.untag_resource(function_arn, tag_keys):
            return 204, {}, "{}"
        else:
            return 404, {}, "{}"
