from __future__ import unicode_literals

import re
from boto3 import Session
from collections import defaultdict

from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.cloudformation import cloudformation_backends

import datetime
import time
import uuid
import itertools
import json
import yaml
import hashlib

from .utils import parameter_arn
from .exceptions import (
    ValidationException,
    InvalidFilterValue,
    InvalidFilterOption,
    InvalidFilterKey,
    ParameterVersionLabelLimitExceeded,
    ParameterVersionNotFound,
    ParameterNotFound,
    DocumentAlreadyExists,
    InvalidDocumentOperation,
    AccessDeniedException,
    InvalidDocument,
    InvalidDocumentContent,
    InvalidDocumentVersion,
    DuplicateDocumentVersionName,
    DuplicateDocumentContent,
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
        self.labels = []

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

    def response_object(self, decrypt=False, region=None):
        r = {
            "Name": self.name,
            "Type": self.type,
            "Value": self.decrypt(self.value) if decrypt else self.value,
            "Version": self.version,
            "LastModifiedDate": round(self.last_modified_date, 3),
        }

        if region:
            r["ARN"] = parameter_arn(region, self.name)

        return r

    def describe_response_object(self, decrypt=False, include_labels=False):
        r = self.response_object(decrypt)
        r["LastModifiedDate"] = round(self.last_modified_date, 3)
        r["LastModifiedUser"] = "N/A"

        if self.description:
            r["Description"] = self.description

        if self.keyid:
            r["KeyId"] = self.keyid

        if self.allowed_pattern:
            r["AllowedPattern"] = self.allowed_pattern

        if include_labels:
            r["Labels"] = self.labels

        return r


MAX_TIMEOUT_SECONDS = 3600


def generate_ssm_doc_param_list(parameters):
    if not parameters:
        return None
    param_list = []
    for param_name, param_info in parameters.items():
        final_dict = {}

        final_dict["Name"] = param_name
        final_dict["Type"] = param_info["type"]
        final_dict["Description"] = param_info["description"]

        if (
            param_info["type"] == "StringList"
            or param_info["type"] == "StringMap"
            or param_info["type"] == "MapList"
        ):
            final_dict["DefaultValue"] = json.dumps(param_info["default"])
        else:
            final_dict["DefaultValue"] = str(param_info["default"])

        param_list.append(final_dict)

    return param_list


class Document(BaseModel):
    def __init__(
        self,
        name,
        version_name,
        content,
        document_type,
        document_format,
        requires,
        attachments,
        target_type,
        tags,
        document_version="1",
    ):
        self.name = name
        self.version_name = version_name
        self.content = content
        self.document_type = document_type
        self.document_format = document_format
        self.requires = requires
        self.attachments = attachments
        self.target_type = target_type
        self.tags = tags

        self.status = "Active"
        self.document_version = document_version
        self.owner = ACCOUNT_ID
        self.created_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if document_format == "JSON":
            try:
                content_json = json.loads(content)
            except ValueError:
                # Python2
                raise InvalidDocumentContent(
                    "The content for the document is not valid."
                )
            except json.decoder.JSONDecodeError:
                raise InvalidDocumentContent(
                    "The content for the document is not valid."
                )
        elif document_format == "YAML":
            try:
                content_json = yaml.safe_load(content)
            except yaml.YAMLError:
                raise InvalidDocumentContent(
                    "The content for the document is not valid."
                )
        else:
            raise ValidationException("Invalid document format " + str(document_format))

        self.content_json = content_json

        try:
            self.schema_version = str(content_json["schemaVersion"])
            self.description = content_json.get("description")
            self.outputs = content_json.get("outputs")
            self.files = content_json.get("files")
            # TODO add platformType (requires mapping the ssm actions to OS's this isn't well documented)
            self.platform_types = ["Not Implemented (moto)"]
            self.parameter_list = generate_ssm_doc_param_list(
                content_json.get("parameters")
            )

            if (
                self.schema_version == "0.3"
                or self.schema_version == "2.0"
                or self.schema_version == "2.2"
            ):
                self.mainSteps = content_json["mainSteps"]
            elif self.schema_version == "1.2":
                self.runtimeConfig = content_json.get("runtimeConfig")

        except KeyError:
            raise InvalidDocumentContent("The content for the document is not valid.")


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


def _validate_document_format(document_format):
    aws_doc_formats = ["JSON", "YAML"]
    if document_format not in aws_doc_formats:
        raise ValidationException("Invalid document format " + str(document_format))


def _validate_document_info(content, name, document_type, document_format, strict=True):
    aws_ssm_name_regex = r"^[a-zA-Z0-9_\-.]{3,128}$"
    aws_name_reject_list = ["aws-", "amazon", "amzn"]
    aws_doc_types = [
        "Command",
        "Policy",
        "Automation",
        "Session",
        "Package",
        "ApplicationConfiguration",
        "ApplicationConfigurationSchema",
        "DeploymentStrategy",
        "ChangeCalendar",
    ]

    _validate_document_format(document_format)

    if not content:
        raise ValidationException("Content is required")

    if list(filter(name.startswith, aws_name_reject_list)):
        raise ValidationException("Invalid document name " + str(name))
    ssm_name_pattern = re.compile(aws_ssm_name_regex)
    if not ssm_name_pattern.match(name):
        raise ValidationException("Invalid document name " + str(name))

    if strict and document_type not in aws_doc_types:
        # Update document doesn't use document type
        raise ValidationException("Invalid document type " + str(document_type))


def _document_filter_equal_comparator(keyed_value, filter):
    for v in filter["Values"]:
        if keyed_value == v:
            return True
    return False


def _document_filter_list_includes_comparator(keyed_value_list, filter):
    for v in filter["Values"]:
        if v in keyed_value_list:
            return True
    return False


def _document_filter_match(filters, ssm_doc):
    for filter in filters:
        if filter["Key"] == "Name" and not _document_filter_equal_comparator(
            ssm_doc.name, filter
        ):
            return False

        elif filter["Key"] == "Owner":
            if len(filter["Values"]) != 1:
                raise ValidationException("Owner filter can only have one value.")
            if filter["Values"][0] == "Self":
                # Update to running account ID
                filter["Values"][0] = ACCOUNT_ID
            if not _document_filter_equal_comparator(ssm_doc.owner, filter):
                return False

        elif filter[
            "Key"
        ] == "PlatformTypes" and not _document_filter_list_includes_comparator(
            ssm_doc.platform_types, filter
        ):
            return False

        elif filter["Key"] == "DocumentType" and not _document_filter_equal_comparator(
            ssm_doc.document_type, filter
        ):
            return False

        elif filter["Key"] == "TargetType" and not _document_filter_equal_comparator(
            ssm_doc.target_type, filter
        ):
            return False

    return True


class SimpleSystemManagerBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(SimpleSystemManagerBackend, self).__init__()
        # each value is a list of all of the versions for a parameter
        # to get the current value, grab the last item of the list
        self._parameters = defaultdict(list)

        self._resource_tags = defaultdict(lambda: defaultdict(dict))
        self._commands = []
        self._errors = []
        self._documents = defaultdict(dict)

        self._region = region_name

    def reset(self):
        region_name = self._region
        self.__dict__ = {}
        self.__init__(region_name)

    def _generate_document_description(self, document):

        latest = self._documents[document.name]["latest_version"]
        default_version = self._documents[document.name]["default_version"]
        base = {
            "Hash": hashlib.sha256(document.content.encode("utf-8")).hexdigest(),
            "HashType": "Sha256",
            "Name": document.name,
            "Owner": document.owner,
            "CreatedDate": document.created_date,
            "Status": document.status,
            "DocumentVersion": document.document_version,
            "Description": document.description,
            "Parameters": document.parameter_list,
            "PlatformTypes": document.platform_types,
            "DocumentType": document.document_type,
            "SchemaVersion": document.schema_version,
            "LatestVersion": latest,
            "DefaultVersion": default_version,
            "DocumentFormat": document.document_format,
        }
        if document.version_name:
            base["VersionName"] = document.version_name
        if document.target_type:
            base["TargetType"] = document.target_type
        if document.tags:
            base["Tags"] = document.tags

        return base

    def _generate_document_information(self, ssm_document, document_format):
        base = {
            "Name": ssm_document.name,
            "DocumentVersion": ssm_document.document_version,
            "Status": ssm_document.status,
            "Content": ssm_document.content,
            "DocumentType": ssm_document.document_type,
            "DocumentFormat": document_format,
        }

        if document_format == "JSON":
            base["Content"] = json.dumps(ssm_document.content_json)
        elif document_format == "YAML":
            base["Content"] = yaml.dump(ssm_document.content_json)
        else:
            raise ValidationException("Invalid document format " + str(document_format))

        if ssm_document.version_name:
            base["VersionName"] = ssm_document.version_name
        if ssm_document.requires:
            base["Requires"] = ssm_document.requires
        if ssm_document.attachments:
            base["AttachmentsContent"] = ssm_document.attachments

        return base

    def _generate_document_list_information(self, ssm_document):
        base = {
            "Name": ssm_document.name,
            "Owner": ssm_document.owner,
            "DocumentVersion": ssm_document.document_version,
            "DocumentType": ssm_document.document_type,
            "SchemaVersion": ssm_document.schema_version,
            "DocumentFormat": ssm_document.document_format,
        }
        if ssm_document.version_name:
            base["VersionName"] = ssm_document.version_name
        if ssm_document.platform_types:
            base["PlatformTypes"] = ssm_document.platform_types
        if ssm_document.target_type:
            base["TargetType"] = ssm_document.target_type
        if ssm_document.tags:
            base["Tags"] = ssm_document.tags
        if ssm_document.requires:
            base["Requires"] = ssm_document.requires

        return base

    def create_document(
        self,
        content,
        requires,
        attachments,
        name,
        version_name,
        document_type,
        document_format,
        target_type,
        tags,
    ):
        ssm_document = Document(
            name=name,
            version_name=version_name,
            content=content,
            document_type=document_type,
            document_format=document_format,
            requires=requires,
            attachments=attachments,
            target_type=target_type,
            tags=tags,
        )

        _validate_document_info(
            content=content,
            name=name,
            document_type=document_type,
            document_format=document_format,
        )

        if self._documents.get(ssm_document.name):
            raise DocumentAlreadyExists("The specified document already exists.")

        self._documents[ssm_document.name] = {
            "documents": {ssm_document.document_version: ssm_document},
            "default_version": ssm_document.document_version,
            "latest_version": ssm_document.document_version,
        }

        return self._generate_document_description(ssm_document)

    def delete_document(self, name, document_version, version_name, force):
        documents = self._documents.get(name, {}).get("documents", {})
        keys_to_delete = set()

        if documents:
            default_version = self._documents[name]["default_version"]

            if (
                documents[default_version].document_type
                == "ApplicationConfigurationSchema"
                and not force
            ):
                raise InvalidDocumentOperation(
                    "You attempted to delete a document while it is still shared. "
                    "You must stop sharing the document before you can delete it."
                )

            if document_version and document_version == default_version:
                raise InvalidDocumentOperation(
                    "Default version of the document can't be deleted."
                )

            if document_version or version_name:
                # We delete only a specific version
                delete_doc = self._find_document(name, document_version, version_name)

                # we can't delete only the default version
                if (
                    delete_doc
                    and delete_doc.document_version == default_version
                    and len(documents) != 1
                ):
                    raise InvalidDocumentOperation(
                        "Default version of the document can't be deleted."
                    )

                if delete_doc:
                    keys_to_delete.add(delete_doc.document_version)
                else:
                    raise InvalidDocument("The specified document does not exist.")
            else:
                # We are deleting all versions
                keys_to_delete = set(documents.keys())

            for key in keys_to_delete:
                del self._documents[name]["documents"][key]

            if len(self._documents[name]["documents"].keys()) == 0:
                del self._documents[name]
            else:
                old_latest = self._documents[name]["latest_version"]
                if old_latest not in self._documents[name]["documents"].keys():
                    leftover_keys = self._documents[name]["documents"].keys()
                    int_keys = []
                    for key in leftover_keys:
                        int_keys.append(int(key))
                    self._documents[name]["latest_version"] = str(sorted(int_keys)[-1])
        else:
            raise InvalidDocument("The specified document does not exist.")

    def _find_document(
        self, name, document_version=None, version_name=None, strict=True
    ):
        if not self._documents.get(name):
            raise InvalidDocument("The specified document does not exist.")

        documents = self._documents[name]["documents"]
        ssm_document = None

        if not version_name and not document_version:
            # Retrieve default version
            default_version = self._documents[name]["default_version"]
            ssm_document = documents.get(default_version)

        elif version_name and document_version:
            for doc_version, document in documents.items():
                if (
                    doc_version == document_version
                    and document.version_name == version_name
                ):
                    ssm_document = document
                    break

        else:
            for doc_version, document in documents.items():
                if document_version and doc_version == document_version:
                    ssm_document = document
                    break
                if version_name and document.version_name == version_name:
                    ssm_document = document
                    break

        if strict and not ssm_document:
            raise InvalidDocument("The specified document does not exist.")

        return ssm_document

    def get_document(self, name, document_version, version_name, document_format):

        ssm_document = self._find_document(name, document_version, version_name)
        if not document_format:
            document_format = ssm_document.document_format
        else:
            _validate_document_format(document_format=document_format)

        return self._generate_document_information(ssm_document, document_format)

    def update_document_default_version(self, name, document_version):

        ssm_document = self._find_document(name, document_version=document_version)
        self._documents[name]["default_version"] = document_version
        base = {
            "Name": ssm_document.name,
            "DefaultVersion": document_version,
        }

        if ssm_document.version_name:
            base["DefaultVersionName"] = ssm_document.version_name

        return base

    def update_document(
        self,
        content,
        attachments,
        name,
        version_name,
        document_version,
        document_format,
        target_type,
    ):
        _validate_document_info(
            content=content,
            name=name,
            document_type=None,
            document_format=document_format,
            strict=False,
        )

        if not self._documents.get(name):
            raise InvalidDocument("The specified document does not exist.")
        if (
            self._documents[name]["latest_version"] != document_version
            and document_version != "$LATEST"
        ):
            raise InvalidDocumentVersion(
                "The document version is not valid or does not exist."
            )
        if version_name and self._find_document(
            name, version_name=version_name, strict=False
        ):
            raise DuplicateDocumentVersionName(
                "The specified version name is a duplicate."
            )

        old_ssm_document = self._find_document(name)

        new_ssm_document = Document(
            name=name,
            version_name=version_name,
            content=content,
            document_type=old_ssm_document.document_type,
            document_format=document_format,
            requires=old_ssm_document.requires,
            attachments=attachments,
            target_type=target_type,
            tags=old_ssm_document.tags,
            document_version=str(int(self._documents[name]["latest_version"]) + 1),
        )

        for doc_version, document in self._documents[name]["documents"].items():
            if document.content == new_ssm_document.content:
                raise DuplicateDocumentContent(
                    "The content of the association document matches another document. "
                    "Change the content of the document and try again."
                )

        self._documents[name]["latest_version"] = str(
            int(self._documents[name]["latest_version"]) + 1
        )
        self._documents[name]["documents"][
            new_ssm_document.document_version
        ] = new_ssm_document

        return self._generate_document_description(new_ssm_document)

    def describe_document(self, name, document_version, version_name):
        ssm_document = self._find_document(name, document_version, version_name)
        return self._generate_document_description(ssm_document)

    def list_documents(
        self, document_filter_list, filters, max_results=10, next_token="0"
    ):
        if document_filter_list:
            raise ValidationException(
                "DocumentFilterList is deprecated. Instead use Filters."
            )

        next_token = int(next_token)
        results = []
        dummy_token_tracker = 0
        # Sort to maintain next token adjacency
        for document_name, document_bundle in sorted(self._documents.items()):
            if len(results) == max_results:
                # There's still more to go so we need a next token
                return results, str(next_token + len(results))

            if dummy_token_tracker < next_token:
                dummy_token_tracker = dummy_token_tracker + 1
                continue

            default_version = document_bundle["default_version"]
            ssm_doc = self._documents[document_name]["documents"][default_version]
            if filters and not _document_filter_match(filters, ssm_doc):
                # If we have filters enabled, and we don't match them,
                continue
            else:
                results.append(self._generate_document_list_information(ssm_doc))

        # If we've fallen out of the loop, theres no more documents. No next token.
        return results, ""

    def delete_parameter(self, name):
        return self._parameters.pop(name, None)

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

            if by_path and key in ["Name", "Path", "Tier"]:
                raise InvalidFilterKey(
                    "The following filter key is not valid: {key}. Valid filter keys include: [Type, KeyId].".format(
                        key=key
                    )
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

            allowed_options = ["Equals", "BeginsWith"]
            if key == "Name":
                allowed_options += ["Contains"]
            if key != "Path" and option not in allowed_options:
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

        if len(names) > 10:
            raise ValidationException(
                "1 validation error detected: "
                "Value '[{}]' at 'names' failed to satisfy constraint: "
                "Member must have length less than or equal to 10.".format(
                    ", ".join(names)
                )
            )

        for name in names:
            if name in self._parameters:
                result.append(self.get_parameter(name, with_decryption))
        return result

    def get_parameters_by_path(
        self,
        path,
        with_decryption,
        recursive,
        filters=None,
        next_token=None,
        max_results=10,
    ):
        """Implement the get-parameters-by-path-API in the backend."""

        self._validate_parameter_filters(filters, by_path=True)

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

        return self._get_values_nexttoken(result, max_results, next_token)

    def _get_values_nexttoken(self, values_list, max_results, next_token=None):
        if next_token is None:
            next_token = 0
        next_token = int(next_token)
        max_results = int(max_results)
        values = values_list[next_token : next_token + max_results]
        if len(values) == max_results:
            next_token = str(next_token + max_results)
        else:
            next_token = None
        return values, next_token

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
                if option != "Contains":
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
            elif option == "Contains" and not any(value in what for value in values):
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
        name_parts = name.split(":")
        name_prefix = name_parts[0]

        if len(name_parts) > 2:
            return None

        if name_prefix in self._parameters:
            if len(name_parts) == 1:
                return self._parameters[name][-1]

            if len(name_parts) == 2:
                version_or_label = name_parts[1]
                parameters = self._parameters[name_prefix]

                if version_or_label.isdigit():
                    result = list(
                        filter(lambda x: str(x.version) == version_or_label, parameters)
                    )
                    if len(result) > 0:
                        return result[-1]

                result = list(
                    filter(lambda x: version_or_label in x.labels, parameters)
                )
                if len(result) > 0:
                    return result[-1]

        return None

    def label_parameter_version(self, name, version, labels):
        previous_parameter_versions = self._parameters[name]
        if not previous_parameter_versions:
            raise ParameterNotFound("Parameter %s not found." % name)
        found_parameter = None
        labels_needing_removal = []
        if not version:
            version = 1
            for parameter in previous_parameter_versions:
                if parameter.version >= version:
                    version = parameter.version
        for parameter in previous_parameter_versions:
            if parameter.version == version:
                found_parameter = parameter
            else:
                for label in labels:
                    if label in parameter.labels:
                        labels_needing_removal.append(label)
        if not found_parameter:
            raise ParameterVersionNotFound(
                "Systems Manager could not find version %s of %s. "
                "Verify the version and try again." % (version, name)
            )
        labels_to_append = []
        invalid_labels = []
        for label in labels:
            if (
                label.startswith("aws")
                or label.startswith("ssm")
                or label[:1].isdigit()
                or not re.match(r"^[a-zA-z0-9_\.\-]*$", label)
            ):
                invalid_labels.append(label)
                continue
            if len(label) > 100:
                raise ValidationException(
                    "1 validation error detected: "
                    "Value '[%s]' at 'labels' failed to satisfy constraint: "
                    "Member must satisfy constraint: "
                    "[Member must have length less than or equal to 100, Member must have length greater than or equal to 1]"
                    % label
                )
                continue
            if label not in found_parameter.labels:
                labels_to_append.append(label)
        if (len(found_parameter.labels) + len(labels_to_append)) > 10:
            raise ParameterVersionLabelLimitExceeded(
                "An error occurred (ParameterVersionLabelLimitExceeded) when calling the LabelParameterVersion operation: "
                "A parameter version can have maximum 10 labels."
                "Move one or more labels to another version and try again."
            )
        found_parameter.labels = found_parameter.labels + labels_to_append
        for parameter in previous_parameter_versions:
            if parameter.version != version:
                for label in parameter.labels[:]:
                    if label in labels_needing_removal:
                        parameter.labels.remove(label)
        return [invalid_labels, version]

    def put_parameter(
        self, name, description, value, type, allowed_pattern, keyid, overwrite
    ):
        if name.lower().lstrip("/").startswith("aws") or name.lower().lstrip(
            "/"
        ).startswith("ssm"):
            is_path = name.count("/") > 1
            if name.lower().startswith("/aws") and is_path:
                raise AccessDeniedException(
                    "No access to reserved parameter name: {name}.".format(name=name)
                )
            if not is_path:
                invalid_prefix_error = 'Parameter name: can\'t be prefixed with "aws" or "ssm" (case-insensitive).'
            else:
                invalid_prefix_error = (
                    'Parameter name: can\'t be prefixed with "ssm" (case-insensitive). '
                    "If formed as a path, it can consist of sub-paths divided by slash symbol; each sub-path can be "
                    "formed as a mix of letters, numbers and the following 3 symbols .-_"
                )
            raise ValidationException(invalid_prefix_error)
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
for region in Session().get_available_regions("ssm"):
    ssm_backends[region] = SimpleSystemManagerBackend(region)
for region in Session().get_available_regions("ssm", partition_name="aws-us-gov"):
    ssm_backends[region] = SimpleSystemManagerBackend(region)
for region in Session().get_available_regions("ssm", partition_name="aws-cn"):
    ssm_backends[region] = SimpleSystemManagerBackend(region)
