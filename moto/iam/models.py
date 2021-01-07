from __future__ import unicode_literals
import base64
import hashlib
import os
import random
import string
import sys
from datetime import datetime
import json
import re
import time

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from six.moves.urllib import parse
from moto.core.exceptions import RESTError
from moto.core import BaseBackend, BaseModel, ACCOUNT_ID, CloudFormationModel
from moto.core.utils import (
    iso_8601_datetime_without_milliseconds,
    iso_8601_datetime_with_milliseconds,
)
from moto.iam.policy_validation import IAMPolicyDocumentValidator

from .aws_managed_policies import aws_managed_policies_data
from .exceptions import (
    IAMNotFoundException,
    IAMConflictException,
    IAMReportNotPresentException,
    IAMLimitExceededException,
    MalformedCertificate,
    DuplicateTags,
    TagKeyTooBig,
    InvalidTagCharacters,
    TooManyTags,
    TagValueTooBig,
    EntityAlreadyExists,
    ValidationError,
    InvalidInput,
    NoSuchEntity,
)
from .utils import (
    random_access_key,
    random_alphanumeric,
    random_resource_id,
    random_policy_id,
)


class MFADevice(object):
    """MFA Device class."""

    def __init__(self, serial_number, authentication_code_1, authentication_code_2):
        self.enable_date = datetime.utcnow()
        self.serial_number = serial_number
        self.authentication_code_1 = authentication_code_1
        self.authentication_code_2 = authentication_code_2

    @property
    def enabled_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.enable_date)


class VirtualMfaDevice(object):
    def __init__(self, device_name):
        self.serial_number = "arn:aws:iam::{0}:mfa{1}".format(ACCOUNT_ID, device_name)

        random_base32_string = "".join(
            random.choice(string.ascii_uppercase + "234567") for _ in range(64)
        )
        self.base32_string_seed = base64.b64encode(
            random_base32_string.encode("ascii")
        ).decode("ascii")
        self.qr_code_png = base64.b64encode(
            os.urandom(64)
        )  # this would be a generated PNG

        self.enable_date = None
        self.user_attribute = None
        self.user = None

    @property
    def enabled_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.enable_date)


class Policy(CloudFormationModel):

    # Note: This class does not implement the CloudFormation support for AWS::IAM::Policy, as that CF resource
    #  is for creating *inline* policies.  That is done in class InlinePolicy.

    is_attachable = False

    def __init__(
        self,
        name,
        default_version_id=None,
        description=None,
        document=None,
        path=None,
        create_date=None,
        update_date=None,
    ):
        self.name = name

        self.attachment_count = 0
        self.description = description or ""
        self.id = random_policy_id()
        self.path = path or "/"

        if default_version_id:
            self.default_version_id = default_version_id
            self.next_version_num = int(default_version_id.lstrip("v")) + 1
        else:
            self.default_version_id = "v1"
            self.next_version_num = 2
        self.versions = [
            PolicyVersion(
                self.arn, document, True, self.default_version_id, update_date
            )
        ]

        self.create_date = create_date if create_date is not None else datetime.utcnow()
        self.update_date = update_date if update_date is not None else datetime.utcnow()

    def update_default_version(self, new_default_version_id):
        for version in self.versions:
            if version.version_id == new_default_version_id:
                version.is_default = True
            if version.version_id == self.default_version_id:
                version.is_default = False
        self.default_version_id = new_default_version_id

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    @property
    def updated_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.update_date)


class SAMLProvider(BaseModel):
    def __init__(self, name, saml_metadata_document=None):
        self.name = name
        self.saml_metadata_document = saml_metadata_document

    @property
    def arn(self):
        return "arn:aws:iam::{0}:saml-provider/{1}".format(ACCOUNT_ID, self.name)


class OpenIDConnectProvider(BaseModel):
    def __init__(self, url, thumbprint_list, client_id_list=None):
        self._errors = []
        self._validate(url, thumbprint_list, client_id_list)

        parsed_url = parse.urlparse(url)
        self.url = parsed_url.netloc + parsed_url.path
        self.thumbprint_list = thumbprint_list
        self.client_id_list = client_id_list
        self.create_date = datetime.utcnow()

    @property
    def arn(self):
        return "arn:aws:iam::{0}:oidc-provider/{1}".format(ACCOUNT_ID, self.url)

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.create_date)

    def _validate(self, url, thumbprint_list, client_id_list):
        if any(len(client_id) > 255 for client_id in client_id_list):
            self._errors.append(
                self._format_error(
                    key="clientIDList",
                    value=client_id_list,
                    constraint="Member must satisfy constraint: "
                    "[Member must have length less than or equal to 255, "
                    "Member must have length greater than or equal to 1]",
                )
            )

        if any(len(thumbprint) > 40 for thumbprint in thumbprint_list):
            self._errors.append(
                self._format_error(
                    key="thumbprintList",
                    value=thumbprint_list,
                    constraint="Member must satisfy constraint: "
                    "[Member must have length less than or equal to 40, "
                    "Member must have length greater than or equal to 40]",
                )
            )

        if len(url) > 255:
            self._errors.append(
                self._format_error(
                    key="url",
                    value=url,
                    constraint="Member must have length less than or equal to 255",
                )
            )

        self._raise_errors()

        parsed_url = parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValidationError("Invalid Open ID Connect Provider URL")

        if len(thumbprint_list) > 5:
            raise InvalidInput("Thumbprint list must contain fewer than 5 entries.")

        if len(client_id_list) > 100:
            raise IAMLimitExceededException(
                "Cannot exceed quota for ClientIdsPerOpenIdConnectProvider: 100"
            )

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

            raise ValidationError(
                "{count} validation error{plural} detected: {errors}".format(
                    count=count, plural=plural, errors=errors
                )
            )


class PolicyVersion(object):
    def __init__(
        self, policy_arn, document, is_default=False, version_id="v1", create_date=None
    ):
        self.policy_arn = policy_arn
        self.document = document or {}
        self.is_default = is_default
        self.version_id = version_id

        self.create_date = create_date if create_date is not None else datetime.utcnow()

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)


class ManagedPolicy(Policy):
    """Managed policy."""

    is_attachable = True

    def attach_to(self, obj):
        self.attachment_count += 1
        obj.managed_policies[self.arn] = self

    def detach_from(self, obj):
        self.attachment_count -= 1
        del obj.managed_policies[self.arn]

    @property
    def arn(self):
        return "arn:aws:iam::{0}:policy{1}{2}".format(ACCOUNT_ID, self.path, self.name)

    def to_config_dict(self):
        return {
            "version": "1.3",
            "configurationItemCaptureTime": str(self.create_date),
            "configurationItemStatus": "OK",
            "configurationStateId": str(
                int(time.mktime(self.create_date.timetuple()))
            ),  # PY2 and 3 compatible
            "arn": "arn:aws:iam::{}:policy/{}".format(ACCOUNT_ID, self.name),
            "resourceType": "AWS::IAM::Policy",
            "resourceId": self.id,
            "resourceName": self.name,
            "awsRegion": "global",
            "availabilityZone": "Not Applicable",
            "resourceCreationTime": str(self.create_date),
            "configuration": {
                "policyName": self.name,
                "policyId": self.id,
                "arn": "arn:aws:iam::{}:policy/{}".format(ACCOUNT_ID, self.name),
                "path": self.path,
                "defaultVersionId": self.default_version_id,
                "attachmentCount": self.attachment_count,
                "permissionsBoundaryUsageCount": 0,
                "isAttachable": ManagedPolicy.is_attachable,
                "description": self.description,
                "createDate": str(self.create_date.isoformat()),
                "updateDate": str(self.create_date.isoformat()),
                "policyVersionList": list(
                    map(
                        lambda version: {
                            "document": parse.quote(version.document),
                            "versionId": version.version_id,
                            "isDefaultVersion": version.is_default,
                            "createDate": str(version.create_date),
                        },
                        self.versions,
                    )
                ),
            },
            "supplementaryConfiguration": {},
        }


class AWSManagedPolicy(ManagedPolicy):
    """AWS-managed policy."""

    @classmethod
    def from_data(cls, name, data):
        return cls(
            name,
            default_version_id=data.get("DefaultVersionId"),
            path=data.get("Path"),
            document=json.dumps(data.get("Document")),
            create_date=datetime.strptime(
                data.get("CreateDate"), "%Y-%m-%dT%H:%M:%S+00:00"
            ),
            update_date=datetime.strptime(
                data.get("UpdateDate"), "%Y-%m-%dT%H:%M:%S+00:00"
            ),
        )

    @property
    def arn(self):
        return "arn:aws:iam::aws:policy{0}{1}".format(self.path, self.name)


# AWS defines some of its own managed policies and we periodically
# import them via `make aws_managed_policies`
# FIXME: Takes about 40ms at import time
aws_managed_policies = [
    AWSManagedPolicy.from_data(name, d)
    for name, d in json.loads(aws_managed_policies_data).items()
]


