from __future__ import unicode_literals

import re
from collections import defaultdict

from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.ec2 import ec2_backends
from moto.cloudformation import cloudformation_backends

import datetime
import time
import uuid
import itertools

from .exceptions import (
    ValidationException,
    InvalidFilterValue,
    InvalidFilterOption,
    InvalidFilterKey,
)


class Parameter(BaseModel):
    def __init__(
        self,
        name,
        value,
        type,
        description,
        allowed_pattern,
        keyid,
        last_modified_date,
        version,
    ):
        self.name = name
        self.type = type
        self.description = description
        self.allowed_pattern = allowed_pattern
        self.keyid = keyid
        self.last_modified_date = last_modified_date
        self.version = version

        if self.type == "SecureString":
            if not self.keyid:
                self.keyid = "alias/aws/ssm"

            self.value = self.encrypt(value)
        else:
            self.value = value

    def encrypt(self, value):
        return "kms:{}:".format(self.keyid) + value

    def decrypt(self, value):
        if self.type != "SecureString":
            return value

        prefix = "kms:{}:".format(self.keyid or "default")
        if value.startswith(prefix):
            return value[len(prefix) :]

    def response_object(self, decrypt=False):
        r = {
            "Name": self.name,
            "Type": self.type,
            "Value": self.decrypt(self.value) if decrypt else self.value,
            "Version": self.version,
        }

        return r

    def describe_response_object(self, decrypt=False):
        r = self.response_object(decrypt)
        r["LastModifiedDate"] = int(self.last_modified_date)
        r["LastModifiedUser"] = "N/A"

        if self.description:
            r["Description"] = self.description

        if self.keyid:
            r["KeyId"] = self.keyid

        if self.allowed_pattern:
            r["AllowedPattern"] = self.allowed_pattern

        return r


MAX_TIMEOUT_SECONDS = 3600


