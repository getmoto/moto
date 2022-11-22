import re
from dataclasses import dataclass
from typing import Dict

from collections import defaultdict

from moto.core import BaseBackend, BackendDict, BaseModel, CloudFormationModel
from moto.core.exceptions import RESTError
from moto.ec2 import ec2_backends
from moto.secretsmanager import secretsmanager_backends
from moto.secretsmanager.exceptions import SecretsManagerClientError
from moto.utilities.utils import load_resource

import datetime
import time
import json
import yaml
import hashlib
from moto.moto_api._internal import mock_random as random
from .utils import parameter_arn, convert_to_params
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
    ParameterMaxVersionLimitExceeded,
    DocumentPermissionLimit,
    InvalidPermissionType,
    InvalidResourceId,
    InvalidResourceType,
)


class ParameterDict(defaultdict):
    def __init__(self, account_id, region_name):
        # each value is a list of all of the versions for a parameter
        # to get the current value, grab the last item of the list
        super().__init__(list)
        self.parameters_loaded = False
        self.account_id = account_id
        self.region_name = region_name

    def _check_loading_status(self, key):
        if not self.parameters_loaded and key and str(key).startswith("/aws"):
            self._load_global_parameters()

    def _load_global_parameters(self):
        try:
            latest_amis_linux = load_resource(
                __name__, f"resources/ami-amazon-linux-latest/{self.region_name}.json"
            )
        except FileNotFoundError:
            latest_amis_linux = []
        for param in latest_amis_linux:
            name = param["Name"]
            super().__getitem__(name).append(
                Parameter(
                    account_id=self.account_id,
                    name=name,
                    value=param["Value"],
                    parameter_type=param["Type"],
                    description=None,
                    allowed_pattern=None,
                    keyid=None,
                    last_modified_date=param["LastModifiedDate"],
                    version=param["Version"],
                    data_type=param["DataType"],
                )
            )
        regions = load_resource(__name__, "resources/regions.json")
        services = load_resource(__name__, "resources/services.json")
        params = []
        params.extend(convert_to_params(regions))
        params.extend(convert_to_params(services))

        for param in params:
            last_modified_date = time.time()
            name = param["Name"]
            value = param["Value"]
            # Following were lost in translation/conversion - using sensible defaults
            parameter_type = "String"
            version = 1
            super().__getitem__(name).append(
                Parameter(
                    account_id=self.account_id,
                    name=name,
                    value=value,
                    parameter_type=parameter_type,
                    description=None,
                    allowed_pattern=None,
                    keyid=None,
                    last_modified_date=last_modified_date,
                    version=version,
                    data_type="text",
                )
            )
        self.parameters_loaded = True

    def _get_secretsmanager_parameter(self, secret_name):
        secrets_backend = secretsmanager_backends[self.account_id][self.region_name]
        secret = secrets_backend.describe_secret(secret_name)
        version_id_to_stage = secret["VersionIdsToStages"]
        # Sort version ID's so that AWSCURRENT is last
        sorted_version_ids = [
            k for k in version_id_to_stage if "AWSCURRENT" not in version_id_to_stage[k]
        ] + [k for k in version_id_to_stage if "AWSCURRENT" in version_id_to_stage[k]]
        values = [
            secrets_backend.get_secret_value(
                secret_name,
                version_id=version_id,
                version_stage=None,
            )
            for version_id in sorted_version_ids
        ]
        return [
            Parameter(
                account_id=self.account_id,
                name=secret["Name"],
                value=val.get("SecretString"),
                parameter_type="SecureString",
                description=secret.get("Description"),
                allowed_pattern=None,
                keyid=None,
                last_modified_date=secret["LastChangedDate"],
                version=0,
                data_type="text",
                labels=[val.get("VersionId")] + val.get("VersionStages", []),
                source_result=json.dumps(secret),
            )
            for val in values
        ]

    def __getitem__(self, item):
        if item.startswith("/aws/reference/secretsmanager/"):
            return self._get_secretsmanager_parameter("/".join(item.split("/")[4:]))
        self._check_loading_status(item)
        return super().__getitem__(item)

    def __contains__(self, k):
        if k and k.startswith("/aws/reference/secretsmanager/"):
            try:
                param = self._get_secretsmanager_parameter("/".join(k.split("/")[4:]))
                return param is not None
            except SecretsManagerClientError:
                raise ParameterNotFound(
                    f"An error occurred (ParameterNotFound) when referencing Secrets Manager: Secret {k} not found."
                )
        self._check_loading_status(k)
        return super().__contains__(k)

    def get_keys_beginning_with(self, path, recursive):
        self._check_loading_status(path)
        for param_name in self:
            if path != "/" and not param_name.startswith(path):
                continue
            if "/" in param_name[len(path) + 1 :] and not recursive:
                continue
            yield param_name


PARAMETER_VERSION_LIMIT = 100
PARAMETER_HISTORY_MAX_RESULTS = 50


