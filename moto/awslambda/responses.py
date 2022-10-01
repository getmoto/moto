import json
import sys

from urllib.parse import unquote

from moto.core.utils import path_url
from moto.utilities.aws_headers import amz_crc32, amzn_request_id
from moto.core.responses import BaseResponse
from .models import lambda_backends


class LambdaResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="awslambda")

    @property
    def json_body(self):
        """
        :return: JSON
        :rtype: dict
        """
        return json.loads(self.body)

    @property
    def backend(self):
        return lambda_backends[self.current_account][self.region]

    def root(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._list_functions()
        elif request.method == "POST":
            return self._create_function()
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
            return self._create_event_source_mapping()
        else:
            raise ValueError("Cannot handle request")

    def aliases(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self._create_alias()

    def alias(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self._delete_alias()
        elif request.method == "GET":
            return self._get_alias()
        elif request.method == "PUT":
            return self._update_alias()

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

    def list_layers(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._list_layers()

    def layers_version(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self._delete_layer_version()
        elif request.method == "GET":
            return self._get_layer_version()

    def layers_versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._get_layer_versions()
        if request.method == "POST":
            return self._publish_layer_version()

    def function(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._get_function()
        elif request.method == "DELETE":
            return self._delete_function()
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
            return self._publish_function()
        else:
            raise ValueError("Cannot handle request")

    @amz_crc32
    @amzn_request_id
    def invoke(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self._invoke(request)
        else:
            raise ValueError("Cannot handle request")

    @amz_crc32
    @amzn_request_id
    def invoke_async(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self._invoke_async()
        else:
            raise ValueError("Cannot handle request")

    def tag(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._list_tags()
        elif request.method == "POST":
            return self._tag_resource()
        elif request.method == "DELETE":
            return self._untag_resource()
        else:
            raise ValueError("Cannot handle {0} request".format(request.method))

    def policy(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._get_policy(request)
        elif request.method == "POST":
            return self._add_policy(request)
        elif request.method == "DELETE":
            return self._del_policy(request, self.querystring)
        else:
            raise ValueError("Cannot handle {0} request".format(request.method))

    def configuration(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self._put_configuration()
        if request.method == "GET":
            return self._get_function_configuration()
        else:
            raise ValueError("Cannot handle request")

    def code(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self._put_code()
        else:
            raise ValueError("Cannot handle request")

    def code_signing_config(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self._get_code_signing_config()

    def function_concurrency(self, request, full_url, headers):
        http_method = request.method
        self.setup_class(request, full_url, headers)

        if http_method == "GET":
            return self._get_function_concurrency()
        elif http_method == "DELETE":
            return self._delete_function_concurrency()
        elif http_method == "PUT":
            return self._put_function_concurrency()
        else:
            raise ValueError("Cannot handle request")

    def function_url_config(self, request, full_url, headers):
        http_method = request.method
        self.setup_class(request, full_url, headers)

        if http_method == "DELETE":
            return self._delete_function_url_config()
        elif http_method == "GET":
            return self._get_function_url_config()
        elif http_method == "POST":
            return self._create_function_url_config()
        elif http_method == "PUT":
            return self._update_function_url_config()

    def _add_policy(self, request):
        path = request.path if hasattr(request, "path") else path_url(request.url)
        function_name = unquote(path.split("/")[-2])
        qualifier = self.querystring.get("Qualifier", [None])[0]
        statement = self.body
        statement = self.backend.add_permission(function_name, qualifier, statement)
        return 200, {}, json.dumps({"Statement": json.dumps(statement)})

    def _get_policy(self, request):
        path = request.path if hasattr(request, "path") else path_url(request.url)
        function_name = unquote(path.split("/")[-2])
        out = self.backend.get_policy(function_name)
        return 200, {}, out

    def _del_policy(self, request, querystring):
        path = request.path if hasattr(request, "path") else path_url(request.url)
        function_name = unquote(path.split("/")[-3])
        statement_id = path.split("/")[-1].split("?")[0]
        revision = querystring.get("RevisionId", "")
        if self.backend.get_function(function_name):
            self.backend.remove_permission(function_name, statement_id, revision)
            return 204, {}, "{}"
        else:
            return 404, {}, "{}"

    def _invoke(self, request):
        response_headers = {}

        # URL Decode in case it's a ARN:
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        qualifier = self._get_param("qualifier")

        payload = self.backend.invoke(
            function_name, qualifier, self.body, self.headers, response_headers
        )
        if payload:
            if request.headers.get("X-Amz-Invocation-Type") != "Event":
                if sys.getsizeof(payload) > 6000000:
                    response_headers["Content-Length"] = "142"
                    response_headers["x-amz-function-error"] = "Unhandled"
                    error_dict = {
                        "errorMessage": "Response payload size exceeded maximum allowed payload size (6291556 bytes).",
                        "errorType": "Function.ResponseSizeTooLarge",
                    }
                    payload = json.dumps(error_dict).encode("utf-8")

            response_headers["content-type"] = "application/json"
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

    def _invoke_async(self):
        response_headers = {}

        function_name = unquote(self.path.rsplit("/", 3)[-3])

        fn = self.backend.get_function(function_name, None)
        payload = fn.invoke(self.body, self.headers, response_headers)
        response_headers["Content-Length"] = str(len(payload))
        return 202, response_headers, payload

    def _list_functions(self):
        querystring = self.querystring
        func_version = querystring.get("FunctionVersion", [None])[0]
        result = {"Functions": []}

        for fn in self.backend.list_functions(func_version):
            json_data = fn.get_configuration()
            result["Functions"].append(json_data)

        return 200, {}, json.dumps(result)

    def _list_versions_by_function(self, function_name):
        result = {"Versions": []}

        functions = self.backend.list_versions_by_function(function_name)
        if functions:
            for fn in functions:
                json_data = fn.get_configuration()
                result["Versions"].append(json_data)

        return 200, {}, json.dumps(result)

    def _create_function(self):
        fn = self.backend.create_function(self.json_body)
        config = fn.get_configuration(on_create=True)
        return 201, {}, json.dumps(config)

    def _create_function_url_config(self):
        function_name = unquote(self.path.split("/")[-2])
        config = self.backend.create_function_url_config(function_name, self.json_body)
        return 201, {}, json.dumps(config.to_dict())

    def _delete_function_url_config(self):
        function_name = unquote(self.path.split("/")[-2])
        self.backend.delete_function_url_config(function_name)
        return 204, {}, "{}"

    def _get_function_url_config(self):
        function_name = unquote(self.path.split("/")[-2])
        config = self.backend.get_function_url_config(function_name)
        return 201, {}, json.dumps(config.to_dict())

    def _update_function_url_config(self):
        function_name = unquote(self.path.split("/")[-2])
        config = self.backend.update_function_url_config(function_name, self.json_body)
        return 200, {}, json.dumps(config.to_dict())

    def _create_event_source_mapping(self):
        fn = self.backend.create_event_source_mapping(self.json_body)
        config = fn.get_configuration()
        return 201, {}, json.dumps(config)

    def _list_event_source_mappings(self, event_source_arn, function_name):
        esms = self.backend.list_event_source_mappings(event_source_arn, function_name)
        result = {"EventSourceMappings": [esm.get_configuration() for esm in esms]}
        return 200, {}, json.dumps(result)

    def _get_event_source_mapping(self, uuid):
        result = self.backend.get_event_source_mapping(uuid)
        if result:
            return 200, {}, json.dumps(result.get_configuration())
        else:
            return 404, {}, "{}"

    def _update_event_source_mapping(self, uuid):
        result = self.backend.update_event_source_mapping(uuid, self.json_body)
        if result:
            return 202, {}, json.dumps(result.get_configuration())
        else:
            return 404, {}, "{}"

    def _delete_event_source_mapping(self, uuid):
        esm = self.backend.delete_event_source_mapping(uuid)
        if esm:
            json_result = esm.get_configuration()
            json_result.update({"State": "Deleting"})
            return 202, {}, json.dumps(json_result)
        else:
            return 404, {}, "{}"

    def _publish_function(self):
        function_name = unquote(self.path.split("/")[-2])
        description = self._get_param("Description")

        fn = self.backend.publish_function(function_name, description)
        config = fn.get_configuration()
        return 201, {}, json.dumps(config)

    def _delete_function(self):
        function_name = unquote(self.path.rsplit("/", 1)[-1])
        qualifier = self._get_param("Qualifier", None)

        self.backend.delete_function(function_name, qualifier)
        return 204, {}, ""

    @staticmethod
    def _set_configuration_qualifier(configuration, qualifier):
        if qualifier is None or qualifier == "$LATEST":
            configuration["Version"] = "$LATEST"
        if qualifier == "$LATEST":
            configuration["FunctionArn"] += ":$LATEST"
        return configuration

    def _get_function(self):
        function_name = unquote(self.path.rsplit("/", 1)[-1])
        qualifier = self._get_param("Qualifier", None)

        fn = self.backend.get_function(function_name, qualifier)

        code = fn.get_code()
        code["Configuration"] = self._set_configuration_qualifier(
            code["Configuration"], qualifier
        )
        return 200, {}, json.dumps(code)

    def _get_function_configuration(self):
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        qualifier = self._get_param("Qualifier", None)

        fn = self.backend.get_function(function_name, qualifier)

        configuration = self._set_configuration_qualifier(
            fn.get_configuration(), qualifier
        )
        return 200, {}, json.dumps(configuration)

    def _get_aws_region(self, full_url):
        region = self.region_regex.search(full_url)
        if region:
            return region.group(1)
        else:
            return self.default_region

    def _list_tags(self):
        function_arn = unquote(self.path.rsplit("/", 1)[-1])

        tags = self.backend.list_tags(function_arn)
        return 200, {}, json.dumps({"Tags": tags})

    def _tag_resource(self):
        function_arn = unquote(self.path.rsplit("/", 1)[-1])

        self.backend.tag_resource(function_arn, self.json_body["Tags"])
        return 200, {}, "{}"

    def _untag_resource(self):
        function_arn = unquote(self.path.rsplit("/", 1)[-1])
        tag_keys = self.querystring["tagKeys"]

        self.backend.untag_resource(function_arn, tag_keys)
        return 204, {}, "{}"

    def _put_configuration(self):
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        qualifier = self._get_param("Qualifier", None)
        resp = self.backend.update_function_configuration(
            function_name, qualifier, body=self.json_body
        )

        if resp:
            return 200, {}, json.dumps(resp)
        else:
            return 404, {}, "{}"

    def _put_code(self):
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        qualifier = self._get_param("Qualifier", None)
        resp = self.backend.update_function_code(
            function_name, qualifier, body=self.json_body
        )

        if resp:
            return 200, {}, json.dumps(resp)
        else:
            return 404, {}, "{}"

    def _get_code_signing_config(self):
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        resp = self.backend.get_code_signing_config(function_name)
        return 200, {}, json.dumps(resp)

    def _get_function_concurrency(self):
        path_function_name = unquote(self.path.rsplit("/", 2)[-2])
        function_name = self.backend.get_function(path_function_name)

        if function_name is None:
            return 404, {}, "{}"

        resp = self.backend.get_function_concurrency(path_function_name)
        return 200, {}, json.dumps({"ReservedConcurrentExecutions": resp})

    def _delete_function_concurrency(self):
        path_function_name = unquote(self.path.rsplit("/", 2)[-2])
        function_name = self.backend.get_function(path_function_name)

        if function_name is None:
            return 404, {}, "{}"

        self.backend.delete_function_concurrency(path_function_name)

        return 204, {}, "{}"

    def _put_function_concurrency(self):
        path_function_name = unquote(self.path.rsplit("/", 2)[-2])
        function = self.backend.get_function(path_function_name)

        if function is None:
            return 404, {}, "{}"

        concurrency = self._get_param("ReservedConcurrentExecutions", None)
        resp = self.backend.put_function_concurrency(path_function_name, concurrency)

        return 200, {}, json.dumps({"ReservedConcurrentExecutions": resp})

    def _list_layers(self):
        layers = self.backend.list_layers()
        return 200, {}, json.dumps({"Layers": layers})

    def _delete_layer_version(self):
        layer_name = self.path.split("/")[-3]
        layer_version = self.path.split("/")[-1]

        self.backend.delete_layer_version(layer_name, layer_version)
        return 200, {}, "{}"

    def _get_layer_version(self):
        layer_name = self.path.split("/")[-3]
        layer_version = self.path.split("/")[-1]

        layer = self.backend.get_layer_version(layer_name, layer_version)
        return 200, {}, json.dumps(layer.get_layer_version())

    def _get_layer_versions(self):
        layer_name = self.path.rsplit("/", 2)[-2]
        layer_versions = self.backend.get_layer_versions(layer_name)
        return (
            200,
            {},
            json.dumps(
                {"LayerVersions": [lv.get_layer_version() for lv in layer_versions]}
            ),
        )

    def _publish_layer_version(self):
        spec = self.json_body
        if "LayerName" not in spec:
            spec["LayerName"] = self.path.rsplit("/", 2)[-2]
        layer_version = self.backend.publish_layer_version(spec)
        config = layer_version.get_layer_version()
        return 201, {}, json.dumps(config)

    def _create_alias(self):
        function_name = unquote(self.path.rsplit("/", 2)[-2])
        params = json.loads(self.body)
        alias_name = params.get("Name")
        description = params.get("Description", "")
        function_version = params.get("FunctionVersion")
        routing_config = params.get("RoutingConfig")
        alias = self.backend.create_alias(
            name=alias_name,
            function_name=function_name,
            function_version=function_version,
            description=description,
            routing_config=routing_config,
        )
        return 201, {}, json.dumps(alias.to_json())

    def _delete_alias(self):
        function_name = unquote(self.path.rsplit("/")[-3])
        alias_name = unquote(self.path.rsplit("/", 2)[-1])
        self.backend.delete_alias(name=alias_name, function_name=function_name)
        return 201, {}, "{}"

    def _get_alias(self):
        function_name = unquote(self.path.rsplit("/")[-3])
        alias_name = unquote(self.path.rsplit("/", 2)[-1])
        alias = self.backend.get_alias(name=alias_name, function_name=function_name)
        return 201, {}, json.dumps(alias.to_json())

    def _update_alias(self):
        function_name = unquote(self.path.rsplit("/")[-3])
        alias_name = unquote(self.path.rsplit("/", 2)[-1])
        params = json.loads(self.body)
        description = params.get("Description")
        function_version = params.get("FunctionVersion")
        routing_config = params.get("RoutingConfig")
        alias = self.backend.update_alias(
            name=alias_name,
            function_name=function_name,
            function_version=function_version,
            description=description,
            routing_config=routing_config,
        )
        return 201, {}, json.dumps(alias.to_json())