class Command(BaseModel):
    def __init__(
        self,
        comment="",
        document_name="",
        timeout_seconds=MAX_TIMEOUT_SECONDS,
        instance_ids=None,
        max_concurrency="",
        max_errors="",
        notification_config=None,
        output_s3_bucket_name="",
        output_s3_key_prefix="",
        output_s3_region="",
        parameters=None,
        service_role_arn="",
        targets=None,
        backend_region="us-east-1",
    ):

        if instance_ids is None:
            instance_ids = []

        if notification_config is None:
            notification_config = {}

        if parameters is None:
            parameters = {}

        if targets is None:
            targets = []

        self.error_count = 0
        self.completed_count = len(instance_ids)
        self.target_count = len(instance_ids)
        self.command_id = str(uuid.uuid4())
        self.status = "Success"
        self.status_details = "Details placeholder"

        self.requested_date_time = datetime.datetime.now()
        self.requested_date_time_iso = self.requested_date_time.isoformat()
        expires_after = self.requested_date_time + datetime.timedelta(
            0, timeout_seconds
        )
        self.expires_after = expires_after.isoformat()

        self.comment = comment
        self.document_name = document_name
        self.instance_ids = instance_ids
        self.max_concurrency = max_concurrency
        self.max_errors = max_errors
        self.notification_config = notification_config
        self.output_s3_bucket_name = output_s3_bucket_name
        self.output_s3_key_prefix = output_s3_key_prefix
        self.output_s3_region = output_s3_region
        self.parameters = parameters
        self.service_role_arn = service_role_arn
        self.targets = targets
        self.backend_region = backend_region

        # Get instance ids from a cloud formation stack target.
        stack_instance_ids = [
            self.get_instance_ids_by_stack_ids(target["Values"])
            for target in self.targets
            if target["Key"] == "tag:aws:cloudformation:stack-name"
        ]

        self.instance_ids += list(itertools.chain.from_iterable(stack_instance_ids))

        # Create invocations with a single run command plugin.
        self.invocations = []
        for instance_id in self.instance_ids:
            self.invocations.append(
                self.invocation_response(instance_id, "aws:runShellScript")
            )

    def get_instance_ids_by_stack_ids(self, stack_ids):
        instance_ids = []
        cloudformation_backend = cloudformation_backends[self.backend_region]
        for stack_id in stack_ids:
            stack_resources = cloudformation_backend.list_stack_resources(stack_id)
            instance_resources = [
                instance.id
                for instance in stack_resources
                if instance.type == "AWS::EC2::Instance"
            ]
            instance_ids.extend(instance_resources)

        return instance_ids

    def response_object(self):
        r = {
            "CommandId": self.command_id,
            "Comment": self.comment,
            "CompletedCount": self.completed_count,
            "DocumentName": self.document_name,
            "ErrorCount": self.error_count,
            "ExpiresAfter": self.expires_after,
            "InstanceIds": self.instance_ids,
            "MaxConcurrency": self.max_concurrency,
            "MaxErrors": self.max_errors,
            "NotificationConfig": self.notification_config,
            "OutputS3Region": self.output_s3_region,
            "OutputS3BucketName": self.output_s3_bucket_name,
            "OutputS3KeyPrefix": self.output_s3_key_prefix,
            "Parameters": self.parameters,
            "RequestedDateTime": self.requested_date_time_iso,
            "ServiceRole": self.service_role_arn,
            "Status": self.status,
            "StatusDetails": self.status_details,
            "TargetCount": self.target_count,
            "Targets": self.targets,
        }

        return r

    def invocation_response(self, instance_id, plugin_name):
        # Calculate elapsed time from requested time and now. Use a hardcoded
        # elapsed time since there is no easy way to convert a timedelta to
        # an ISO 8601 duration string.
        elapsed_time_iso = "PT5M"
        elapsed_time_delta = datetime.timedelta(minutes=5)
        end_time = self.requested_date_time + elapsed_time_delta

        r = {
            "CommandId": self.command_id,
            "InstanceId": instance_id,
            "Comment": self.comment,
            "DocumentName": self.document_name,
            "PluginName": plugin_name,
            "ResponseCode": 0,
            "ExecutionStartDateTime": self.requested_date_time_iso,
            "ExecutionElapsedTime": elapsed_time_iso,
            "ExecutionEndDateTime": end_time.isoformat(),
            "Status": "Success",
            "StatusDetails": "Success",
            "StandardOutputContent": "",
            "StandardOutputUrl": "",
            "StandardErrorContent": "",
        }

        return r

    def get_invocation(self, instance_id, plugin_name):
        invocation = next(
            (
                invocation
                for invocation in self.invocations
                if invocation["InstanceId"] == instance_id
            ),
            None,
        )

        if invocation is None:
            raise RESTError(
                "InvocationDoesNotExist",
                "An error occurred (InvocationDoesNotExist) when calling the GetCommandInvocation operation",
            )

        if plugin_name is not None and invocation["PluginName"] != plugin_name:
            raise RESTError(
                "InvocationDoesNotExist",
                "An error occurred (InvocationDoesNotExist) when calling the GetCommandInvocation operation",
            )

        return invocation