class Parameter(CloudFormationModel):
    def __init__(
        self,
        account_id,
        name,
        value,
        parameter_type,
        description,
        allowed_pattern,
        keyid,
        last_modified_date,
        version,
        data_type,
        tags=None,
        labels=None,
        source_result=None,
    ):
        self.account_id = account_id
        self.name = name
        self.type = parameter_type
        self.description = description
        self.allowed_pattern = allowed_pattern
        self.keyid = keyid
        self.last_modified_date = last_modified_date
        self.version = version
        self.data_type = data_type
        self.tags = tags or []
        self.labels = labels or []
        self.source_result = source_result

        if self.type == "SecureString":
            if not self.keyid:
                self.keyid = "alias/aws/ssm"

            self.value = self.encrypt(value)
        else:
            self.value = value

    def encrypt(self, value):
        return f"kms:{self.keyid}:" + value

    def decrypt(self, value):
        if self.type != "SecureString":
            return value

        prefix = f"kms:{self.keyid or 'default'}:"
        if value.startswith(prefix):
            return value[len(prefix) :]

    def response_object(self, decrypt=False, region=None):
        r = {
            "Name": self.name,
            "Type": self.type,
            "Value": self.decrypt(self.value) if decrypt else self.value,
            "Version": self.version,
            "LastModifiedDate": round(self.last_modified_date, 3),
            "DataType": self.data_type,
        }
        if self.source_result:
            r["SourceResult"] = self.source_result

        if region:
            r["ARN"] = parameter_arn(self.account_id, region, self.name)

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

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ssm-parameter.html
        return "AWS::SSM::Parameter"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        ssm_backend = ssm_backends[account_id][region_name]
        properties = cloudformation_json["Properties"]

        parameter_args = {
            "name": properties.get("Name"),
            "description": properties.get("Description", None),
            "value": properties.get("Value", None),
            "parameter_type": properties.get("Type", None),
            "allowed_pattern": properties.get("AllowedPattern", None),
            "keyid": properties.get("KeyId", None),
            "overwrite": properties.get("Overwrite", False),
            "tags": properties.get("Tags", None),
            "data_type": properties.get("DataType", "text"),
        }
        ssm_backend.put_parameter(**parameter_args)
        parameter = ssm_backend.get_parameter(properties.get("Name"))
        return parameter

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, account_id, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        ssm_backend = ssm_backends[account_id][region_name]
        properties = cloudformation_json["Properties"]

        ssm_backend.delete_parameter(properties.get("Name"))


MAX_TIMEOUT_SECONDS = 3600


def generate_ssm_doc_param_list(parameters):
    if not parameters:
        return None
    param_list = []
    for param_name, param_info in parameters.items():
        final_dict = {
            "Name": param_name,
        }

        description = param_info.get("description")
        if description:
            final_dict["Description"] = description

        param_type = param_info["type"]
        final_dict["Type"] = param_type

        default_value = param_info.get("default")
        if default_value is not None:
            if param_type in {"StringList", "StringMap", "MapList"}:
                final_dict["DefaultValue"] = json.dumps(default_value)
            else:
                final_dict["DefaultValue"] = str(default_value)

        param_list.append(final_dict)

    return param_list


@dataclass(frozen=True)
class AccountPermission:
    account_id: str
    version: str
    created_at: datetime