class InlinePolicy(CloudFormationModel):
    # Represents an Inline Policy created by CloudFormation
    def __init__(
        self,
        resource_name,
        policy_name,
        policy_document,
        group_names,
        role_names,
        user_names,
    ):
        self.name = resource_name
        self.policy_name = None
        self.policy_document = None
        self.group_names = None
        self.role_names = None
        self.user_names = None
        self.update(policy_name, policy_document, group_names, role_names, user_names)

    def update(
        self, policy_name, policy_document, group_names, role_names, user_names,
    ):
        self.policy_name = policy_name
        self.policy_document = (
            json.dumps(policy_document)
            if isinstance(policy_document, dict)
            else policy_document
        )
        self.group_names = group_names
        self.role_names = role_names
        self.user_names = user_names

    @staticmethod
    def cloudformation_name_type():
        return None  # Resource never gets named after by template PolicyName!

    @staticmethod
    def cloudformation_type():
        return "AWS::IAM::Policy"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_physical_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json.get("Properties", {})
        policy_document = properties.get("PolicyDocument")
        policy_name = properties.get("PolicyName")
        user_names = properties.get("Users")
        role_names = properties.get("Roles")
        group_names = properties.get("Groups")

        return iam_backend.create_inline_policy(
            resource_physical_name,
            policy_name,
            policy_document,
            group_names,
            role_names,
            user_names,
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name,
    ):
        properties = cloudformation_json["Properties"]

        if cls.is_replacement_update(properties):
            resource_name_property = cls.cloudformation_name_type()
            if resource_name_property not in properties:
                properties[resource_name_property] = new_resource_name
            new_resource = cls.create_from_cloudformation_json(
                properties[resource_name_property], cloudformation_json, region_name
            )
            properties[resource_name_property] = original_resource.name
            cls.delete_from_cloudformation_json(
                original_resource.name, cloudformation_json, region_name
            )
            return new_resource

        else:  # No Interruption
            properties = cloudformation_json.get("Properties", {})
            policy_document = properties.get("PolicyDocument")
            policy_name = properties.get("PolicyName", original_resource.name)
            user_names = properties.get("Users")
            role_names = properties.get("Roles")
            group_names = properties.get("Groups")

            return iam_backend.update_inline_policy(
                original_resource.name,
                policy_name,
                policy_document,
                group_names,
                role_names,
                user_names,
            )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        iam_backend.delete_inline_policy(resource_name)

    @staticmethod
    def is_replacement_update(properties):
        properties_requiring_replacement_update = []
        return any(
            [
                property_requiring_replacement in properties
                for property_requiring_replacement in properties_requiring_replacement_update
            ]
        )

    @property
    def physical_resource_id(self):
        return self.name

    def apply_policy(self, backend):
        if self.user_names:
            for user_name in self.user_names:
                backend.put_user_policy(
                    user_name, self.policy_name, self.policy_document
                )
        if self.role_names:
            for role_name in self.role_names:
                backend.put_role_policy(
                    role_name, self.policy_name, self.policy_document
                )
        if self.group_names:
            for group_name in self.group_names:
                backend.put_group_policy(
                    group_name, self.policy_name, self.policy_document
                )

    def unapply_policy(self, backend):
        if self.user_names:
            for user_name in self.user_names:
                backend.delete_user_policy(user_name, self.policy_name)
        if self.role_names:
            for role_name in self.role_names:
                backend.delete_role_policy(role_name, self.policy_name)
        if self.group_names:
            for group_name in self.group_names:
                backend.delete_group_policy(group_name, self.policy_name)


class Role(CloudFormationModel):
    def __init__(
        self,
        role_id,
        name,
        assume_role_policy_document,
        path,
        permissions_boundary,
        description,
        tags,
        max_session_duration,
    ):
        self.id = role_id
        self.name = name
        self.assume_role_policy_document = assume_role_policy_document
        self.path = path or "/"
        self.policies = {}
        self.managed_policies = {}
        self.create_date = datetime.utcnow()
        self.tags = tags
        self.description = description
        self.permissions_boundary = permissions_boundary
        self.max_session_duration = max_session_duration

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    @staticmethod
    def cloudformation_name_type():
        return "RoleName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-role.html
        return "AWS::IAM::Role"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_physical_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        role_name = (
            properties["RoleName"]
            if "RoleName" in properties
            else resource_physical_name
        )

        role = iam_backend.create_role(
            role_name=role_name,
            assume_role_policy_document=properties["AssumeRolePolicyDocument"],
            path=properties.get("Path", "/"),
            permissions_boundary=properties.get("PermissionsBoundary", ""),
            description=properties.get("Description", ""),
            tags=properties.get("Tags", {}),
            max_session_duration=properties.get("MaxSessionDuration", 3600),
        )

        policies = properties.get("Policies", [])
        for policy in policies:
            policy_name = policy["PolicyName"]
            policy_json = policy["PolicyDocument"]
            role.put_policy(policy_name, policy_json)

        return role

    @property
    def arn(self):
        return "arn:aws:iam::{0}:role{1}{2}".format(ACCOUNT_ID, self.path, self.name)

    def to_config_dict(self):
        _managed_policies = []
        for key in self.managed_policies.keys():
            _managed_policies.append(
                {"policyArn": key, "policyName": iam_backend.managed_policies[key].name}
            )

        _role_policy_list = []
        for key, value in self.policies.items():
            _role_policy_list.append(
                {"policyName": key, "policyDocument": parse.quote(value)}
            )

        _instance_profiles = []
        for key, instance_profile in iam_backend.instance_profiles.items():
            for role in instance_profile.roles:
                _instance_profiles.append(instance_profile.to_embedded_config_dict())
                break

        config_dict = {
            "version": "1.3",
            "configurationItemCaptureTime": str(self.create_date),
            "configurationItemStatus": "ResourceDiscovered",
            "configurationStateId": str(
                int(time.mktime(self.create_date.timetuple()))
            ),  # PY2 and 3 compatible
            "arn": "arn:aws:iam::{}:role/{}".format(ACCOUNT_ID, self.name),
            "resourceType": "AWS::IAM::Role",
            "resourceId": self.name,
            "resourceName": self.name,
            "awsRegion": "global",
            "availabilityZone": "Not Applicable",
            "resourceCreationTime": str(self.create_date),
            "relatedEvents": [],
            "relationships": [],
            "tags": self.tags,
            "configuration": {
                "path": self.path,
                "roleName": self.name,
                "roleId": self.id,
                "arn": "arn:aws:iam::{}:role/{}".format(ACCOUNT_ID, self.name),
                "assumeRolePolicyDocument": parse.quote(
                    self.assume_role_policy_document
                )
                if self.assume_role_policy_document
                else None,
                "instanceProfileList": _instance_profiles,
                "rolePolicyList": _role_policy_list,
                "createDate": self.create_date.isoformat(),
                "attachedManagedPolicies": _managed_policies,
                "permissionsBoundary": self.permissions_boundary,
                "tags": list(
                    map(
                        lambda key: {"key": key, "value": self.tags[key]["Value"]},
                        self.tags,
                    )
                ),
                "roleLastUsed": None,
            },
            "supplementaryConfiguration": {},
        }
        return config_dict

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def delete_policy(self, policy_name):
        try:
            del self.policies[policy_name]
        except KeyError:
            raise IAMNotFoundException(
                "The role policy with name {0} cannot be found.".format(policy_name)
            )

    @property
    def physical_resource_id(self):
        return self.id

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()

    def get_tags(self):
        return [self.tags[tag] for tag in self.tags]


class InstanceProfile(CloudFormationModel):
    def __init__(self, instance_profile_id, name, path, roles):
        self.id = instance_profile_id
        self.name = name
        self.path = path or "/"
        self.roles = roles if roles else []
        self.create_date = datetime.utcnow()

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    @staticmethod
    def cloudformation_name_type():
        return "InstanceProfileName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-instanceprofile.html
        return "AWS::IAM::InstanceProfile"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_physical_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        role_ids = properties["Roles"]
        return iam_backend.create_instance_profile(
            name=resource_physical_name,
            path=properties.get("Path", "/"),
            role_ids=role_ids,
        )

    @property
    def arn(self):
        return "arn:aws:iam::{0}:instance-profile{1}{2}".format(
            ACCOUNT_ID, self.path, self.name
        )

    @property
    def physical_resource_id(self):
        return self.name

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()

    def to_embedded_config_dict(self):
        # Instance Profiles aren't a config item itself, but they are returned in IAM roles with
        # a "config like" json structure It's also different than Role.to_config_dict()
        roles = []
        for role in self.roles:
            roles.append(
                {
                    "path": role.path,
                    "roleName": role.name,
                    "roleId": role.id,
                    "arn": "arn:aws:iam::{}:role/{}".format(ACCOUNT_ID, role.name),
                    "createDate": str(role.create_date),
                    "assumeRolePolicyDocument": parse.quote(
                        role.assume_role_policy_document
                    ),
                    "description": role.description,
                    "maxSessionDuration": None,
                    "permissionsBoundary": role.permissions_boundary,
                    "tags": list(
                        map(
                            lambda key: {"key": key, "value": role.tags[key]["Value"]},
                            role.tags,
                        )
                    ),
                    "roleLastUsed": None,
                }
            )

        return {
            "path": self.path,
            "instanceProfileName": self.name,
            "instanceProfileId": self.id,
            "arn": "arn:aws:iam::{}:instance-profile/{}".format(ACCOUNT_ID, self.name),
            "createDate": str(self.create_date),
            "roles": roles,
        }