class SimpleSystemManagerBackend(BaseBackend):
    def __init__(self):
        # each value is a list of all of the versions for a parameter
        # to get the current value, grab the last item of the list
        self._parameters = defaultdict(list)

        self._resource_tags = defaultdict(lambda: defaultdict(dict))
        self._commands = []
        self._errors = []

        # figure out what region we're in
        for region, backend in ssm_backends.items():
            if backend == self:
                self._region = region

    def delete_parameter(self, name):
        try:
            del self._parameters[name]
        except KeyError:
            pass

    def delete_parameters(self, names):
        result = []
        for name in names:
            try:
                del self._parameters[name]
                result.append(name)
            except KeyError:
                pass
        return result

    def describe_parameters(self, filters, parameter_filters):
        if filters and parameter_filters:
            raise ValidationException(
                "You can use either Filters or ParameterFilters in a single request."
            )

        self._validate_parameter_filters(parameter_filters, by_path=False)

        result = []
        for param_name in self._parameters:
            ssm_parameter = self.get_parameter(param_name, False)
            if not self._match_filters(ssm_parameter, parameter_filters):
                continue

            if filters:
                for filter in filters:
                    if filter["Key"] == "Name":
                        k = ssm_parameter.name
                        for v in filter["Values"]:
                            if k.startswith(v):
                                result.append(ssm_parameter)
                                break
                    elif filter["Key"] == "Type":
                        k = ssm_parameter.type
                        for v in filter["Values"]:
                            if k == v:
                                result.append(ssm_parameter)
                                break
                    elif filter["Key"] == "KeyId":
                        k = ssm_parameter.keyid
                        if k:
                            for v in filter["Values"]:
                                if k == v:
                                    result.append(ssm_parameter)
                                    break
                continue

            result.append(ssm_parameter)

        return result

    def _validate_parameter_filters(self, parameter_filters, by_path):
        for index, filter_obj in enumerate(parameter_filters or []):
            key = filter_obj["Key"]
            values = filter_obj.get("Values", [])

            if key == "Path":
                option = filter_obj.get("Option", "OneLevel")
            else:
                option = filter_obj.get("Option", "Equals")

            if not re.match(r"^tag:.+|Name|Type|KeyId|Path|Label|Tier$", key):
                self._errors.append(
                    self._format_error(
                        key="parameterFilters.{index}.member.key".format(
                            index=(index + 1)
                        ),
                        value=key,
                        constraint="Member must satisfy regular expression pattern: tag:.+|Name|Type|KeyId|Path|Label|Tier",
                    )
                )

            if len(key) > 132:
                self._errors.append(
                    self._format_error(
                        key="parameterFilters.{index}.member.key".format(
                            index=(index + 1)
                        ),
                        value=key,
                        constraint="Member must have length less than or equal to 132",
                    )
                )

            if len(option) > 10:
                self._errors.append(
                    self._format_error(
                        key="parameterFilters.{index}.member.option".format(
                            index=(index + 1)
                        ),
                        value="over 10 chars",
                        constraint="Member must have length less than or equal to 10",
                    )
                )

            if len(values) > 50:
                self._errors.append(
                    self._format_error(
                        key="parameterFilters.{index}.member.values".format(
                            index=(index + 1)
                        ),
                        value=values,
                        constraint="Member must have length less than or equal to 50",
                    )
                )

            if any(len(value) > 1024 for value in values):
                self._errors.append(
                    self._format_error(
                        key="parameterFilters.{index}.member.values".format(
                            index=(index + 1)
                        ),
                        value=values,
                        constraint="[Member must have length less than or equal to 1024, Member must have length greater than or equal to 1]",
                    )
                )

        self._raise_errors()

        filter_keys = []
        for filter_obj in parameter_filters or []:
            key = filter_obj["Key"]
            values = filter_obj.get("Values")

            if key == "Path":
                option = filter_obj.get("Option", "OneLevel")
            else:
                option = filter_obj.get("Option", "Equals")

            if not by_path and key == "Label":
                raise InvalidFilterKey(
                    "The following filter key is not valid: Label. Valid filter keys include: [Path, Name, Type, KeyId, Tier]."
                )

            if not values:
                raise InvalidFilterValue(
                    "The following filter values are missing : null for filter key Name."
                )

            if key in filter_keys:
                raise InvalidFilterKey(
                    "The following filter is duplicated in the request: Name. A request can contain only one occurrence of a specific filter."
                )

            if key == "Path":
                if option not in ["Recursive", "OneLevel"]:
                    raise InvalidFilterOption(
                        "The following filter option is not valid: {option}. Valid options include: [Recursive, OneLevel].".format(
                            option=option
                        )
                    )
                if any(value.lower().startswith(("/aws", "/ssm")) for value in values):
                    raise ValidationException(
                        'Filters for common parameters can\'t be prefixed with "aws" or "ssm" (case-insensitive). '
                        "When using global parameters, please specify within a global namespace."
                    )
                for value in values:
                    if value.lower().startswith(("/aws", "/ssm")):
                        raise ValidationException(
                            'Filters for common parameters can\'t be prefixed with "aws" or "ssm" (case-insensitive). '
                            "When using global parameters, please specify within a global namespace."
                        )
                    if (
                        "//" in value
                        or not value.startswith("/")
                        or not re.match("^[a-zA-Z0-9_.-/]*$", value)
                    ):
                        raise ValidationException(
                            'The parameter doesn\'t meet the parameter name requirements. The parameter name must begin with a forward slash "/". '
                            'It can\'t be prefixed with "aws" or "ssm" (case-insensitive). '
                            "It must use only letters, numbers, or the following symbols: . (period), - (hyphen), _ (underscore). "
                            'Special characters are not allowed. All sub-paths, if specified, must use the forward slash symbol "/". '
                            "Valid example: /get/parameters2-/by1./path0_."
                        )

            if key == "Tier":
                for value in values:
                    if value not in ["Standard", "Advanced", "Intelligent-Tiering"]:
                        raise InvalidFilterOption(
                            "The following filter value is not valid: {value}. Valid values include: [Standard, Advanced, Intelligent-Tiering].".format(
                                value=value
                            )
                        )

            if key == "Type":
                for value in values:
                    if value not in ["String", "StringList", "SecureString"]:
                        raise InvalidFilterOption(
                            "The following filter value is not valid: {value}. Valid values include: [String, StringList, SecureString].".format(
                                value=value
                            )
                        )

            if key != "Path" and option not in ["Equals", "BeginsWith"]:
                raise InvalidFilterOption(
                    "The following filter option is not valid: {option}. Valid options include: [BeginsWith, Equals].".format(
                        option=option
                    )
                )

            filter_keys.append(key)

    def _format_error(self, key, value, constraint):
        return 'Value "{value}" at "{key}" failed to satisfy constraint: {constraint}'.format(
            constraint=constraint, key=key, value=value
        )

    def _raise_errors(self):
        if self._errors:
            count = len(self._errors)
            plural = "s" if len(self._errors) > 1 else ""
            errors = "; ".join(self._errors)
            self._errors = []  # reset collected errors

            raise ValidationException(
                "{count} validation error{plural} detected: {errors}".format(
                    count=count, plural=plural, errors=errors
                )
            )

    def get_all_parameters(self):
        result = []
        for k, _ in self._parameters.items():
            result.append(self._parameters[k])
        return result

    def get_parameters(self, names, with_decryption):
        result = []
        for name in names:
            if name in self._parameters:
                result.append(self.get_parameter(name, with_decryption))
        return result

    def get_parameters_by_path(self, path, with_decryption, recursive, filters=None):
        """Implement the get-parameters-by-path-API in the backend."""
        result = []
        # path could be with or without a trailing /. we handle this
        # difference here.
        path = path.rstrip("/") + "/"
        for param_name in self._parameters:
            if path != "/" and not param_name.startswith(path):
                continue
            if "/" in param_name[len(path) + 1 :] and not recursive:
                continue
            if not self._match_filters(
                self.get_parameter(param_name, with_decryption), filters
            ):
                continue
            result.append(self.get_parameter(param_name, with_decryption))

        return result

    def get_parameter_history(self, name, with_decryption):
        if name in self._parameters:
            return self._parameters[name]
        return None

    def _match_filters(self, parameter, filters=None):
        """Return True if the given parameter matches all the filters"""
        for filter_obj in filters or []:
            key = filter_obj["Key"]
            values = filter_obj.get("Values", [])

            if key == "Path":
                option = filter_obj.get("Option", "OneLevel")
            else:
                option = filter_obj.get("Option", "Equals")

            what = None
            if key == "KeyId":
                what = parameter.keyid
            elif key == "Name":
                what = "/" + parameter.name.lstrip("/")
                values = ["/" + value.lstrip("/") for value in values]
            elif key == "Path":
                what = "/" + parameter.name.lstrip("/")
                values = ["/" + value.strip("/") for value in values]
            elif key == "Type":
                what = parameter.type

            if what is None:
                return False
            elif option == "BeginsWith" and not any(
                what.startswith(value) for value in values
            ):
                return False
            elif option == "Equals" and not any(what == value for value in values):
                return False
            elif option == "OneLevel":
                if any(value == "/" and len(what.split("/")) == 2 for value in values):
                    continue
                elif any(
                    value != "/"
                    and what.startswith(value + "/")
                    and len(what.split("/")) - 1 == len(value.split("/"))
                    for value in values
                ):
                    continue
                else:
                    return False
            elif option == "Recursive":
                if any(value == "/" for value in values):
                    continue
                elif any(what.startswith(value + "/") for value in values):
                    continue
                else:
                    return False
        # True if no false match (or no filters at all)
        return True

    def get_parameter(self, name, with_decryption):
        if name in self._parameters:
            return self._parameters[name][-1]
        return None

    def put_parameter(
        self, name, description, value, type, allowed_pattern, keyid, overwrite
    ):
        previous_parameter_versions = self._parameters[name]
        if len(previous_parameter_versions) == 0:
            previous_parameter = None
            version = 1
        else:
            previous_parameter = previous_parameter_versions[-1]
            version = previous_parameter.version + 1

            if not overwrite:
                return

        last_modified_date = time.time()
        self._parameters[name].append(
            Parameter(
                name,
                value,
                type,
                description,
                allowed_pattern,
                keyid,
                last_modified_date,
                version,
            )
        )
        return version

    def add_tags_to_resource(self, resource_type, resource_id, tags):
        for key, value in tags.items():
            self._resource_tags[resource_type][resource_id][key] = value

    def remove_tags_from_resource(self, resource_type, resource_id, keys):
        tags = self._resource_tags[resource_type][resource_id]
        for key in keys:
            if key in tags:
                del tags[key]

    def list_tags_for_resource(self, resource_type, resource_id):
        return self._resource_tags[resource_type][resource_id]

    def send_command(self, **kwargs):
        command = Command(
            comment=kwargs.get("Comment", ""),
            document_name=kwargs.get("DocumentName"),
            timeout_seconds=kwargs.get("TimeoutSeconds", 3600),
            instance_ids=kwargs.get("InstanceIds", []),
            max_concurrency=kwargs.get("MaxConcurrency", "50"),
            max_errors=kwargs.get("MaxErrors", "0"),
            notification_config=kwargs.get(
                "NotificationConfig",
                {
                    "NotificationArn": "string",
                    "NotificationEvents": ["Success"],
                    "NotificationType": "Command",
                },
            ),
            output_s3_bucket_name=kwargs.get("OutputS3BucketName", ""),
            output_s3_key_prefix=kwargs.get("OutputS3KeyPrefix", ""),
            output_s3_region=kwargs.get("OutputS3Region", ""),
            parameters=kwargs.get("Parameters", {}),
            service_role_arn=kwargs.get("ServiceRoleArn", ""),
            targets=kwargs.get("Targets", []),
            backend_region=self._region,
        )

        self._commands.append(command)
        return {"Command": command.response_object()}

    def list_commands(self, **kwargs):
        """
        https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_ListCommands.html
        """
        commands = self._commands

        command_id = kwargs.get("CommandId", None)
        if command_id:
            commands = [self.get_command_by_id(command_id)]
        instance_id = kwargs.get("InstanceId", None)
        if instance_id:
            commands = self.get_commands_by_instance_id(instance_id)

        return {"Commands": [command.response_object() for command in commands]}

    def get_command_by_id(self, id):
        command = next(
            (command for command in self._commands if command.command_id == id), None
        )

        if command is None:
            raise RESTError("InvalidCommandId", "Invalid command id.")

        return command

    def get_commands_by_instance_id(self, instance_id):
        return [
            command for command in self._commands if instance_id in command.instance_ids
        ]

    def get_command_invocation(self, **kwargs):
        """
        https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_GetCommandInvocation.html
        """

        command_id = kwargs.get("CommandId")
        instance_id = kwargs.get("InstanceId")
        plugin_name = kwargs.get("PluginName", None)

        command = self.get_command_by_id(command_id)
        return command.get_invocation(instance_id, plugin_name)


ssm_backends = {}
for region, ec2_backend in ec2_backends.items():
    ssm_backends[region] = SimpleSystemManagerBackend()