class Documents(BaseModel):
    def __init__(self, ssm_document):
        version = ssm_document.document_version
        self.versions = {version: ssm_document}
        self.default_version = version
        self.latest_version = version
        self.permissions = {}  # {AccountID: AccountPermission }

    def get_default_version(self):
        return self.versions.get(self.default_version)

    def get_latest_version(self):
        return self.versions.get(self.latest_version)

    def find_by_version_name(self, version_name):
        return next(
            (
                document
                for document in self.versions.values()
                if document.version_name == version_name
            ),
            None,
        )

    def find_by_version(self, version):
        return self.versions.get(version)

    def find_by_version_and_version_name(self, version, version_name):
        return next(
            (
                document
                for doc_version, document in self.versions.items()
                if doc_version == version and document.version_name == version_name
            ),
            None,
        )

    def find(self, document_version=None, version_name=None, strict=True):

        if document_version == "$LATEST":
            ssm_document = self.get_latest_version()
        elif version_name and document_version:
            ssm_document = self.find_by_version_and_version_name(
                document_version, version_name
            )
        elif version_name:
            ssm_document = self.find_by_version_name(version_name)
        elif document_version:
            ssm_document = self.find_by_version(document_version)
        else:
            ssm_document = self.get_default_version()

        if strict and not ssm_document:
            raise InvalidDocument("The specified document does not exist.")

        return ssm_document

    def exists(self, document_version=None, version_name=None):
        return self.find(document_version, version_name, strict=False) is not None

    def add_new_version(self, new_document_version):
        version = new_document_version.document_version
        self.latest_version = version
        self.versions[version] = new_document_version

    def update_default_version(self, version):
        ssm_document = self.find_by_version(version)
        if not ssm_document:
            raise InvalidDocument("The specified document does not exist.")
        self.default_version = version
        return ssm_document

    def delete(self, *versions):
        for version in versions:
            if version in self.versions:
                del self.versions[version]

        if self.versions and self.latest_version not in self.versions:
            ordered_versions = sorted(self.versions.keys())
            new_latest_version = ordered_versions[-1]
            self.latest_version = new_latest_version

    def describe(self, document_version=None, version_name=None, tags=None):
        document = self.find(document_version, version_name)
        base = {
            "Hash": document.hash,
            "HashType": "Sha256",
            "Name": document.name,
            "Owner": document.owner,
            "CreatedDate": document.created_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Status": document.status,
            "DocumentVersion": document.document_version,
            "Description": document.description,
            "Parameters": document.parameter_list,
            "PlatformTypes": document.platform_types,
            "DocumentType": document.document_type,
            "SchemaVersion": document.schema_version,
            "LatestVersion": self.latest_version,
            "DefaultVersion": self.default_version,
            "DocumentFormat": document.document_format,
        }
        if document.version_name:
            base["VersionName"] = document.version_name
        if document.target_type:
            base["TargetType"] = document.target_type
        if tags:
            base["Tags"] = tags

        return base

    def modify_permissions(self, accounts_to_add, accounts_to_remove, version):
        version = version or "$DEFAULT"
        if accounts_to_add:
            if "all" in accounts_to_add:
                self.permissions.clear()
            else:
                self.permissions.pop("all", None)

            new_permissions = {
                account_id: AccountPermission(
                    account_id, version, datetime.datetime.now()
                )
                for account_id in accounts_to_add
            }
            self.permissions.update(**new_permissions)

        if accounts_to_remove:
            if "all" in accounts_to_remove:
                self.permissions.clear()
            else:
                for account_id in accounts_to_remove:
                    self.permissions.pop(account_id, None)

    def describe_permissions(self):

        permissions_ordered_by_date = sorted(
            self.permissions.values(), key=lambda p: p.created_at
        )

        return {
            "AccountIds": [p.account_id for p in permissions_ordered_by_date],
            "AccountSharingInfoList": [
                {"AccountId": p.account_id, "SharedDocumentVersion": p.version}
                for p in permissions_ordered_by_date
            ],
        }

    def is_shared(self):
        return len(self.permissions) > 0