class Certificate(BaseModel):
    def __init__(self, cert_name, cert_body, private_key, cert_chain=None, path=None):
        self.cert_name = cert_name
        self.cert_body = cert_body
        self.private_key = private_key
        self.path = path if path else "/"
        self.cert_chain = cert_chain

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def arn(self):
        return "arn:aws:iam::{0}:server-certificate{1}{2}".format(
            ACCOUNT_ID, self.path, self.cert_name
        )


class SigningCertificate(BaseModel):
    def __init__(self, id, user_name, body):
        self.id = id
        self.user_name = user_name
        self.body = body
        self.upload_date = datetime.utcnow()
        self.status = "Active"

    @property
    def uploaded_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.upload_date)


class AccessKey(CloudFormationModel):
    def __init__(self, user_name, status="Active"):
        self.user_name = user_name
        self.access_key_id = "AKIA" + random_access_key()
        self.secret_access_key = random_alphanumeric(40)
        self.status = status
        self.create_date = datetime.utcnow()
        self.last_used = None

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.create_date)

    @property
    def last_used_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.last_used)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "SecretAccessKey":
            return self.secret_access_key
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return None  # Resource never gets named after by template PolicyName!

    @staticmethod
    def cloudformation_type():
        return "AWS::IAM::AccessKey"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_physical_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json.get("Properties", {})
        user_name = properties.get("UserName")
        status = properties.get("Status", "Active")

        return iam_backend.create_access_key(user_name, status=status,)

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name,
    ):
        properties = cloudformation_json["Properties"]

        if cls.is_replacement_update(properties):
            new_resource = cls.create_from_cloudformation_json(
                new_resource_name, cloudformation_json, region_name
            )
            cls.delete_from_cloudformation_json(
                original_resource.physical_resource_id, cloudformation_json, region_name
            )
            return new_resource

        else:  # No Interruption
            properties = cloudformation_json.get("Properties", {})
            status = properties.get("Status")
            return iam_backend.update_access_key(
                original_resource.user_name, original_resource.access_key_id, status
            )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        iam_backend.delete_access_key_by_name(resource_name)

    @staticmethod
    def is_replacement_update(properties):
        properties_requiring_replacement_update = ["Serial", "UserName"]
        return any(
            [
                property_requiring_replacement in properties
                for property_requiring_replacement in properties_requiring_replacement_update
            ]
        )

    @property
    def physical_resource_id(self):
        return self.access_key_id


class SshPublicKey(BaseModel):
    def __init__(self, user_name, ssh_public_key_body):
        self.user_name = user_name
        self.ssh_public_key_body = ssh_public_key_body
        self.ssh_public_key_id = "APKA" + random_access_key()
        self.fingerprint = hashlib.md5(ssh_public_key_body.encode()).hexdigest()
        self.status = "Active"
        self.upload_date = datetime.utcnow()

    @property
    def uploaded_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.upload_date)


class Group(BaseModel):
    def __init__(self, name, path="/"):
        self.name = name
        self.id = random_resource_id()
        self.path = path
        self.create_date = datetime.utcnow()

        self.users = []
        self.managed_policies = {}
        self.policies = {}

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()

    @property
    def arn(self):
        if self.path == "/":
            return "arn:aws:iam::{0}:group/{1}".format(ACCOUNT_ID, self.name)

        else:
            return "arn:aws:iam::{0}:group/{1}/{2}".format(
                ACCOUNT_ID, self.path, self.name
            )

    def get_policy(self, policy_name):
        try:
            policy_json = self.policies[policy_name]
        except KeyError:
            raise IAMNotFoundException("Policy {0} not found".format(policy_name))

        return {
            "policy_name": policy_name,
            "policy_document": policy_json,
            "group_name": self.name,
        }

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def list_policies(self):
        return self.policies.keys()

    def delete_policy(self, policy_name):
        if policy_name not in self.policies:
            raise IAMNotFoundException("Policy {0} not found".format(policy_name))

        del self.policies[policy_name]


class User(CloudFormationModel):
    def __init__(self, name, path=None, tags=None):
        self.name = name
        self.id = random_resource_id()
        self.path = path if path else "/"
        self.create_date = datetime.utcnow()
        self.mfa_devices = {}
        self.policies = {}
        self.managed_policies = {}
        self.access_keys = []
        self.ssh_public_keys = []
        self.password = None
        self.password_reset_required = False
        self.signing_certificates = {}
        self.tags = tags

    @property
    def arn(self):
        return "arn:aws:iam::{0}:user{1}{2}".format(ACCOUNT_ID, self.path, self.name)

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    def get_policy(self, policy_name):
        policy_json = None
        try:
            policy_json = self.policies[policy_name]
        except KeyError:
            raise IAMNotFoundException("Policy {0} not found".format(policy_name))

        return {
            "policy_name": policy_name,
            "policy_document": policy_json,
            "user_name": self.name,
        }

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def deactivate_mfa_device(self, serial_number):
        self.mfa_devices.pop(serial_number)

    def delete_policy(self, policy_name):
        if policy_name not in self.policies:
            raise IAMNotFoundException("Policy {0} not found".format(policy_name))

        del self.policies[policy_name]

    def create_access_key(self, status="Active"):
        access_key = AccessKey(self.name, status)
        self.access_keys.append(access_key)
        return access_key

    def enable_mfa_device(
        self, serial_number, authentication_code_1, authentication_code_2
    ):
        self.mfa_devices[serial_number] = MFADevice(
            serial_number, authentication_code_1, authentication_code_2
        )

    def get_all_access_keys(self):
        return self.access_keys

    def delete_access_key(self, access_key_id):
        key = self.get_access_key_by_id(access_key_id)
        self.access_keys.remove(key)

    def update_access_key(self, access_key_id, status=None):
        key = self.get_access_key_by_id(access_key_id)
        if status is not None:
            key.status = status
        return key

    def get_access_key_by_id(self, access_key_id):
        for key in self.access_keys:
            if key.access_key_id == access_key_id:
                return key
        else:
            raise IAMNotFoundException(
                "The Access Key with id {0} cannot be found".format(access_key_id)
            )

    def has_access_key(self, access_key_id):
        return any(
            [
                access_key
                for access_key in self.access_keys
                if access_key.access_key_id == access_key_id
            ]
        )

    def upload_ssh_public_key(self, ssh_public_key_body):
        pubkey = SshPublicKey(self.name, ssh_public_key_body)
        self.ssh_public_keys.append(pubkey)
        return pubkey

    def get_ssh_public_key(self, ssh_public_key_id):
        for key in self.ssh_public_keys:
            if key.ssh_public_key_id == ssh_public_key_id:
                return key
        else:
            raise IAMNotFoundException(
                "The SSH Public Key with id {0} cannot be found".format(
                    ssh_public_key_id
                )
            )

    def get_all_ssh_public_keys(self):
        return self.ssh_public_keys

    def update_ssh_public_key(self, ssh_public_key_id, status):
        key = self.get_ssh_public_key(ssh_public_key_id)
        key.status = status

    def delete_ssh_public_key(self, ssh_public_key_id):
        key = self.get_ssh_public_key(ssh_public_key_id)
        self.ssh_public_keys.remove(key)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()

    def to_csv(self):
        date_format = "%Y-%m-%dT%H:%M:%S+00:00"
        date_created = self.create_date
        # aagrawal,arn:aws:iam::509284790694:user/aagrawal,2014-09-01T22:28:48+00:00,true,2014-11-12T23:36:49+00:00,2014-09-03T18:59:00+00:00,N/A,false,true,2014-09-01T22:28:48+00:00,false,N/A,false,N/A,false,N/A
        if not self.password:
            password_enabled = "false"
            password_last_used = "not_supported"
        else:
            password_enabled = "true"
            password_last_used = "no_information"

        if len(self.access_keys) == 0:
            access_key_1_active = "false"
            access_key_1_last_rotated = "N/A"
            access_key_1_last_used = "N/A"
            access_key_2_active = "false"
            access_key_2_last_rotated = "N/A"
            access_key_2_last_used = "N/A"
        elif len(self.access_keys) == 1:
            access_key_1_active = (
                "true" if self.access_keys[0].status == "Active" else "false"
            )
            access_key_1_last_rotated = self.access_keys[0].create_date.strftime(
                date_format
            )
            access_key_1_last_used = (
                "N/A"
                if self.access_keys[0].last_used is None
                else self.access_keys[0].last_used.strftime(date_format)
            )
            access_key_2_active = "false"
            access_key_2_last_rotated = "N/A"
            access_key_2_last_used = "N/A"
        else:
            access_key_1_active = (
                "true" if self.access_keys[0].status == "Active" else "false"
            )
            access_key_1_last_rotated = self.access_keys[0].create_date.strftime(
                date_format
            )
            access_key_1_last_used = (
                "N/A"
                if self.access_keys[0].last_used is None
                else self.access_keys[0].last_used.strftime(date_format)
            )
            access_key_2_active = (
                "true" if self.access_keys[1].status == "Active" else "false"
            )
            access_key_2_last_rotated = self.access_keys[1].create_date.strftime(
                date_format
            )
            access_key_2_last_used = (
                "N/A"
                if self.access_keys[1].last_used is None
                else self.access_keys[1].last_used.strftime(date_format)
            )

        return "{0},{1},{2},{3},{4},{5},not_supported,false,{6},{7},{8},not_supported,not_supported,{9},{10},{11},not_supported,not_supported,false,N/A,false,N/A\n".format(
            self.name,
            self.arn,
            date_created.strftime(date_format),
            password_enabled,
            password_last_used,
            date_created.strftime(date_format),
            access_key_1_active,
            access_key_1_last_rotated,
            access_key_1_last_used,
            access_key_2_active,
            access_key_2_last_rotated,
            access_key_2_last_used,
        )

    @staticmethod
    def cloudformation_name_type():
        return "UserName"

    @staticmethod
    def cloudformation_type():
        return "AWS::IAM::User"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_physical_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json.get("Properties", {})
        path = properties.get("Path")
        return iam_backend.create_user(resource_physical_name, path)

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name,
    ):
        properties = cloudformation_json["Properties"]

        if cls.is_replacement_update(properties):
            resource_name_property = cls.cloudformation_name_type()
            if resource_name_property not in properties:
                properties[resource_name_property] = new_resource_name
            new_resource = cls.create_from_cloudformation_json(
                properties[resource_name_property], cloudformation_json, region_name
            )
            properties[resource_name_property] = original_resource.name
            cls.delete_from_cloudformation_json(
                original_resource.name, cloudformation_json, region_name
            )
            return new_resource

        else:  # No Interruption
            if "Path" in properties:
                original_resource.path = properties["Path"]
            return original_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        iam_backend.delete_user(resource_name)

    @staticmethod
    def is_replacement_update(properties):
        properties_requiring_replacement_update = ["UserName"]
        return any(
            [
                property_requiring_replacement in properties
                for property_requiring_replacement in properties_requiring_replacement_update
            ]
        )

    @property
    def physical_resource_id(self):
        return self.name


