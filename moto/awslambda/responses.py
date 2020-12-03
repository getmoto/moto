from __future__ import unicode_literals

import json

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from moto.core.utils import amz_crc32, amzn_request_id, path_url
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
        if request.method == "GET":
            return self._list_functions(request, full_url, headers)
        elif request.method == "POST":
            return self._create_function(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    def event_source_mappings(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            querystring = self.querystring
            event_source_arn = querystring.get("EventSourceArn", [None])[0]
            function_name = querystring.get("FunctionName", [None])[0]
            return self._list_event_source_mappings(event_source_arn, function_name)
        elif request.method == "POST":
            return self._create_event_source_mapping(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    def event_source_mapping(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        path = request.path if hasattr(request, "path") else path_url(request.url)
        uuid = path.split("/")[-1]
        if request.method == "GET":
            return self._get_event_source_mapping(uuid)
        elif request.method == "PUT":
            return self._update_event_source_mapping(uuid)
        elif request.method == "DELETE":
            return self._delete_event_source_mapping(uuid)
        else:
            raise ValueError("Cannot handle request")

    def function(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._get_function(request, full_url, headers)
        elif request.method == "DELETE":
            return self._delete_function(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    def versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            # This is ListVersionByFunction

            path = request.path if hasattr(request, "path") else path_url(request.url)
            function_name = path.split("/")[-2]
            return self._list_versions_by_function(function_name)

        elif request.method == "POST":
            return self._publish_function(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    @amz_crc32
    @amzn_request_id
    def invoke(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self._invoke(request, full_url)
        else:
            raise ValueError("Cannot handle request")

    @amz_crc32
    @amzn_request_id
    def invoke_async(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self._invoke_async(request, full_url)
        else:
            raise ValueError("Cannot handle request")

    def tag(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._list_tags(request, full_url)
        elif request.method == "POST":
            return self._tag_resource(request, full_url)
        elif request.method == "DELETE":
            return self._untag_resource(request, full_url)
        else:
            raise ValueError("Cannot handle {0} request".format(request.method))

    def policy(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._get_policy(request, full_url, headers)
        elif request.method == "POST":
            return self._add_policy(request, full_url, headers)
        elif request.method == "DELETE":
            return self._del_policy(request, full_url, headers, self.querystring)
        else:
            raise ValueError("Cannot handle {0} request".format(request.method))

    def configuration(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self._put_configuration(request)
        else:
            raise ValueError("Cannot handle request")

    def code(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self._put_code()
        else:
            raise ValueError("Cannot handle request")

    def function_concurrency(self, request, full_url, headers):
        http_method = request.method
        self.setup_class(request, full_url, headers)

        if http_method == "GET":
            return self._get_function_concurrency(request)
        elif http_method == "DELETE":
            return self._delete_function_concurrency(request)
        elif http_method == "PUT":
            return self._put_function_concurrency(request)
        else:
            raise ValueError("Cannot handle request")

    def _add_policy(self, request, full_url, headers):
        path = request.path if hasattr(request, "path") else path_url(request.url)
        function_name = path.split("/")[-2]
        if self.lambda_backend.get_function(function_name):
            statement = self.body
            self.lambda_backend.add_permission(function_name, statement)
            return 200, {}, json.dumps({"Statement": statement})
        else:
            return 404, {}, "{}"

    def _get_policy(self, request, full_url, headers):
        path = request.path if hasattr(request, "path") else path_url(request.url)
        function_name = path.split("/")[-2]
        if self.lambda_backend.get_function(function_name):
            out = self.lambda_backend.get_policy_wire_format(function_name)
            return 200, {}, out
        else:
            return 404, {}, "{}"

    def _del_policy(self, request, full_url, headers, querystring):
        path = request.path if hasattr(request, "path") else path_url(request.url)
        function_name = path.split("/")[-3]
        statement_id = path.split("/")[-1].split("?")[0]
        revision = querystring.get("RevisionId", "")
        if self.lambda_backend.get_function(function_name):
            self.lambda_backend.remove_permission(function_name, statement_id, revision)
            return 204, {}, "{}"
        else:
            return 404, {}, "{}"

    def _invoke(self, request, full_url):
        response_headers = {}

        # URL Decode in case it's a ARN:
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        qualifier = self._get_param("qualifier")

        payload = self.lambda_backend.invoke(
            function_name, qualifier, self.body, self.headers, response_headers
        )
        if payload:
            if request.headers.get("X-Amz-Invocation-Type") == "Event":
                status_code = 202
            elif request.headers.get("X-Amz-Invocation-Type") == "DryRun":
                status_code = 204
            else:
                if request.headers.get("X-Amz-Log-Type") != "Tail":
                    del response_headers["x-amz-log-result"]
                status_code = 200
            return status_code, response_headers, payload
        else:
            return 404, response_headers, "{}"

    def _invoke_async(self, request, full_url):
        response_headers = {}

        function_name = self.path.rsplit("/", 3)[-3]

        fn = self.lambda_backend.get_function(function_name, None)
        if fn:
            payload = fn.invoke(self.body, self.headers, response_headers)
            response_headers["Content-Length"] = str(len(payload))
            return 202, response_headers, payload
        else:
            return 404, response_headers, "{}"

    def _list_functions(self, request, full_url, headers):
        result = {"Functions": []}

        for fn in self.lambda_backend.list_functions():
            json_data = fn.get_configuration()
            json_data["Version"] = "$LATEST"
            result["Functions"].append(json_data)

        return 200, {}, json.dumps(result)

    def _list_versions_by_function(self, function_name):
        result = {"Versions": []}

        functions = self.lambda_backend.list_versions_by_function(function_name)
        if functions:
            for fn in functions:
                json_data = fn.get_configuration()
                result["Versions"].append(json_data)

        return 200, {}, json.dumps(result)

    def _create_function(self, request, full_url, headers):
        fn = self.lambda_backend.create_function(self.json_body)
        config = fn.get_configuration()
        return 201, {}, json.dumps(config)

    def _create_event_source_mapping(self, request, full_url, headers):
        fn = self.lambda_backend.create_event_source_mapping(self.json_body)
        config = fn.get_configuration()
        return 201, {}, json.dumps(config)

    def _list_event_source_mappings(self, event_source_arn, function_name):
        esms = self.lambda_backend.list_event_source_mappings(
            event_source_arn, function_name
        )
        result = {"EventSourceMappings": [esm.get_configuration() for esm in esms]}
        return 200, {}, json.dumps(result)

    def _get_event_source_mapping(self, uuid):
        result = self.lambda_backend.get_event_source_mapping(uuid)
        if result:
            return 200, {}, json.dumps(result.get_configuration())
        else:
            return 404, {}, "{}"

    def _update_event_source_mapping(self, uuid):
        result = self.lambda_backend.update_event_source_mapping(uuid, self.json_body)
        if result:
            return 202, {}, json.dumps(result.get_configuration())
        else:
            return 404, {}, "{}"

    def _delete_event_source_mapping(self, uuid):
        esm = self.lambda_backend.delete_event_source_mapping(uuid)
        if esm:
            json_result = esm.get_configuration()
            json_result.update({"State": "Deleting"})
            return 202, {}, json.dumps(json_result)
        else:
            return 404, {}, "{}"

    def _publish_function(self, request, full_url, headers):
        function_name = self.path.rsplit("/", 2)[-2]

        fn = self.lambda_backend.publish_function(function_name)
        if fn:
            config = fn.get_configuration()
            return 201, {}, json.dumps(config)
        else:
            return 404, {}, "{}"

    def _delete_function(self, request, full_url, headers):
        function_name = unquote(self.path.rsplit("/", 1)[-1])
        qualifier = self._get_param("Qualifier", None)

        if self.lambda_backend.delete_function(function_name, qualifier):
            return 204, {}, ""
        else:
            return 404, {}, "{}"

    def _get_function(self, request, full_url, headers):
        function_name = unquote(self.path.rsplit("/", 1)[-1])
        qualifier = self._get_param("Qualifier", None)

        fn = self.lambda_backend.get_function(function_name, qualifier)

        if fn:
            code = fn.get_code()
            if qualifier is None or qualifier == "$LATEST":
                code["Configuration"]["Version"] = "$LATEST"
            if qualifier == "$LATEST":
                code["Configuration"]["FunctionArn"] += ":$LATEST"
            return 200, {}, json.dumps(code)
        else:
            return 404, {"x-amzn-ErrorType": "ResourceNotFoundException"}, "{}"

    def _get_aws_region(self, full_url):
        region = self.region_regex.search(full_url)
        if region:
            return region.group(1)
        else:
            return self.default_region

    def _list_tags(self, request, full_url):
        function_arn = unquote(self.path.rsplit("/", 1)[-1])

        fn = self.lambda_backend.get_function_by_arn(function_arn)
        if fn:
            return 200, {}, json.dumps({"Tags": fn.tags})
        else:
            return 404, {}, "{}"

    def _tag_resource(self, request, full_url):
        function_arn = unquote(self.path.rsplit("/", 1)[-1])

        if self.lambda_backend.tag_resource(function_arn, self.json_body["Tags"]):
            return 200, {}, "{}"
        else:
            return 404, {}, "{}"

    def _untag_resource(self, request, full_url):
        function_arn = unquote(self.path.rsplit("/", 1)[-1])
        tag_keys = self.querystring["tagKeys"]

        if self.lambda_backend.untag_resource(function_arn, tag_keys):
            return 204, {}, "{}"
        else:
            return 404, {}, "{}"

    def _put_configuration(self, request):
        function_name = self.path.rsplit("/", 2)[-2]
        qualifier = self._get_param("Qualifier", None)
        resp = self.lambda_backend.update_function_configuration(
            function_name, qualifier, body=self.json_body
        )

        if resp:
            return 200, {}, json.dumps(resp)
        else:
            return 404, {}, "{}"

    def _put_code(self):
        function_name = self.path.rsplit("/", 2)[-2]
        qualifier = self._get_param("Qualifier", None)
        resp = self.lambda_backend.update_function_code(
            function_name, qualifier, body=self.json_body
        )

        if resp:
            return 200, {}, json.dumps(resp)
        else:
            return 404, {}, "{}"

    def _get_function_concurrency(self, request):
        path_function_name = self.path.rsplit("/", 2)[-2]
        function_name = self.lambda_backend.get_function(path_function_name)

        if function_name is None:
            return 404, {}, "{}"

        resp = self.lambda_backend.get_function_concurrency(path_function_name)
        return 200, {}, json.dumps({"ReservedConcurrentExecutions": resp})

    def _delete_function_concurrency(self, request):
        path_function_name = self.path.rsplit("/", 2)[-2]
        function_name = self.lambda_backend.get_function(path_function_name)

        if function_name is None:
            return 404, {}, "{}"

        self.lambda_backend.delete_function_concurrency(path_function_name)

        return 204, {}, "{}"

    def _put_function_concurrency(self, request):
        path_function_name = self.path.rsplit("/", 2)[-2]
        function = self.lambda_backend.get_function(path_function_name)

        if function is None:
            return 404, {}, "{}"

        concurrency = self._get_param("ReservedConcurrentExecutions", None)
        resp = self.lambda_backend.put_function_concurrency(
            path_function_name, concurrency
        )

        return 200, {}, json.dumps({"ReservedConcurrentExecutions": resp})
