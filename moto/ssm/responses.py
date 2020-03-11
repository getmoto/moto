from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import ssm_backends


class SimpleSystemManagerResponse(BaseResponse):
    @property
    def ssm_backend(self):
        return ssm_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, default=None):
        return self.request_params.get(param, default)

    def delete_parameter(self):
        name = self._get_param("Name")
        result = self.ssm_backend.delete_parameter(name)
        if result is None:
            error = {
                "__type": "ParameterNotFound",
                "message": "Parameter {0} not found.".format(name),
            }
            return json.dumps(error), dict(status=400)
        return json.dumps({})

    def delete_parameters(self):
        names = self._get_param("Names")
        result = self.ssm_backend.delete_parameters(names)

        response = {"DeletedParameters": [], "InvalidParameters": []}

        for name in names:
            if name in result:
                response["DeletedParameters"].append(name)
            else:
                response["InvalidParameters"].append(name)
        return json.dumps(response)

    def get_parameter(self):
        name = self._get_param("Name")
        with_decryption = self._get_param("WithDecryption")

        result = self.ssm_backend.get_parameter(name, with_decryption)

        if result is None:
            error = {
                "__type": "ParameterNotFound",
                "message": "Parameter {0} not found.".format(name),
            }
            return json.dumps(error), dict(status=400)

        response = {"Parameter": result.response_object(with_decryption, self.region)}
        return json.dumps(response)

    def get_parameters(self):
        names = self._get_param("Names")
        with_decryption = self._get_param("WithDecryption")

        result = self.ssm_backend.get_parameters(names, with_decryption)

        response = {"Parameters": [], "InvalidParameters": []}

        for parameter in result:
            param_data = parameter.response_object(with_decryption, self.region)
            response["Parameters"].append(param_data)

        param_names = [param.name for param in result]
        for name in names:
            if name not in param_names:
                response["InvalidParameters"].append(name)
        return json.dumps(response)

    def get_parameters_by_path(self):
        path = self._get_param("Path")
        with_decryption = self._get_param("WithDecryption")
        recursive = self._get_param("Recursive", False)
        filters = self._get_param("ParameterFilters")
        token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults", 10)

        result, next_token = self.ssm_backend.get_parameters_by_path(
            path,
            with_decryption,
            recursive,
            filters,
            next_token=token,
            max_results=max_results,
        )

        response = {"Parameters": [], "NextToken": next_token}

        for parameter in result:
            param_data = parameter.response_object(with_decryption, self.region)
            response["Parameters"].append(param_data)

        return json.dumps(response)

    def describe_parameters(self):
        page_size = 10
        filters = self._get_param("Filters")
        parameter_filters = self._get_param("ParameterFilters")
        token = self._get_param("NextToken")
        if hasattr(token, "strip"):
            token = token.strip()
        if not token:
            token = "0"
        token = int(token)

        result = self.ssm_backend.describe_parameters(filters, parameter_filters)

        response = {"Parameters": []}

        end = token + page_size
        for parameter in result[token:]:
            response["Parameters"].append(parameter.describe_response_object(False))

            token = token + 1
            if len(response["Parameters"]) == page_size:
                response["NextToken"] = str(end)
                break

        return json.dumps(response)

    def put_parameter(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        value = self._get_param("Value")
        type_ = self._get_param("Type")
        allowed_pattern = self._get_param("AllowedPattern")
        keyid = self._get_param("KeyId")
        overwrite = self._get_param("Overwrite", False)

        result = self.ssm_backend.put_parameter(
            name, description, value, type_, allowed_pattern, keyid, overwrite
        )

        if result is None:
            error = {
                "__type": "ParameterAlreadyExists",
                "message": "Parameter {0} already exists.".format(name),
            }
            return json.dumps(error), dict(status=400)

        response = {"Version": result}
        return json.dumps(response)

    def get_parameter_history(self):
        name = self._get_param("Name")
        with_decryption = self._get_param("WithDecryption")

        result = self.ssm_backend.get_parameter_history(name, with_decryption)

        if result is None:
            error = {
                "__type": "ParameterNotFound",
                "message": "Parameter {0} not found.".format(name),
            }
            return json.dumps(error), dict(status=400)

        response = {"Parameters": []}
        for parameter_version in result:
            param_data = parameter_version.describe_response_object(
                decrypt=with_decryption, include_labels=True
            )
            response["Parameters"].append(param_data)

        return json.dumps(response)

    def label_parameter_version(self):
        name = self._get_param("Name")
        version = self._get_param("ParameterVersion")
        labels = self._get_param("Labels")

        invalid_labels, version = self.ssm_backend.label_parameter_version(
            name, version, labels
        )

        response = {"InvalidLabels": invalid_labels, "ParameterVersion": version}
        return json.dumps(response)

    def add_tags_to_resource(self):
        resource_id = self._get_param("ResourceId")
        resource_type = self._get_param("ResourceType")
        tags = {t["Key"]: t["Value"] for t in self._get_param("Tags")}
        self.ssm_backend.add_tags_to_resource(resource_id, resource_type, tags)
        return json.dumps({})

    def remove_tags_from_resource(self):
        resource_id = self._get_param("ResourceId")
        resource_type = self._get_param("ResourceType")
        keys = self._get_param("TagKeys")
        self.ssm_backend.remove_tags_from_resource(resource_id, resource_type, keys)
        return json.dumps({})

    def list_tags_for_resource(self):
        resource_id = self._get_param("ResourceId")
        resource_type = self._get_param("ResourceType")
        tags = self.ssm_backend.list_tags_for_resource(resource_id, resource_type)
        tag_list = [{"Key": k, "Value": v} for (k, v) in tags.items()]
        response = {"TagList": tag_list}
        return json.dumps(response)

    def send_command(self):
        return json.dumps(self.ssm_backend.send_command(**self.request_params))

    def list_commands(self):
        return json.dumps(self.ssm_backend.list_commands(**self.request_params))

    def get_command_invocation(self):
        return json.dumps(
            self.ssm_backend.get_command_invocation(**self.request_params)
        )