class AccountPasswordPolicy(BaseModel):
    def __init__(
        self,
        allow_change_password,
        hard_expiry,
        max_password_age,
        minimum_password_length,
        password_reuse_prevention,
        require_lowercase_characters,
        require_numbers,
        require_symbols,
        require_uppercase_characters,
    ):
        self._errors = []
        self._validate(
            max_password_age, minimum_password_length, password_reuse_prevention
        )

        self.allow_users_to_change_password = allow_change_password
        self.hard_expiry = hard_expiry
        self.max_password_age = max_password_age
        self.minimum_password_length = minimum_password_length
        self.password_reuse_prevention = password_reuse_prevention
        self.require_lowercase_characters = require_lowercase_characters
        self.require_numbers = require_numbers
        self.require_symbols = require_symbols
        self.require_uppercase_characters = require_uppercase_characters

    @property
    def expire_passwords(self):
        return True if self.max_password_age and self.max_password_age > 0 else False

    def _validate(
        self, max_password_age, minimum_password_length, password_reuse_prevention
    ):
        if minimum_password_length > 128:
            self._errors.append(
                self._format_error(
                    key="minimumPasswordLength",
                    value=minimum_password_length,
                    constraint="Member must have value less than or equal to 128",
                )
            )

        if password_reuse_prevention and password_reuse_prevention > 24:
            self._errors.append(
                self._format_error(
                    key="passwordReusePrevention",
                    value=password_reuse_prevention,
                    constraint="Member must have value less than or equal to 24",
                )
            )

        if max_password_age and max_password_age > 1095:
            self._errors.append(
                self._format_error(
                    key="maxPasswordAge",
                    value=max_password_age,
                    constraint="Member must have value less than or equal to 1095",
                )
            )

        self._raise_errors()

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

            raise ValidationError(
                "{count} validation error{plural} detected: {errors}".format(
                    count=count, plural=plural, errors=errors
                )
            )


class AccountSummary(BaseModel):
    def __init__(self, iam_backend):
        self._iam_backend = iam_backend

        self._group_policy_size_quota = 5120
        self._instance_profiles_quota = 1000
        self._groups_per_user_quota = 10
        self._attached_policies_per_user_quota = 10
        self._policies_quota = 1500
        self._account_mfa_enabled = 0  # Haven't found any information being able to activate MFA for the root account programmatically
        self._access_keys_per_user_quota = 2
        self._assume_role_policy_size_quota = 2048
        self._policy_versions_in_use_quota = 10000
        self._global_endpoint_token_version = (
            1  # ToDo: Implement set_security_token_service_preferences()
        )
        self._versions_per_policy_quota = 5
        self._attached_policies_per_group_quota = 10
        self._policy_size_quota = 6144
        self._account_signing_certificates_present = 0  # valid values: 0 | 1
        self._users_quota = 5000
        self._server_certificates_quota = 20
        self._user_policy_size_quota = 2048
        self._roles_quota = 1000
        self._signing_certificates_per_user_quota = 2
        self._role_policy_size_quota = 10240
        self._attached_policies_per_role_quota = 10
        self._account_access_keys_present = 0  # valid values: 0 | 1
        self._groups_quota = 300

    @property
    def summary_map(self):
        return {
            "GroupPolicySizeQuota": self._group_policy_size_quota,
            "InstanceProfilesQuota": self._instance_profiles_quota,
            "Policies": self._policies,
            "GroupsPerUserQuota": self._groups_per_user_quota,
            "InstanceProfiles": self._instance_profiles,
            "AttachedPoliciesPerUserQuota": self._attached_policies_per_user_quota,
            "Users": self._users,
            "PoliciesQuota": self._policies_quota,
            "Providers": self._providers,
            "AccountMFAEnabled": self._account_mfa_enabled,
            "AccessKeysPerUserQuota": self._access_keys_per_user_quota,
            "AssumeRolePolicySizeQuota": self._assume_role_policy_size_quota,
            "PolicyVersionsInUseQuota": self._policy_versions_in_use_quota,
            "GlobalEndpointTokenVersion": self._global_endpoint_token_version,
            "VersionsPerPolicyQuota": self._versions_per_policy_quota,
            "AttachedPoliciesPerGroupQuota": self._attached_policies_per_group_quota,
            "PolicySizeQuota": self._policy_size_quota,
            "Groups": self._groups,
            "AccountSigningCertificatesPresent": self._account_signing_certificates_present,
            "UsersQuota": self._users_quota,
            "ServerCertificatesQuota": self._server_certificates_quota,
            "MFADevices": self._mfa_devices,
            "UserPolicySizeQuota": self._user_policy_size_quota,
            "PolicyVersionsInUse": self._policy_versions_in_use,
            "ServerCertificates": self._server_certificates,
            "Roles": self._roles,
            "RolesQuota": self._roles_quota,
            "SigningCertificatesPerUserQuota": self._signing_certificates_per_user_quota,
            "MFADevicesInUse": self._mfa_devices_in_use,
            "RolePolicySizeQuota": self._role_policy_size_quota,
            "AttachedPoliciesPerRoleQuota": self._attached_policies_per_role_quota,
            "AccountAccessKeysPresent": self._account_access_keys_present,
            "GroupsQuota": self._groups_quota,
        }

    @property
    def _groups(self):
        return len(self._iam_backend.groups)

    @property
    def _instance_profiles(self):
        return len(self._iam_backend.instance_profiles)

    @property
    def _mfa_devices(self):
        # Don't know, if hardware devices are also counted here
        return len(self._iam_backend.virtual_mfa_devices)

    @property
    def _mfa_devices_in_use(self):
        devices = 0

        for user in self._iam_backend.users.values():
            devices += len(user.mfa_devices)

        return devices

    @property
    def _policies(self):
        customer_policies = [
            policy
            for policy in self._iam_backend.managed_policies
            if not policy.startswith("arn:aws:iam::aws:policy")
        ]
        return len(customer_policies)

    @property
    def _policy_versions_in_use(self):
        attachments = 0

        for policy in self._iam_backend.managed_policies.values():
            attachments += policy.attachment_count

        return attachments

    @property
    def _providers(self):
        providers = len(self._iam_backend.saml_providers) + len(
            self._iam_backend.open_id_providers
        )
        return providers

    @property
    def _roles(self):
        return len(self._iam_backend.roles)

    @property
    def _server_certificates(self):
        return len(self._iam_backend.certificates)

    @property
    def _users(self):
        return len(self._iam_backend.users)