class Document(BaseModel):
    def __init__(
        self,
        account_id,
        name,
        version_name,
        content,
        document_type,
        document_format,
        requires,
        attachments,
        target_type,
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

        self.status = "Active"
        self.document_version = document_version
        self.owner = account_id
        self.created_date = datetime.datetime.utcnow()

        if document_format == "JSON":
            try:
                content_json = json.loads(content)
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

            if self.schema_version in {"0.3", "2.0", "2.2"}:
                self.mainSteps = content_json.get("mainSteps")
            elif self.schema_version == "1.2":
                self.runtimeConfig = content_json.get("runtimeConfig")

        except KeyError:
            raise InvalidDocumentContent("The content for the document is not valid.")

    @property
    def hash(self):
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def list_describe(self, tags=None):
        base = {
            "Name": self.name,
            "Owner": self.owner,
            "DocumentVersion": self.document_version,
            "DocumentType": self.document_type,
            "SchemaVersion": self.schema_version,
            "DocumentFormat": self.document_format,
        }
        if self.version_name:
            base["VersionName"] = self.version_name
        if self.platform_types:
            base["PlatformTypes"] = self.platform_types
        if self.target_type:
            base["TargetType"] = self.target_type
        if self.requires:
            base["Requires"] = self.requires
        if tags:
            base["Tags"] = tags

        return base


class Command(BaseModel):
    def __init__(
        self,
        account_id,
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

        self.command_id = str(random.uuid4())
        self.status = "Success"
        self.status_details = "Details placeholder"
        self.account_id = account_id

        self.requested_date_time = datetime.datetime.now()
        self.requested_date_time_iso = self.requested_date_time.isoformat()
        expires_after = self.requested_date_time + datetime.timedelta(
            0, timeout_seconds
        )
        self.expires_after = expires_after.isoformat()

        self.comment = comment
        self.document_name = document_name
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

        self.instance_ids = instance_ids
        self.instance_ids += self._get_instance_ids_from_targets()
        # Ensure no duplicate instance_ids
        self.instance_ids = list(set(self.instance_ids))

        # NOTE: All of these counts are 0 in the ssm:SendCommand response
        # received from a real AWS backend.  The counts are correct when
        # making subsequent calls to ssm:DescribeCommand or ssm:ListCommands.
        # Not likely to cause any problems, but perhaps an area for future
        # improvement.
        self.error_count = 0
        self.completed_count = len(instance_ids)
        self.target_count = len(instance_ids)

        # Create invocations with a single run command plugin.
        self.invocations = []
        for instance_id in self.instance_ids:
            self.invocations.append(
                self.invocation_response(instance_id, "aws:runShellScript")
            )

    def _get_instance_ids_from_targets(self):
        target_instance_ids = []
        ec2_backend = ec2_backends[self.account_id][self.backend_region]
        ec2_filters = {target["Key"]: target["Values"] for target in self.targets}
        reservations = ec2_backend.all_reservations(filters=ec2_filters)
        for reservation in reservations:
            for instance in reservation.instances:
                target_instance_ids.append(instance.id)
        return target_instance_ids

    def response_object(self):
        r = {
            "CommandId": self.command_id,
            "Comment": self.comment,
            "CompletedCount": self.completed_count,
            "DeliveryTimedOutCount": 0,
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


def _document_filter_equal_comparator(keyed_value, _filter):
    for v in _filter["Values"]:
        if keyed_value == v:
            return True
    return False


def _document_filter_list_includes_comparator(keyed_value_list, _filter):
    for v in _filter["Values"]:
        if v in keyed_value_list:
            return True
    return False


def _document_filter_match(account_id, filters, ssm_doc):
    for _filter in filters:
        if _filter["Key"] == "Name" and not _document_filter_equal_comparator(
            ssm_doc.name, _filter
        ):
            return False

        elif _filter["Key"] == "Owner":
            if len(_filter["Values"]) != 1:
                raise ValidationException("Owner filter can only have one value.")
            if _filter["Values"][0] == "Self":
                # Update to running account ID
                _filter["Values"][0] = account_id
            if not _document_filter_equal_comparator(ssm_doc.owner, _filter):
                return False

        elif _filter[
            "Key"
        ] == "PlatformTypes" and not _document_filter_list_includes_comparator(
            ssm_doc.platform_types, _filter
        ):
            return False

        elif _filter["Key"] == "DocumentType" and not _document_filter_equal_comparator(
            ssm_doc.document_type, _filter
        ):
            return False

        elif _filter["Key"] == "TargetType" and not _document_filter_equal_comparator(
            ssm_doc.target_type, _filter
        ):
            return False

    return True


def _valid_parameter_data_type(data_type):
    """
    Parameter DataType field allows only `text` and `aws:ec2:image` values

    """
    return data_type in ("text", "aws:ec2:image")


class FakeMaintenanceWindow:
    def __init__(
        self,
        name,
        description,
        enabled,
        duration,
        cutoff,
        schedule,
        schedule_timezone,
        schedule_offset,
        start_date,
        end_date,
    ):
        self.id = FakeMaintenanceWindow.generate_id()
        self.name = name
        self.description = description
        self.enabled = enabled
        self.duration = duration
        self.cutoff = cutoff
        self.schedule = schedule
        self.schedule_timezone = schedule_timezone
        self.schedule_offset = schedule_offset
        self.start_date = start_date
        self.end_date = end_date

    def to_json(self):
        return {
            "WindowId": self.id,
            "Name": self.name,
            "Description": self.description,
            "Enabled": self.enabled,
            "Duration": self.duration,
            "Cutoff": self.cutoff,
            "Schedule": self.schedule,
            "ScheduleTimezone": self.schedule_timezone,
            "ScheduleOffset": self.schedule_offset,
            "StartDate": self.start_date,
            "EndDate": self.end_date,
        }

    @staticmethod
    def generate_id():
        chars = list(range(10)) + ["a", "b", "c", "d", "e", "f"]
        return "mw-" + "".join(str(random.choice(chars)) for _ in range(17))


class SimpleSystemManagerBackend(BaseBackend):
    """
    Moto supports the following default parameters out of the box:

     - /aws/service/global-infrastructure/regions
     - /aws/service/global-infrastructure/services

    Note that these are hardcoded, so they may be out of date for new services/regions.

    Integration with SecretsManager is also supported.
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._parameters = ParameterDict(account_id, region_name)

        self._resource_tags = defaultdict(lambda: defaultdict(dict))
        self._commands = []
        self._errors = []
        self._documents: Dict[str, Documents] = {}

        self.windows: Dict[str, FakeMaintenanceWindow] = dict()

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint services."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "ssm"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "ssmmessages"
        )

    def _generate_document_information(self, ssm_document, document_format):
        content = self._get_document_content(document_format, ssm_document)
        base = {
            "Name": ssm_document.name,
            "DocumentVersion": ssm_document.document_version,
            "Status": ssm_document.status,
            "Content": content,
            "DocumentType": ssm_document.document_type,
            "DocumentFormat": document_format,
        }

        if ssm_document.version_name:
            base["VersionName"] = ssm_document.version_name
        if ssm_document.requires:
            base["Requires"] = ssm_document.requires
        if ssm_document.attachments:
            base["AttachmentsContent"] = ssm_document.attachments

        return base

    @staticmethod
    def _get_document_content(document_format, ssm_document):
        if document_format == ssm_document.document_format:
            content = ssm_document.content
        elif document_format == "JSON":
            content = json.dumps(ssm_document.content_json)
        elif document_format == "YAML":
            content = yaml.dump(ssm_document.content_json)
        else:
            raise ValidationException("Invalid document format " + str(document_format))
        return content

    def _get_documents(self, name):
        documents = self._documents.get(name)
        if not documents:
            raise InvalidDocument("The specified document does not exist.")
        return documents

    def _get_documents_tags(self, name):
        docs_tags = self._resource_tags.get("Document")
        if docs_tags:
            document_tags = docs_tags.get(name, {})
            return [
                {"Key": tag, "Value": value} for tag, value in document_tags.items()
            ]
        return []

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
            account_id=self.account_id,
            name=name,
            version_name=version_name,
            content=content,
            document_type=document_type,
            document_format=document_format,
            requires=requires,
            attachments=attachments,
            target_type=target_type,
        )

        _validate_document_info(
            content=content,
            name=name,
            document_type=document_type,
            document_format=document_format,
        )

        if self._documents.get(ssm_document.name):
            raise DocumentAlreadyExists("The specified document already exists.")

        documents = Documents(ssm_document)
        self._documents[ssm_document.name] = documents

        if tags:
            document_tags = {t["Key"]: t["Value"] for t in tags}
            self.add_tags_to_resource("Document", name, document_tags)

        return documents.describe(tags=tags)

    def delete_document(self, name, document_version, version_name, force):
        documents = self._get_documents(name)

        if documents.is_shared():
            raise InvalidDocumentOperation("Must unshare document first before delete")

        keys_to_delete = set()

        if documents:
            default_doc = documents.get_default_version()
            if (
                default_doc.document_type == "ApplicationConfigurationSchema"
                and not force
            ):
                raise InvalidDocumentOperation(
                    "You attempted to delete a document while it is still shared. "
                    "You must stop sharing the document before you can delete it."
                )

            if document_version and document_version == default_doc.document_version:
                raise InvalidDocumentOperation(
                    "Default version of the document can't be deleted."
                )

            if document_version or version_name:
                # We delete only a specific version
                delete_doc = documents.find(document_version, version_name)

                # we can't delete only the default version
                if (
                    delete_doc
                    and delete_doc.document_version == default_doc.document_version
                    and len(documents.versions) != 1
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
                keys_to_delete = set(documents.versions.keys())

            documents.delete(*keys_to_delete)

            if len(documents.versions) == 0:
                self._resource_tags.get("Document", {}).pop(name, None)
                del self._documents[name]

    def get_document(self, name, document_version, version_name, document_format):

        documents = self._get_documents(name)
        ssm_document = documents.find(document_version, version_name)

        if not document_format:
            document_format = ssm_document.document_format
        else:
            _validate_document_format(document_format=document_format)

        return self._generate_document_information(ssm_document, document_format)

    def update_document_default_version(self, name, document_version):
        documents = self._get_documents(name)
        ssm_document = documents.update_default_version(document_version)

        result = {
            "Name": ssm_document.name,
            "DefaultVersion": document_version,
        }

        if ssm_document.version_name:
            result["DefaultVersionName"] = ssm_document.version_name

        return result

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

        documents = self._documents.get(name)
        if not documents:
            raise InvalidDocument("The specified document does not exist.")

        if (
            documents.latest_version != document_version
            and document_version != "$LATEST"
        ):
            raise InvalidDocumentVersion(
                "The document version is not valid or does not exist."
            )

        if version_name:
            if documents.exists(version_name=version_name):
                raise DuplicateDocumentVersionName(
                    "The specified version name is a duplicate."
                )

        old_ssm_document = documents.get_default_version()

        new_version = str(int(documents.latest_version) + 1)
        new_ssm_document = Document(
            account_id=self.account_id,
            name=name,
            version_name=version_name,
            content=content,
            document_type=old_ssm_document.document_type,
            document_format=document_format,
            requires=old_ssm_document.requires,
            attachments=attachments,
            target_type=target_type,
            document_version=new_version,
        )

        for document in documents.versions.values():
            if document.content == new_ssm_document.content:
                if not target_type or target_type == document.target_type:
                    raise DuplicateDocumentContent(
                        "The content of the association document matches another document. "
                        "Change the content of the document and try again."
                    )

        documents.add_new_version(new_ssm_document)
        tags = self._get_documents_tags(name)
        return documents.describe(document_version=new_version, tags=tags)

    def describe_document(self, name, document_version, version_name):
        documents = self._get_documents(name)
        tags = self._get_documents_tags(name)
        return documents.describe(document_version, version_name, tags=tags)

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
        for _, documents in sorted(self._documents.items()):
            if len(results) == max_results:
                # There's still more to go so we need a next token
                return results, str(next_token + len(results))

            if dummy_token_tracker < next_token:
                dummy_token_tracker += 1
                continue

            ssm_doc = documents.get_default_version()
            if filters and not _document_filter_match(
                self.account_id, filters, ssm_doc
            ):
                # If we have filters enabled, and we don't match them,
                continue
            else:
                tags = self._get_documents_tags(ssm_doc.name)
                doc_describe = ssm_doc.list_describe(tags=tags)
                results.append(doc_describe)

        # If we've fallen out of the loop, theres no more documents. No next token.
        return results, ""

    def describe_document_permission(self, name):
        """
        Parameters max_results, permission_type, and next_token not yet implemented
        """
        document = self._get_documents(name)
        return document.describe_permissions()

    def modify_document_permission(
        self,
        name,
        account_ids_to_add,
        account_ids_to_remove,
        shared_document_version,
        permission_type,
    ):

        account_id_regex = re.compile(r"^(all|[0-9]{12})$", re.IGNORECASE)
        version_regex = re.compile(r"^([$]LATEST|[$]DEFAULT|[$]ALL)$")

        account_ids_to_add = account_ids_to_add or []
        account_ids_to_remove = account_ids_to_remove or []

        if shared_document_version and not version_regex.match(shared_document_version):
            raise ValidationException(
                f"Value '{shared_document_version}' at 'sharedDocumentVersion' failed to satisfy constraint: "
                f"Member must satisfy regular expression pattern: ([$]LATEST|[$]DEFAULT|[$]ALL)."
            )

        for account_id in account_ids_to_add:
            if not account_id_regex.match(account_id):
                raise ValidationException(
                    f"Value '[{account_id}]' at 'accountIdsToAdd' failed to satisfy constraint: "
                    "Member must satisfy regular expression pattern: (all|[0-9]{12}])."
                )

        for account_id in account_ids_to_remove:
            if not account_id_regex.match(account_id):
                raise ValidationException(
                    f"Value '[{account_id}]' at 'accountIdsToRemove' failed to satisfy constraint: "
                    "Member must satisfy regular expression pattern: (?i)all|[0-9]{12}]."
                )

        if "all" in account_ids_to_add and len(account_ids_to_add) > 1:
            raise DocumentPermissionLimit(
                "Accounts can either be all or a group of AWS accounts"
            )

        if "all" in account_ids_to_remove and len(account_ids_to_remove) > 1:
            raise DocumentPermissionLimit(
                "Accounts can either be all or a group of AWS accounts"
            )

        if permission_type != "Share":
            raise InvalidPermissionType(
                f"Value '{permission_type}' at 'permissionType' failed to satisfy constraint: "
                "Member must satisfy enum value set: [Share]."
            )

        document = self._get_documents(name)
        document.modify_permissions(
            account_ids_to_add, account_ids_to_remove, shared_document_version
        )

    def delete_parameter(self, name):
        self._resource_tags.get("Parameter", {}).pop(name, None)
        return self._parameters.pop(name, None)

    def delete_parameters(self, names):
        result = []
        for name in names:
            try:
                del self._parameters[name]
                result.append(name)
                self._resource_tags.get("Parameter", {}).pop(name, None)
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
            ssm_parameter = self.get_parameter(param_name)
            if not self._match_filters(ssm_parameter, parameter_filters):
                continue

            if filters:
                for _filter in filters:
                    if _filter["Key"] == "Name":
                        k = ssm_parameter.name
                        for v in _filter["Values"]:
                            if k.startswith(v):
                                result.append(ssm_parameter)
                                break
                    elif _filter["Key"] == "Type":
                        k = ssm_parameter.type
                        for v in _filter["Values"]:
                            if k == v:
                                result.append(ssm_parameter)
                                break
                    elif _filter["Key"] == "KeyId":
                        k = ssm_parameter.keyid
                        if k:
                            for v in _filter["Values"]:
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
                        key=f"parameterFilters.{index + 1}.member.key",
                        value=key,
                        constraint="Member must satisfy regular expression pattern: tag:.+|Name|Type|KeyId|Path|Label|Tier",
                    )
                )

            if len(key) > 132:
                self._errors.append(
                    self._format_error(
                        key=f"parameterFilters.{index + 1}.member.key",
                        value=key,
                        constraint="Member must have length less than or equal to 132",
                    )
                )

            if len(option) > 10:
                self._errors.append(
                    self._format_error(
                        key=f"parameterFilters.{index + 1}.member.option",
                        value="over 10 chars",
                        constraint="Member must have length less than or equal to 10",
                    )
                )

            if len(values) > 50:
                self._errors.append(
                    self._format_error(
                        key=f"parameterFilters.{index + 1}.member.values",
                        value=values,
                        constraint="Member must have length less than or equal to 50",
                    )
                )

            if any(len(value) > 1024 for value in values):
                self._errors.append(
                    self._format_error(
                        key=f"parameterFilters.{index + 1}.member.values",
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
                    f"The following filter key is not valid: {key}. Valid filter keys include: [Type, KeyId]."
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
                        f"The following filter option is not valid: {option}. Valid options include: [Recursive, OneLevel]."
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
                        or not re.match(r"^[a-zA-Z0-9_.\-/]*$", value)
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
                            f"The following filter value is not valid: {value}. Valid values include: [Standard, Advanced, Intelligent-Tiering]."
                        )

            if key == "Type":
                for value in values:
                    if value not in ["String", "StringList", "SecureString"]:
                        raise InvalidFilterOption(
                            f"The following filter value is not valid: {value}. Valid values include: [String, StringList, SecureString]."
                        )

            allowed_options = ["Equals", "BeginsWith"]
            if key == "Name":
                allowed_options += ["Contains"]
            if key != "Path" and option not in allowed_options:
                raise InvalidFilterOption(
                    f"The following filter option is not valid: {option}. Valid options include: [BeginsWith, Equals]."
                )

            filter_keys.append(key)

    def _format_error(self, key, value, constraint):
        return f'Value "{value}" at "{key}" failed to satisfy constraint: {constraint}'

    def _raise_errors(self):
        if self._errors:
            count = len(self._errors)
            plural = "s" if len(self._errors) > 1 else ""
            errors = "; ".join(self._errors)
            self._errors = []  # reset collected errors

            raise ValidationException(
                f"{count} validation error{plural} detected: {errors}"
            )

    def get_all_parameters(self):
        result = []
        for k, _ in self._parameters.items():
            result.append(self._parameters[k])
        return result

    def get_parameters(self, names):
        result = {}

        if len(names) > 10:
            all_names = ", ".join(names)
            raise ValidationException(
                "1 validation error detected: "
                f"Value '[{all_names}]' at 'names' failed to satisfy constraint: Member must have length less than or equal to 10."
            )

        for name in set(names):
            if name.split(":")[0] in self._parameters:
                try:
                    param = self.get_parameter(name)

                    if param is not None:
                        result[name] = param
                except ParameterVersionNotFound:
                    pass
        return result

    def get_parameters_by_path(
        self,
        path,
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
        for param_name in self._parameters.get_keys_beginning_with(path, recursive):
            parameter = self.get_parameter(param_name)
            if not self._match_filters(parameter, filters):
                continue
            result.append(parameter)

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

    def get_parameter_history(self, name, next_token, max_results=50):

        if max_results > PARAMETER_HISTORY_MAX_RESULTS:
            raise ValidationException(
                "1 validation error detected: "
                f"Value '{max_results}' at 'maxResults' failed to satisfy constraint: "
                f"Member must have value less than or equal to {PARAMETER_HISTORY_MAX_RESULTS}."
            )

        if name in self._parameters:
            history = self._parameters[name]
            return self._get_history_nexttoken(history, next_token, max_results)

        return None, None

    def _get_history_nexttoken(self, history, next_token, max_results):
        if next_token is None:
            next_token = 0
        next_token = int(next_token)
        max_results = int(max_results)
        history_to_return = history[next_token : next_token + max_results]
        if (
            len(history_to_return) == max_results
            and len(history) > next_token + max_results
        ):
            new_next_token = next_token + max_results
            return history_to_return, str(new_next_token)
        return history_to_return, None

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
            elif key == "Label":
                what = parameter.labels
                # Label filter can only have option="Equals" (also valid implicitly)
                if len(what) == 0 or not all(label in values for label in what):
                    return False
                else:
                    continue
            elif key.startswith("tag:"):
                what = key[4:] or None
                for tag in parameter.tags:
                    if tag["Key"] == what and tag["Value"] in values:
                        return True
                return False

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

    def get_parameter(self, name):
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
                    elif len(parameters) > 0:
                        raise ParameterVersionNotFound(
                            "Systems Manager could not find version %s of %s. "
                            "Verify the version and try again."
                            % (version_or_label, name_prefix)
                        )
                result = list(
                    filter(lambda x: version_or_label in x.labels, parameters)
                )
                if len(result) > 0:
                    return result[-1]

        return None

    def label_parameter_version(self, name, version, labels):
        previous_parameter_versions = self._parameters[name]
        if not previous_parameter_versions:
            raise ParameterNotFound(f"Parameter {name} not found.")
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
                f"Systems Manager could not find version {version} of {name}. Verify the version and try again."
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

    def _check_for_parameter_version_limit_exception(self, name):
        # https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-versions.html
        parameter_versions = self._parameters[name]
        oldest_parameter = parameter_versions[0]
        if oldest_parameter.labels:
            raise ParameterMaxVersionLimitExceeded(
                f"You attempted to create a new version of {name} by calling the PutParameter API "
                f"with the overwrite flag. Version {oldest_parameter.version}, the oldest version, can't be deleted "
                "because it has a label associated with it. Move the label to another version "
                "of the parameter, and try again."
            )

    def put_parameter(
        self,
        name,
        description,
        value,
        parameter_type,
        allowed_pattern,
        keyid,
        overwrite,
        tags,
        data_type,
    ):
        if not value:
            raise ValidationException(
                "1 validation error detected: Value '' at 'value' failed to satisfy"
                " constraint: Member must have length greater than or equal to 1."
            )
        if overwrite and tags:
            raise ValidationException(
                "Invalid request: tags and overwrite can't be used together. To create a "
                "parameter with tags, please remove overwrite flag. To update tags for an "
                "existing parameter, please use AddTagsToResource or RemoveTagsFromResource."
            )
        if name.lower().lstrip("/").startswith("aws") or name.lower().lstrip(
            "/"
        ).startswith("ssm"):
            is_path = name.count("/") > 1
            if name.lower().startswith("/aws") and is_path:
                raise AccessDeniedException(
                    f"No access to reserved parameter name: {name}."
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

        if not _valid_parameter_data_type(data_type):
            # The check of the existence of an AMI ID in the account for a parameter of DataType `aws:ec2:image`
            # is not supported. The parameter will be created.
            # https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-ec2-aliases.html
            raise ValidationException(
                f"The following data type is not supported: {data_type} (Data type names are all lowercase.)"
            )

        previous_parameter_versions = self._parameters[name]
        if len(previous_parameter_versions) == 0:
            previous_parameter = None
            version = 1
        else:
            previous_parameter = previous_parameter_versions[-1]
            version = previous_parameter.version + 1

            if not overwrite:
                return

            if len(previous_parameter_versions) >= PARAMETER_VERSION_LIMIT:
                self._check_for_parameter_version_limit_exception(name)
                previous_parameter_versions.pop(0)

        last_modified_date = time.time()
        self._parameters[name].append(
            Parameter(
                account_id=self.account_id,
                name=name,
                value=value,
                parameter_type=parameter_type,
                description=description,
                allowed_pattern=allowed_pattern,
                keyid=keyid,
                last_modified_date=last_modified_date,
                version=version,
                tags=tags or [],
                data_type=data_type,
            )
        )

        if tags:
            tags = {t["Key"]: t["Value"] for t in tags}
            self.add_tags_to_resource("Parameter", name, tags)

        return version

    def add_tags_to_resource(self, resource_type, resource_id, tags):
        self._validate_resource_type_and_id(resource_type, resource_id)
        for key, value in tags.items():
            self._resource_tags[resource_type][resource_id][key] = value

    def remove_tags_from_resource(self, resource_type, resource_id, keys):
        self._validate_resource_type_and_id(resource_type, resource_id)
        tags = self._resource_tags[resource_type][resource_id]
        for key in keys:
            if key in tags:
                del tags[key]

    def list_tags_for_resource(self, resource_type, resource_id):
        self._validate_resource_type_and_id(resource_type, resource_id)
        return self._resource_tags[resource_type][resource_id]

    def _validate_resource_type_and_id(self, resource_type, resource_id):
        if resource_type == "Parameter":
            if resource_id not in self._parameters:
                raise InvalidResourceId()
            else:
                return
        elif resource_type == "Document":
            if resource_id not in self._documents:
                raise InvalidResourceId()
            else:
                return
        elif resource_type not in (
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.remove_tags_from_resource
            "ManagedInstance",
            "MaintenanceWindow",
            "PatchBaseline",
            "OpsItem",
            "OpsMetadata",
        ):
            raise InvalidResourceType()
        else:
            raise InvalidResourceId()

    def send_command(self, **kwargs):
        command = Command(
            account_id=self.account_id,
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
            backend_region=self.region_name,
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

    def get_command_by_id(self, command_id):
        command = next(
            (command for command in self._commands if command.command_id == command_id),
            None,
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

    def create_maintenance_window(
        self,
        name,
        description,
        enabled,
        duration,
        cutoff,
        schedule,
        schedule_timezone,
        schedule_offset,
        start_date,
        end_date,
    ):
        """
        Creates a maintenance window. No error handling or input validation has been implemented yet.
        """
        window = FakeMaintenanceWindow(
            name,
            description,
            enabled,
            duration,
            cutoff,
            schedule,
            schedule_timezone,
            schedule_offset,
            start_date,
            end_date,
        )
        self.windows[window.id] = window
        return window.id

    def get_maintenance_window(self, window_id):
        """
        The window is assumed to exist - no error handling has been implemented yet.
        The NextExecutionTime-field is not returned.
        """
        return self.windows[window_id]

    def describe_maintenance_windows(self, filters):
        """
        Returns all windows. No pagination has been implemented yet. Only filtering for Name is supported.
        The NextExecutionTime-field is not returned.

        """
        res = [window for window in self.windows.values()]
        if filters:
            for f in filters:
                if f["Key"] == "Name":
                    res = [w for w in res if w.name in f["Values"]]
        return res

    def delete_maintenance_window(self, window_id):
        """
        Assumes the provided WindowId exists. No error handling has been implemented yet.
        """
        del self.windows[window_id]


ssm_backends = BackendDict(SimpleSystemManagerBackend, "ssm")
