from __future__ import unicode_literals

import json
import re

from moto.core.responses import BaseResponse


class LambdaResponse(BaseResponse):

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

    def invoke(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == 'POST':
            return self._invoke(request, full_url)
        else:
            raise ValueError("Cannot handle request")

    def _invoke(self, request, full_url):
        response_headers = {}
        lambda_backend = self.get_lambda_backend(full_url)

        path = request.path if hasattr(request, 'path') else request.path_url
        function_name = path.split('/')[-2]

        if lambda_backend.has_function(function_name):
            fn = lambda_backend.get_function(function_name)
            payload = fn.invoke(self.body, self.headers, response_headers)
            response_headers['Content-Length'] = str(len(payload))
            return 202, response_headers, payload
        else:
            return 404, response_headers, "{}"

    def _list_functions(self, request, full_url, headers):
        lambda_backend = self.get_lambda_backend(full_url)
        return 200, {}, json.dumps({
            "Functions": [fn.get_configuration() for fn in lambda_backend.list_functions()],
            # "NextMarker": str(uuid.uuid4()),
        })

    def _create_function(self, request, full_url, headers):
        lambda_backend = self.get_lambda_backend(full_url)
        spec = json.loads(self.body)
        try:
            fn = lambda_backend.create_function(spec)
        except ValueError as e:
            return 400, {}, json.dumps({"Error": {"Code": e.args[0], "Message": e.args[1]}})
        else:
            config = fn.get_configuration()
            return 201, {}, json.dumps(config)

    def _delete_function(self, request, full_url, headers):
        lambda_backend = self.get_lambda_backend(full_url)

        path = request.path if hasattr(request, 'path') else request.path_url
        function_name = path.split('/')[-1]

        if lambda_backend.has_function(function_name):
            lambda_backend.delete_function(function_name)
            return 204, {}, ""
        else:
            return 404, {}, "{}"

    def _get_function(self, request, full_url, headers):
        lambda_backend = self.get_lambda_backend(full_url)

        path = request.path if hasattr(request, 'path') else request.path_url
        function_name = path.split('/')[-1]

        if lambda_backend.has_function(function_name):
            fn = lambda_backend.get_function(function_name)
            code = fn.get_code()
            return 200, {}, json.dumps(code)
        else:
            return 404, {}, "{}"

    def get_lambda_backend(self, full_url):
        from moto.awslambda.models import lambda_backends
        region = self._get_aws_region(full_url)
        return lambda_backends[region]

    def _get_aws_region(self, full_url):
        region = re.search(self.region_regex, full_url)
        if region:
            return region.group(1)
        else:
            return self.default_region