def filter_items_with_path_prefix(path_prefix, items):
    return [role for role in items if role.path.startswith(path_prefix)]


class IAMBackend(BaseBackend):
    def __init__(self):
        self.instance_profiles = {}
        self.roles = {}
        self.certificates = {}
        self.groups = {}
        self.users = {}
        self.credential_report = None
        self.managed_policies = self._init_managed_policies()
        self.account_aliases = []
        self.saml_providers = {}
        self.open_id_providers = {}
        self.policy_arn_regex = re.compile(r"^arn:aws:iam::[0-9]*:policy/.*$")
        self.virtual_mfa_devices = {}
        self.account_password_policy = None
        self.account_summary = AccountSummary(self)
        self.inline_policies = {}
        self.access_keys = {}
        super(IAMBackend, self).__init__()

    def _init_managed_policies(self):
        return dict((p.arn, p) for p in aws_managed_policies)

    def attach_role_policy(self, policy_arn, role_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        policy = arns[policy_arn]
        policy.attach_to(self.get_role(role_name))

    def update_role_description(self, role_name, role_description):
        role = self.get_role(role_name)
        role.description = role_description
        return role

    def update_role(self, role_name, role_description, max_session_duration):
        role = self.get_role(role_name)
        role.description = role_description
        role.max_session_duration = max_session_duration
        return role

    def put_role_permissions_boundary(self, role_name, permissions_boundary):
        if permissions_boundary and not self.policy_arn_regex.match(
            permissions_boundary
        ):
            raise RESTError(
                "InvalidParameterValue",
                "Value ({}) for parameter PermissionsBoundary is invalid.".format(
                    permissions_boundary
                ),
            )
        role = self.get_role(role_name)
        role.permissions_boundary = permissions_boundary

    def delete_role_permissions_boundary(self, role_name):
        role = self.get_role(role_name)
        role.permissions_boundary = None

    def detach_role_policy(self, policy_arn, role_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        try:
            policy = arns[policy_arn]
            policy.detach_from(self.get_role(role_name))
        except KeyError:
            raise IAMNotFoundException("Policy {0} was not found.".format(policy_arn))

    def attach_group_policy(self, policy_arn, group_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        try:
            policy = arns[policy_arn]
        except KeyError:
            raise IAMNotFoundException("Policy {0} was not found.".format(policy_arn))
        policy.attach_to(self.get_group(group_name))

    def detach_group_policy(self, policy_arn, group_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        try:
            policy = arns[policy_arn]
        except KeyError:
            raise IAMNotFoundException("Policy {0} was not found.".format(policy_arn))
        policy.detach_from(self.get_group(group_name))

    def attach_user_policy(self, policy_arn, user_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        try:
            policy = arns[policy_arn]
        except KeyError:
            raise IAMNotFoundException("Policy {0} was not found.".format(policy_arn))
        policy.attach_to(self.get_user(user_name))

    def detach_user_policy(self, policy_arn, user_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        try:
            policy = arns[policy_arn]
        except KeyError:
            raise IAMNotFoundException("Policy {0} was not found.".format(policy_arn))
        policy.detach_from(self.get_user(user_name))

    def create_policy(self, description, path, policy_document, policy_name):
        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_document)
        iam_policy_document_validator.validate()

        policy = ManagedPolicy(
            policy_name, description=description, document=policy_document, path=path
        )
        if policy.arn in self.managed_policies:
            raise EntityAlreadyExists(
                "A policy called {0} already exists. Duplicate names are not allowed.".format(
                    policy_name
                )
            )
        self.managed_policies[policy.arn] = policy
        return policy

    def get_policy(self, policy_arn):
        if policy_arn not in self.managed_policies:
            raise IAMNotFoundException("Policy {0} not found".format(policy_arn))
        return self.managed_policies.get(policy_arn)

    def list_attached_role_policies(
        self, role_name, marker=None, max_items=100, path_prefix="/"
    ):
        policies = self.get_role(role_name).managed_policies.values()
        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def list_attached_group_policies(
        self, group_name, marker=None, max_items=100, path_prefix="/"
    ):
        policies = self.get_group(group_name).managed_policies.values()
        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def list_attached_user_policies(
        self, user_name, marker=None, max_items=100, path_prefix="/"
    ):
        policies = self.get_user(user_name).managed_policies.values()
        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def list_policies(self, marker, max_items, only_attached, path_prefix, scope):
        policies = self.managed_policies.values()

        if only_attached:
            policies = [p for p in policies if p.attachment_count > 0]

        if scope == "AWS":
            policies = [p for p in policies if isinstance(p, AWSManagedPolicy)]
        elif scope == "Local":
            policies = [p for p in policies if not isinstance(p, AWSManagedPolicy)]

        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def set_default_policy_version(self, policy_arn, version_id):
        import re

        if re.match("v[1-9][0-9]*(\.[A-Za-z0-9-]*)?", version_id) is None:
            raise ValidationError(
                "Value '{0}' at 'versionId' failed to satisfy constraint: Member must satisfy regular expression pattern: v[1-9][0-9]*(\.[A-Za-z0-9-]*)?".format(
                    version_id
                )
            )

        policy = self.get_policy(policy_arn)

        for version in policy.versions:
            if version.version_id == version_id:
                policy.update_default_version(version_id)
                return True

        raise NoSuchEntity(
            "Policy {0} version {1} does not exist or is not attachable.".format(
                policy_arn, version_id
            )
        )

    def _filter_attached_policies(self, policies, marker, max_items, path_prefix):
        if path_prefix:
            policies = [p for p in policies if p.path.startswith(path_prefix)]

        policies = sorted(policies, key=lambda policy: policy.name)
        start_idx = int(marker) if marker else 0

        policies = policies[start_idx : start_idx + max_items]

        if len(policies) < max_items:
            marker = None
        else:
            marker = str(start_idx + max_items)

        return policies, marker

    def create_role(
        self,
        role_name,
        assume_role_policy_document,
        path,
        permissions_boundary,
        description,
        tags,
        max_session_duration,
    ):
        role_id = random_resource_id()
        if permissions_boundary and not self.policy_arn_regex.match(
            permissions_boundary
        ):
            raise RESTError(
                "InvalidParameterValue",
                "Value ({}) for parameter PermissionsBoundary is invalid.".format(
                    permissions_boundary
                ),
            )
        if [role for role in self.get_roles() if role.name == role_name]:
            raise EntityAlreadyExists(
                "Role with name {0} already exists.".format(role_name)
            )

        clean_tags = self._tag_verification(tags)
        role = Role(
            role_id,
            role_name,
            assume_role_policy_document,
            path,
            permissions_boundary,
            description,
            clean_tags,
            max_session_duration,
        )
        self.roles[role_id] = role
        return role

    def get_role_by_id(self, role_id):
        return self.roles.get(role_id)

    def get_role(self, role_name):
        for role in self.get_roles():
            if role.name == role_name:
                return role
        raise IAMNotFoundException("Role {0} not found".format(role_name))

    def get_role_by_arn(self, arn):
        for role in self.get_roles():
            if role.arn == arn:
                return role
        raise IAMNotFoundException("Role {0} not found".format(arn))

    def delete_role(self, role_name):
        role = self.get_role(role_name)
        for instance_profile in self.get_instance_profiles():
            for profile_role in instance_profile.roles:
                if profile_role.name == role_name:
                    raise IAMConflictException(
                        code="DeleteConflict",
                        message="Cannot delete entity, must remove roles from instance profile first.",
                    )
        if role.managed_policies:
            raise IAMConflictException(
                code="DeleteConflict",
                message="Cannot delete entity, must detach all policies first.",
            )
        if role.policies:
            raise IAMConflictException(
                code="DeleteConflict",
                message="Cannot delete entity, must delete policies first.",
            )
        del self.roles[role.id]

    def get_roles(self):
        return self.roles.values()

    def put_role_policy(self, role_name, policy_name, policy_json):
        role = self.get_role(role_name)

        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_json)
        iam_policy_document_validator.validate()
        role.put_policy(policy_name, policy_json)

    def delete_role_policy(self, role_name, policy_name):
        role = self.get_role(role_name)
        role.delete_policy(policy_name)

    def get_role_policy(self, role_name, policy_name):
        role = self.get_role(role_name)
        for p, d in role.policies.items():
            if p == policy_name:
                return p, d
        raise IAMNotFoundException(
            "Policy Document {0} not attached to role {1}".format(
                policy_name, role_name
            )
        )

    def list_role_policies(self, role_name):
        role = self.get_role(role_name)
        return role.policies.keys()

    def _tag_verification(self, tags):
        if len(tags) > 50:
            raise TooManyTags(tags)

        tag_keys = {}
        for tag in tags:
            # Need to index by the lowercase tag key since the keys are case insensitive, but their case is retained.
            ref_key = tag["Key"].lower()
            self._check_tag_duplicate(tag_keys, ref_key)
            self._validate_tag_key(tag["Key"])
            if len(tag["Value"]) > 256:
                raise TagValueTooBig(tag["Value"])

            tag_keys[ref_key] = tag

        return tag_keys

    def _validate_tag_key(self, tag_key, exception_param="tags.X.member.key"):
        """Validates the tag key.

        :param tag_key: The tag key to check against.
        :param exception_param: The exception parameter to send over to help format the message. This is to reflect
                                the difference between the tag and untag APIs.
        :return:
        """
        # Validate that the key length is correct:
        if len(tag_key) > 128:
            raise TagKeyTooBig(tag_key, param=exception_param)

        # Validate that the tag key fits the proper Regex:
        # [\w\s_.:/=+\-@]+ SHOULD be the same as the Java regex on the AWS documentation: [\p{L}\p{Z}\p{N}_.:/=+\-@]+
        match = re.findall(r"[\w\s_.:/=+\-@]+", tag_key)
        # Kudos if you can come up with a better way of doing a global search :)
        if not len(match) or len(match[0]) < len(tag_key):
            raise InvalidTagCharacters(tag_key, param=exception_param)

    def _check_tag_duplicate(self, all_tags, tag_key):
        """Validates that a tag key is not a duplicate

        :param all_tags: Dict to check if there is a duplicate tag.
        :param tag_key: The tag key to check against.
        :return:
        """
        if tag_key in all_tags:
            raise DuplicateTags()

    def list_role_tags(self, role_name, marker, max_items=100):
        role = self.get_role(role_name)

        max_items = int(max_items)
        tag_index = sorted(role.tags)
        start_idx = int(marker) if marker else 0

        tag_index = tag_index[start_idx : start_idx + max_items]

        if len(role.tags) <= (start_idx + max_items):
            marker = None
        else:
            marker = str(start_idx + max_items)

        # Make the tag list of dict's:
        tags = [role.tags[tag] for tag in tag_index]

        return tags, marker

    def tag_role(self, role_name, tags):
        clean_tags = self._tag_verification(tags)
        role = self.get_role(role_name)
        role.tags.update(clean_tags)

    def untag_role(self, role_name, tag_keys):
        if len(tag_keys) > 50:
            raise TooManyTags(tag_keys, param="tagKeys")

        role = self.get_role(role_name)

        for key in tag_keys:
            ref_key = key.lower()
            self._validate_tag_key(key, exception_param="tagKeys")

            role.tags.pop(ref_key, None)

    def create_policy_version(self, policy_arn, policy_document, set_as_default):
        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_document)
        iam_policy_document_validator.validate()

        policy = self.get_policy(policy_arn)
        if not policy:
            raise IAMNotFoundException("Policy not found")
        if len(policy.versions) >= 5:
            raise IAMLimitExceededException(
                "A managed policy can have up to 5 versions. Before you create a new version, you must delete an existing version."
            )
        set_as_default = set_as_default == "true"  # convert it to python bool
        version = PolicyVersion(policy_arn, policy_document, set_as_default)
        policy.versions.append(version)
        version.version_id = "v{0}".format(policy.next_version_num)
        policy.next_version_num += 1
        if set_as_default:
            policy.update_default_version(version.version_id)
        return version

    def get_policy_version(self, policy_arn, version_id):
        policy = self.get_policy(policy_arn)
        if not policy:
            raise IAMNotFoundException("Policy not found")
        for version in policy.versions:
            if version.version_id == version_id:
                return version
        raise IAMNotFoundException("Policy version not found")

    def list_policy_versions(self, policy_arn):
        policy = self.get_policy(policy_arn)
        if not policy:
            raise IAMNotFoundException("Policy not found")
        return policy.versions

    def delete_policy_version(self, policy_arn, version_id):
        policy = self.get_policy(policy_arn)
        if not policy:
            raise IAMNotFoundException("Policy not found")
        if version_id == policy.default_version_id:
            raise IAMConflictException(
                code="DeleteConflict",
                message="Cannot delete the default version of a policy.",
            )
        for i, v in enumerate(policy.versions):
            if v.version_id == version_id:
                del policy.versions[i]
                return
        raise IAMNotFoundException("Policy not found")

    def create_instance_profile(self, name, path, role_ids):
        if self.instance_profiles.get(name):
            raise IAMConflictException(
                code="EntityAlreadyExists",
                message="Instance Profile {0} already exists.".format(name),
            )

        instance_profile_id = random_resource_id()

        roles = [iam_backend.get_role_by_id(role_id) for role_id in role_ids]
        instance_profile = InstanceProfile(instance_profile_id, name, path, roles)
        self.instance_profiles[name] = instance_profile
        return instance_profile

    def delete_instance_profile(self, name):
        instance_profile = self.get_instance_profile(name)
        if len(instance_profile.roles) > 0:
            raise IAMConflictException(
                code="DeleteConflict",
                message="Cannot delete entity, must remove roles from instance profile first.",
            )
        del self.instance_profiles[name]

    def get_instance_profile(self, profile_name):
        for profile in self.get_instance_profiles():
            if profile.name == profile_name:
                return profile

        raise IAMNotFoundException(
            "Instance profile {0} not found".format(profile_name)
        )

    def get_instance_profile_by_arn(self, profile_arn):
        for profile in self.get_instance_profiles():
            if profile.arn == profile_arn:
                return profile

        raise IAMNotFoundException("Instance profile {0} not found".format(profile_arn))

    def get_instance_profiles(self):
        return self.instance_profiles.values()

    def get_instance_profiles_for_role(self, role_name):
        found_profiles = []

        for profile in self.get_instance_profiles():
            if len(profile.roles) > 0:
                if profile.roles[0].name == role_name:
                    found_profiles.append(profile)

        return found_profiles

    def add_role_to_instance_profile(self, profile_name, role_name):
        profile = self.get_instance_profile(profile_name)
        role = self.get_role(role_name)
        profile.roles.append(role)

    def remove_role_from_instance_profile(self, profile_name, role_name):
        profile = self.get_instance_profile(profile_name)
        role = self.get_role(role_name)
        profile.roles.remove(role)

    def get_all_server_certs(self, marker=None):
        return self.certificates.values()

    def upload_server_certificate(
        self, cert_name, cert_body, private_key, cert_chain=None, path=None
    ):
        certificate_id = random_resource_id()
        cert = Certificate(cert_name, cert_body, private_key, cert_chain, path)
        self.certificates[certificate_id] = cert
        return cert

    def get_server_certificate(self, name):
        for key, cert in self.certificates.items():
            if name == cert.cert_name:
                return cert

        raise IAMNotFoundException(
            "The Server Certificate with name {0} cannot be " "found.".format(name)
        )

    def delete_server_certificate(self, name):
        cert_id = None
        for key, cert in self.certificates.items():
            if name == cert.cert_name:
                cert_id = key
                break

        if cert_id is None:
            raise IAMNotFoundException(
                "The Server Certificate with name {0} cannot be " "found.".format(name)
            )

        self.certificates.pop(cert_id, None)

    def create_group(self, group_name, path="/"):
        if group_name in self.groups:
            raise IAMConflictException("Group {0} already exists".format(group_name))

        group = Group(group_name, path)
        self.groups[group_name] = group
        return group

    def get_group(self, group_name, marker=None, max_items=None):
        group = None
        try:
            group = self.groups[group_name]
        except KeyError:
            raise IAMNotFoundException("Group {0} not found".format(group_name))

        return group

    def list_groups(self):
        return self.groups.values()

    def get_groups_for_user(self, user_name):
        user = self.get_user(user_name)
        groups = []
        for group in self.list_groups():
            if user in group.users:
                groups.append(group)

        return groups

    def put_group_policy(self, group_name, policy_name, policy_json):
        group = self.get_group(group_name)

        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_json)
        iam_policy_document_validator.validate()
        group.put_policy(policy_name, policy_json)

    def list_group_policies(self, group_name, marker=None, max_items=None):
        group = self.get_group(group_name)
        return group.list_policies()

    def delete_group_policy(self, group_name, policy_name):
        group = self.get_group(group_name)
        group.delete_policy(policy_name)

    def get_group_policy(self, group_name, policy_name):
        group = self.get_group(group_name)
        return group.get_policy(policy_name)

    def delete_group(self, group_name):
        try:
            del self.groups[group_name]
        except KeyError:
            raise IAMNotFoundException(
                "The group with name {0} cannot be found.".format(group_name)
            )

    def create_user(self, user_name, path="/", tags=None):
        if user_name in self.users:
            raise IAMConflictException(
                "EntityAlreadyExists", "User {0} already exists".format(user_name)
            )

        user = User(user_name, path, tags)
        self.users[user_name] = user
        return user

    def get_user(self, user_name):
        user = None
        try:
            user = self.users[user_name]
        except KeyError:
            raise IAMNotFoundException("User {0} not found".format(user_name))

        return user

    def list_users(self, path_prefix, marker, max_items):
        users = None
        try:

            users = self.users.values()
            if path_prefix:
                users = filter_items_with_path_prefix(path_prefix, users)

        except KeyError:
            raise IAMNotFoundException(
                "Users {0}, {1}, {2} not found".format(path_prefix, marker, max_items)
            )

        return users

    def update_user(self, user_name, new_path=None, new_user_name=None):
        try:
            user = self.users[user_name]
        except KeyError:
            raise IAMNotFoundException("User {0} not found".format(user_name))

        if new_path:
            user.path = new_path
        if new_user_name:
            user.name = new_user_name
            self.users[new_user_name] = self.users.pop(user_name)

    def list_roles(self, path_prefix=None, marker=None, max_items=None):
        path_prefix = path_prefix if path_prefix else "/"
        max_items = int(max_items) if max_items else 100
        start_index = int(marker) if marker else 0

        roles = self.roles.values()
        roles = filter_items_with_path_prefix(path_prefix, roles)
        sorted_roles = sorted(roles, key=lambda role: role.id)

        roles_to_return = sorted_roles[start_index : start_index + max_items]

        if len(sorted_roles) <= (start_index + max_items):
            marker = None
        else:
            marker = str(start_index + max_items)

        return roles_to_return, marker

    def upload_signing_certificate(self, user_name, body):
        user = self.get_user(user_name)
        cert_id = random_resource_id(size=32)

        # Validate the signing cert:
        try:
            if sys.version_info < (3, 0):
                data = bytes(body)
            else:
                data = bytes(body, "utf8")

            x509.load_pem_x509_certificate(data, default_backend())

        except Exception:
            raise MalformedCertificate(body)

        user.signing_certificates[cert_id] = SigningCertificate(
            cert_id, user_name, body
        )

        return user.signing_certificates[cert_id]

    def delete_signing_certificate(self, user_name, cert_id):
        user = self.get_user(user_name)

        try:
            del user.signing_certificates[cert_id]
        except KeyError:
            raise IAMNotFoundException(
                "The Certificate with id {id} cannot be found.".format(id=cert_id)
            )

    def list_signing_certificates(self, user_name):
        user = self.get_user(user_name)

        return list(user.signing_certificates.values())

    def update_signing_certificate(self, user_name, cert_id, status):
        user = self.get_user(user_name)

        try:
            user.signing_certificates[cert_id].status = status

        except KeyError:
            raise IAMNotFoundException(
                "The Certificate with id {id} cannot be found.".format(id=cert_id)
            )

    def create_login_profile(self, user_name, password):
        # This does not currently deal with PasswordPolicyViolation.
        user = self.get_user(user_name)
        if user.password:
            raise IAMConflictException(
                "User {0} already has password".format(user_name)
            )
        user.password = password
        return user

    def get_login_profile(self, user_name):
        user = self.get_user(user_name)
        if not user.password:
            raise IAMNotFoundException(
                "Login profile for {0} not found".format(user_name)
            )
        return user

    def update_login_profile(self, user_name, password, password_reset_required):
        # This does not currently deal with PasswordPolicyViolation.
        user = self.get_user(user_name)
        if not user.password:
            raise IAMNotFoundException(
                "Login profile for {0} not found".format(user_name)
            )
        user.password = password
        user.password_reset_required = password_reset_required
        return user

    def delete_login_profile(self, user_name):
        user = self.get_user(user_name)
        if not user.password:
            raise IAMNotFoundException(
                "Login profile for {0} not found".format(user_name)
            )
        user.password = None

    def add_user_to_group(self, group_name, user_name):
        user = self.get_user(user_name)
        group = self.get_group(group_name)
        group.users.append(user)

    def remove_user_from_group(self, group_name, user_name):
        group = self.get_group(group_name)
        user = self.get_user(user_name)
        try:
            group.users.remove(user)
        except ValueError:
            raise IAMNotFoundException(
                "User {0} not in group {1}".format(user_name, group_name)
            )

    def get_user_policy(self, user_name, policy_name):
        user = self.get_user(user_name)
        policy = user.get_policy(policy_name)
        return policy

    def list_user_policies(self, user_name):
        user = self.get_user(user_name)
        return user.policies.keys()

    def list_user_tags(self, user_name):
        user = self.get_user(user_name)
        return user.tags

    def put_user_policy(self, user_name, policy_name, policy_json):
        user = self.get_user(user_name)

        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_json)
        iam_policy_document_validator.validate()
        user.put_policy(policy_name, policy_json)

    def delete_user_policy(self, user_name, policy_name):
        user = self.get_user(user_name)
        user.delete_policy(policy_name)

    def delete_policy(self, policy_arn):
        del self.managed_policies[policy_arn]

    def create_access_key(self, user_name=None, status="Active"):
        user = self.get_user(user_name)
        key = user.create_access_key(status)
        self.access_keys[key.physical_resource_id] = key
        return key

    def update_access_key(self, user_name, access_key_id, status=None):
        user = self.get_user(user_name)
        return user.update_access_key(access_key_id, status)

    def get_access_key_last_used(self, access_key_id):
        access_keys_list = self.get_all_access_keys_for_all_users()
        for key in access_keys_list:
            if key.access_key_id == access_key_id:
                return {"user_name": key.user_name, "last_used": key.last_used_iso_8601}
        else:
            raise IAMNotFoundException(
                "The Access Key with id {0} cannot be found".format(access_key_id)
            )

    def get_all_access_keys_for_all_users(self):
        access_keys_list = []
        for user_name in self.users:
            access_keys_list += self.get_all_access_keys(user_name)
        return access_keys_list

    def get_all_access_keys(self, user_name, marker=None, max_items=None):
        user = self.get_user(user_name)
        keys = user.get_all_access_keys()
        return keys

    def delete_access_key(self, access_key_id, user_name):
        user = self.get_user(user_name)
        access_key = user.get_access_key_by_id(access_key_id)
        self.delete_access_key_by_name(access_key.access_key_id)

    def delete_access_key_by_name(self, name):
        key = self.access_keys[name]
        try:  # User may have been deleted before their access key...
            user = self.get_user(key.user_name)
            user.delete_access_key(key.access_key_id)
        except IAMNotFoundException:
            pass
        del self.access_keys[name]

    def upload_ssh_public_key(self, user_name, ssh_public_key_body):
        user = self.get_user(user_name)
        return user.upload_ssh_public_key(ssh_public_key_body)

    def get_ssh_public_key(self, user_name, ssh_public_key_id):
        user = self.get_user(user_name)
        return user.get_ssh_public_key(ssh_public_key_id)

    def get_all_ssh_public_keys(self, user_name):
        user = self.get_user(user_name)
        return user.get_all_ssh_public_keys()

    def update_ssh_public_key(self, user_name, ssh_public_key_id, status):
        user = self.get_user(user_name)
        return user.update_ssh_public_key(ssh_public_key_id, status)

    def delete_ssh_public_key(self, user_name, ssh_public_key_id):
        user = self.get_user(user_name)
        return user.delete_ssh_public_key(ssh_public_key_id)

    def enable_mfa_device(
        self, user_name, serial_number, authentication_code_1, authentication_code_2
    ):
        """Enable MFA Device for user."""
        user = self.get_user(user_name)
        if serial_number in user.mfa_devices:
            raise IAMConflictException(
                "EntityAlreadyExists", "Device {0} already exists".format(serial_number)
            )

        device = self.virtual_mfa_devices.get(serial_number, None)
        if device:
            device.enable_date = datetime.utcnow()
            device.user = user
            device.user_attribute = {
                "Path": user.path,
                "UserName": user.name,
                "UserId": user.id,
                "Arn": user.arn,
                "CreateDate": user.created_iso_8601,
                "PasswordLastUsed": None,  # not supported
                "PermissionsBoundary": {},  # ToDo: add put_user_permissions_boundary() functionality
                "Tags": {},  # ToDo: add tag_user() functionality
            }

        user.enable_mfa_device(
            serial_number, authentication_code_1, authentication_code_2
        )

    def deactivate_mfa_device(self, user_name, serial_number):
        """Deactivate and detach MFA Device from user if device exists."""
        user = self.get_user(user_name)
        if serial_number not in user.mfa_devices:
            raise IAMNotFoundException("Device {0} not found".format(serial_number))

        device = self.virtual_mfa_devices.get(serial_number, None)
        if device:
            device.enable_date = None
            device.user = None
            device.user_attribute = None

        user.deactivate_mfa_device(serial_number)

    def list_mfa_devices(self, user_name):
        user = self.get_user(user_name)
        return user.mfa_devices.values()

    def create_virtual_mfa_device(self, device_name, path):
        if not path:
            path = "/"

        if not path.startswith("/") and not path.endswith("/"):
            raise ValidationError(
                "The specified value for path is invalid. "
                "It must begin and end with / and contain only alphanumeric characters and/or / characters."
            )

        if any(not len(part) for part in path.split("/")[1:-1]):
            raise ValidationError(
                "The specified value for path is invalid. "
                "It must begin and end with / and contain only alphanumeric characters and/or / characters."
            )

        if len(path) > 512:
            raise ValidationError(
                "1 validation error detected: "
                'Value "{}" at "path" failed to satisfy constraint: '
                "Member must have length less than or equal to 512"
            )

        device = VirtualMfaDevice(path + device_name)

        if device.serial_number in self.virtual_mfa_devices:
            raise EntityAlreadyExists(
                "MFADevice entity at the same path and name already exists."
            )

        self.virtual_mfa_devices[device.serial_number] = device
        return device

    def delete_virtual_mfa_device(self, serial_number):
        device = self.virtual_mfa_devices.pop(serial_number, None)

        if not device:
            raise IAMNotFoundException(
                "VirtualMFADevice with serial number {0} doesn't exist.".format(
                    serial_number
                )
            )

    def list_virtual_mfa_devices(self, assignment_status, marker, max_items):
        devices = list(self.virtual_mfa_devices.values())

        if assignment_status == "Assigned":
            devices = [device for device in devices if device.enable_date]

        if assignment_status == "Unassigned":
            devices = [device for device in devices if not device.enable_date]

        sorted(devices, key=lambda device: device.serial_number)
        max_items = int(max_items)
        start_idx = int(marker) if marker else 0

        if start_idx > len(devices):
            raise ValidationError("Invalid Marker.")

        devices = devices[start_idx : start_idx + max_items]

        if len(devices) < max_items:
            marker = None
        else:
            marker = str(start_idx + max_items)

        return devices, marker

    def delete_user(self, user_name):
        user = self.get_user(user_name)
        if user.managed_policies:
            raise IAMConflictException(
                code="DeleteConflict",
                message="Cannot delete entity, must detach all policies first.",
            )
        if user.policies:
            raise IAMConflictException(
                code="DeleteConflict",
                message="Cannot delete entity, must delete policies first.",
            )
        del self.users[user_name]

    def report_generated(self):
        return self.credential_report

    def generate_report(self):
        self.credential_report = True

    def get_credential_report(self):
        if not self.credential_report:
            raise IAMReportNotPresentException("Credential report not present")
        report = "user,arn,user_creation_time,password_enabled,password_last_used,password_last_changed,password_next_rotation,mfa_active,access_key_1_active,access_key_1_last_rotated,access_key_1_last_used_date,access_key_1_last_used_region,access_key_1_last_used_service,access_key_2_active,access_key_2_last_rotated,access_key_2_last_used_date,access_key_2_last_used_region,access_key_2_last_used_service,cert_1_active,cert_1_last_rotated,cert_2_active,cert_2_last_rotated\n"
        for user in self.users:
            report += self.users[user].to_csv()
        return base64.b64encode(report.encode("ascii")).decode("ascii")

    def list_account_aliases(self):
        return self.account_aliases

    def create_account_alias(self, alias):
        # alias is force updated
        self.account_aliases = [alias]

    def delete_account_alias(self, alias):
        self.account_aliases = []

    def get_account_authorization_details(self, filter):
        policies = self.managed_policies.values()
        local_policies = set(policies) - set(aws_managed_policies)
        returned_policies = []

        if len(filter) == 0:
            return {
                "instance_profiles": self.instance_profiles.values(),
                "roles": self.roles.values(),
                "groups": self.groups.values(),
                "users": self.users.values(),
                "managed_policies": self.managed_policies.values(),
            }

        if "AWSManagedPolicy" in filter:
            returned_policies = aws_managed_policies
        if "LocalManagedPolicy" in filter:
            returned_policies = returned_policies + list(local_policies)

        return {
            "instance_profiles": self.instance_profiles.values(),
            "roles": self.roles.values() if "Role" in filter else [],
            "groups": self.groups.values() if "Group" in filter else [],
            "users": self.users.values() if "User" in filter else [],
            "managed_policies": returned_policies,
        }

    def create_saml_provider(self, name, saml_metadata_document):
        saml_provider = SAMLProvider(name, saml_metadata_document)
        self.saml_providers[name] = saml_provider
        return saml_provider

    def update_saml_provider(self, saml_provider_arn, saml_metadata_document):
        saml_provider = self.get_saml_provider(saml_provider_arn)
        saml_provider.saml_metadata_document = saml_metadata_document
        return saml_provider

    def delete_saml_provider(self, saml_provider_arn):
        try:
            for saml_provider in list(self.list_saml_providers()):
                if saml_provider.arn == saml_provider_arn:
                    del self.saml_providers[saml_provider.name]
        except KeyError:
            raise IAMNotFoundException(
                "SAMLProvider {0} not found".format(saml_provider_arn)
            )

    def list_saml_providers(self):
        return self.saml_providers.values()

    def get_saml_provider(self, saml_provider_arn):
        for saml_provider in self.list_saml_providers():
            if saml_provider.arn == saml_provider_arn:
                return saml_provider
        raise IAMNotFoundException(
            "SamlProvider {0} not found".format(saml_provider_arn)
        )

    def get_user_from_access_key_id(self, access_key_id):
        for user_name, user in self.users.items():
            access_keys = self.get_all_access_keys(user_name)
            for access_key in access_keys:
                if access_key.access_key_id == access_key_id:
                    return user
        return None

    def create_open_id_connect_provider(self, url, thumbprint_list, client_id_list):
        open_id_provider = OpenIDConnectProvider(url, thumbprint_list, client_id_list)

        if open_id_provider.arn in self.open_id_providers:
            raise EntityAlreadyExists("Unknown")

        self.open_id_providers[open_id_provider.arn] = open_id_provider
        return open_id_provider

    def delete_open_id_connect_provider(self, arn):
        self.open_id_providers.pop(arn, None)

    def get_open_id_connect_provider(self, arn):
        open_id_provider = self.open_id_providers.get(arn)

        if not open_id_provider:
            raise IAMNotFoundException(
                "OpenIDConnect Provider not found for arn {}".format(arn)
            )

        return open_id_provider

    def list_open_id_connect_providers(self):
        return list(self.open_id_providers.keys())

    def update_account_password_policy(
        self,
        allow_change_password,
        hard_expiry,
        max_password_age,
        minimum_password_length,
        password_reuse_prevention,
        require_lowercase_characters,
        require_numbers,
        require_symbols,
        require_uppercase_characters,
    ):
        self.account_password_policy = AccountPasswordPolicy(
            allow_change_password,
            hard_expiry,
            max_password_age,
            minimum_password_length,
            password_reuse_prevention,
            require_lowercase_characters,
            require_numbers,
            require_symbols,
            require_uppercase_characters,
        )

    def get_account_password_policy(self):
        if not self.account_password_policy:
            raise NoSuchEntity(
                "The Password Policy with domain name {} cannot be found.".format(
                    ACCOUNT_ID
                )
            )

        return self.account_password_policy

    def delete_account_password_policy(self):
        if not self.account_password_policy:
            raise NoSuchEntity(
                "The account policy with name PasswordPolicy cannot be found."
            )

        self.account_password_policy = None

    def get_account_summary(self):
        return self.account_summary

    def create_inline_policy(
        self,
        resource_name,
        policy_name,
        policy_document,
        group_names,
        role_names,
        user_names,
    ):
        if resource_name in self.inline_policies:
            raise IAMConflictException(
                "EntityAlreadyExists",
                "Inline Policy {0} already exists".format(resource_name),
            )

        inline_policy = InlinePolicy(
            resource_name,
            policy_name,
            policy_document,
            group_names,
            role_names,
            user_names,
        )
        self.inline_policies[resource_name] = inline_policy
        inline_policy.apply_policy(self)
        return inline_policy

    def get_inline_policy(self, policy_id):
        inline_policy = None
        try:
            inline_policy = self.inline_policies[policy_id]
        except KeyError:
            raise IAMNotFoundException("Inline policy {0} not found".format(policy_id))
        return inline_policy

    def update_inline_policy(
        self,
        resource_name,
        policy_name,
        policy_document,
        group_names,
        role_names,
        user_names,
    ):
        inline_policy = self.get_inline_policy(resource_name)
        inline_policy.unapply_policy(self)
        inline_policy.update(
            policy_name, policy_document, group_names, role_names, user_names,
        )
        inline_policy.apply_policy(self)
        return inline_policy

    def delete_inline_policy(self, policy_id):
        inline_policy = self.get_inline_policy(policy_id)
        inline_policy.unapply_policy(self)
        del self.inline_policies[policy_id]


iam_backend = IAMBackend()
