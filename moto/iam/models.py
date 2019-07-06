from __future__ import unicode_literals
import base64
import sys
from datetime import datetime
import json
import re

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from moto.core.exceptions import RESTError
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_without_milliseconds, iso_8601_datetime_with_milliseconds
from moto.iam.policy_validation import IAMPolicyDocumentValidator

from .aws_managed_policies import aws_managed_policies_data
from .exceptions import IAMNotFoundException, IAMConflictException, IAMReportNotPresentException, MalformedCertificate, \
    DuplicateTags, TagKeyTooBig, InvalidTagCharacters, TooManyTags, TagValueTooBig
from .utils import random_access_key, random_alphanumeric, random_resource_id, random_policy_id

ACCOUNT_ID = 123456789012


class MFADevice(object):
    """MFA Device class."""

    def __init__(self,
                 serial_number,
                 authentication_code_1,
                 authentication_code_2):
        self.enable_date = datetime.utcnow()
        self.serial_number = serial_number
        self.authentication_code_1 = authentication_code_1
        self.authentication_code_2 = authentication_code_2

    @property
    def enabled_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.enable_date)


class Policy(BaseModel):
    is_attachable = False

    def __init__(self,
                 name,
                 default_version_id=None,
                 description=None,
                 document=None,
                 path=None,
                 create_date=None,
                 update_date=None):
        self.name = name

        self.attachment_count = 0
        self.description = description or ''
        self.id = random_policy_id()
        self.path = path or '/'

        if default_version_id:
            self.default_version_id = default_version_id
            self.next_version_num = int(default_version_id.lstrip('v')) + 1
        else:
            self.default_version_id = 'v1'
            self.next_version_num = 2
        self.versions = [PolicyVersion(self.arn, document, True, self.default_version_id, update_date)]

        self.create_date = create_date if create_date is not None else datetime.utcnow()
        self.update_date = update_date if update_date is not None else datetime.utcnow()

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


class PolicyVersion(object):

    def __init__(self,
                 policy_arn,
                 document,
                 is_default=False,
                 version_id='v1',
                 create_date=None):
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


class AWSManagedPolicy(ManagedPolicy):
    """AWS-managed policy."""

    @classmethod
    def from_data(cls, name, data):
        return cls(name,
                   default_version_id=data.get('DefaultVersionId'),
                   path=data.get('Path'),
                   document=json.dumps(data.get('Document')),
                   create_date=datetime.strptime(data.get('CreateDate'), "%Y-%m-%dT%H:%M:%S+00:00"),
                   update_date=datetime.strptime(data.get('UpdateDate'), "%Y-%m-%dT%H:%M:%S+00:00"))

    @property
    def arn(self):
        return 'arn:aws:iam::aws:policy{0}{1}'.format(self.path, self.name)


# AWS defines some of its own managed policies and we periodically
# import them via `make aws_managed_policies`
aws_managed_policies = [
    AWSManagedPolicy.from_data(name, d) for name, d
    in json.loads(aws_managed_policies_data).items()]


class InlinePolicy(Policy):
    """TODO: is this needed?"""


class Role(BaseModel):

    def __init__(self, role_id, name, assume_role_policy_document, path, permissions_boundary):
        self.id = role_id
        self.name = name
        self.assume_role_policy_document = assume_role_policy_document
        self.path = path or '/'
        self.policies = {}
        self.managed_policies = {}
        self.create_date = datetime.utcnow()
        self.tags = {}
        self.description = ""
        self.permissions_boundary = permissions_boundary

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        role = iam_backend.create_role(
            role_name=resource_name,
            assume_role_policy_document=properties['AssumeRolePolicyDocument'],
            path=properties.get('Path', '/'),
            permissions_boundary=properties.get('PermissionsBoundary', '')
        )

        policies = properties.get('Policies', [])
        for policy in policies:
            policy_name = policy['PolicyName']
            policy_json = policy['PolicyDocument']
            role.put_policy(policy_name, policy_json)

        return role

    @property
    def arn(self):
        return "arn:aws:iam::{0}:role{1}{2}".format(ACCOUNT_ID, self.path, self.name)

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def delete_policy(self, policy_name):
        try:
            del self.policies[policy_name]
        except KeyError:
            raise IAMNotFoundException(
                "The role policy with name {0} cannot be found.".format(policy_name))

    @property
    def physical_resource_id(self):
        return self.id

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()

    def get_tags(self):
        return [self.tags[tag] for tag in self.tags]


class InstanceProfile(BaseModel):

    def __init__(self, instance_profile_id, name, path, roles):
        self.id = instance_profile_id
        self.name = name
        self.path = path or '/'
        self.roles = roles if roles else []
        self.create_date = datetime.utcnow()

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_with_milliseconds(self.create_date)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        role_ids = properties['Roles']
        return iam_backend.create_instance_profile(
            name=resource_name,
            path=properties.get('Path', '/'),
            role_ids=role_ids,
        )

    @property
    def arn(self):
        return "arn:aws:iam::{0}:instance-profile{1}{2}".format(ACCOUNT_ID, self.path, self.name)

    @property
    def physical_resource_id(self):
        return self.name

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            return self.arn
        raise UnformattedGetAttTemplateException()


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
        return "arn:aws:iam::{0}:server-certificate{1}{2}".format(ACCOUNT_ID, self.path, self.cert_name)


class SigningCertificate(BaseModel):

    def __init__(self, id, user_name, body):
        self.id = id
        self.user_name = user_name
        self.body = body
        self.upload_date = datetime.utcnow()
        self.status = 'Active'

    @property
    def uploaded_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.upload_date)


class AccessKey(BaseModel):

    def __init__(self, user_name):
        self.user_name = user_name
        self.access_key_id = "AKIA" + random_access_key()
        self.secret_access_key = random_alphanumeric(40)
        self.status = 'Active'
        self.create_date = datetime.utcnow()
        self.last_used = datetime.utcnow()

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.create_date)

    @property
    def last_used_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.last_used)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'SecretAccessKey':
            return self.secret_access_key
        raise UnformattedGetAttTemplateException()


class Group(BaseModel):

    def __init__(self, name, path='/'):
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
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()

    @property
    def arn(self):
        if self.path == '/':
            return "arn:aws:iam::{0}:group/{1}".format(ACCOUNT_ID, self.name)

        else:
            return "arn:aws:iam::{0}:group/{1}/{2}".format(ACCOUNT_ID, self.path, self.name)

    def get_policy(self, policy_name):
        try:
            policy_json = self.policies[policy_name]
        except KeyError:
            raise IAMNotFoundException("Policy {0} not found".format(policy_name))

        return {
            'policy_name': policy_name,
            'policy_document': policy_json,
            'group_name': self.name,
        }

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def list_policies(self):
        return self.policies.keys()


class User(BaseModel):

    def __init__(self, name, path=None):
        self.name = name
        self.id = random_resource_id()
        self.path = path if path else "/"
        self.create_date = datetime.utcnow()
        self.mfa_devices = {}
        self.policies = {}
        self.managed_policies = {}
        self.access_keys = []
        self.password = None
        self.password_reset_required = False
        self.signing_certificates = {}

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
            raise IAMNotFoundException(
                "Policy {0} not found".format(policy_name))

        return {
            'policy_name': policy_name,
            'policy_document': policy_json,
            'user_name': self.name,
        }

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def deactivate_mfa_device(self, serial_number):
        self.mfa_devices.pop(serial_number)

    def delete_policy(self, policy_name):
        if policy_name not in self.policies:
            raise IAMNotFoundException(
                "Policy {0} not found".format(policy_name))

        del self.policies[policy_name]

    def create_access_key(self):
        access_key = AccessKey(self.name)
        self.access_keys.append(access_key)
        return access_key

    def enable_mfa_device(self,
                          serial_number,
                          authentication_code_1,
                          authentication_code_2):
        self.mfa_devices[serial_number] = MFADevice(
            serial_number,
            authentication_code_1,
            authentication_code_2
        )

    def get_all_access_keys(self):
        return self.access_keys

    def delete_access_key(self, access_key_id):
        key = self.get_access_key_by_id(access_key_id)
        self.access_keys.remove(key)

    def update_access_key(self, access_key_id, status):
        key = self.get_access_key_by_id(access_key_id)
        key.status = status

    def get_access_key_by_id(self, access_key_id):
        for key in self.access_keys:
            if key.access_key_id == access_key_id:
                return key
        else:
            raise IAMNotFoundException(
                "The Access Key with id {0} cannot be found".format(access_key_id))

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()

    def to_csv(self):
        date_format = '%Y-%m-%dT%H:%M:%S+00:00'
        date_created = self.create_date
        # aagrawal,arn:aws:iam::509284790694:user/aagrawal,2014-09-01T22:28:48+00:00,true,2014-11-12T23:36:49+00:00,2014-09-03T18:59:00+00:00,N/A,false,true,2014-09-01T22:28:48+00:00,false,N/A,false,N/A,false,N/A
        if not self.password:
            password_enabled = 'false'
            password_last_used = 'not_supported'
        else:
            password_enabled = 'true'
            password_last_used = 'no_information'

        if len(self.access_keys) == 0:
            access_key_1_active = 'false'
            access_key_1_last_rotated = 'N/A'
            access_key_2_active = 'false'
            access_key_2_last_rotated = 'N/A'
        elif len(self.access_keys) == 1:
            access_key_1_active = 'true'
            access_key_1_last_rotated = date_created.strftime(date_format)
            access_key_2_active = 'false'
            access_key_2_last_rotated = 'N/A'
        else:
            access_key_1_active = 'true'
            access_key_1_last_rotated = date_created.strftime(date_format)
            access_key_2_active = 'true'
            access_key_2_last_rotated = date_created.strftime(date_format)

        return '{0},{1},{2},{3},{4},{5},not_supported,false,{6},{7},{8},{9},false,N/A,false,N/A'.format(self.name,
                                                                                                        self.arn,
                                                                                                        date_created.strftime(
                                                                                                            date_format),
                                                                                                        password_enabled,
                                                                                                        password_last_used,
                                                                                                        date_created.strftime(
                                                                                                            date_format),
                                                                                                        access_key_1_active,
                                                                                                        access_key_1_last_rotated,
                                                                                                        access_key_2_active,
                                                                                                        access_key_2_last_rotated
                                                                                                        )


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
        self.policy_arn_regex = re.compile(
            r'^arn:aws:iam::[0-9]*:policy/.*$')
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

    def update_role(self, role_name, role_description):
        role = self.get_role(role_name)
        role.description = role_description
        return role

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
            policy_name,
            description=description,
            document=policy_document,
            path=path,
        )
        self.managed_policies[policy.arn] = policy
        return policy

    def get_policy(self, policy_arn):
        if policy_arn not in self.managed_policies:
            raise IAMNotFoundException("Policy {0} not found".format(policy_arn))
        return self.managed_policies.get(policy_arn)

    def list_attached_role_policies(self, role_name, marker=None, max_items=100, path_prefix='/'):
        policies = self.get_role(role_name).managed_policies.values()
        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def list_attached_group_policies(self, group_name, marker=None, max_items=100, path_prefix='/'):
        policies = self.get_group(group_name).managed_policies.values()
        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def list_attached_user_policies(self, user_name, marker=None, max_items=100, path_prefix='/'):
        policies = self.get_user(user_name).managed_policies.values()
        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def list_policies(self, marker, max_items, only_attached, path_prefix, scope):
        policies = self.managed_policies.values()

        if only_attached:
            policies = [p for p in policies if p.attachment_count > 0]

        if scope == 'AWS':
            policies = [p for p in policies if isinstance(p, AWSManagedPolicy)]
        elif scope == 'Local':
            policies = [p for p in policies if not isinstance(
                p, AWSManagedPolicy)]

        return self._filter_attached_policies(policies, marker, max_items, path_prefix)

    def _filter_attached_policies(self, policies, marker, max_items, path_prefix):
        if path_prefix:
            policies = [p for p in policies if p.path.startswith(path_prefix)]

        policies = sorted(policies, key=lambda policy: policy.name)
        start_idx = int(marker) if marker else 0

        policies = policies[start_idx:start_idx + max_items]

        if len(policies) < max_items:
            marker = None
        else:
            marker = str(start_idx + max_items)

        return policies, marker

    def create_role(self, role_name, assume_role_policy_document, path, permissions_boundary):
        role_id = random_resource_id()
        if permissions_boundary and not self.policy_arn_regex.match(permissions_boundary):
            raise RESTError('InvalidParameterValue', 'Value ({}) for parameter PermissionsBoundary is invalid.'.format(permissions_boundary))

        role = Role(role_id, role_name, assume_role_policy_document, path, permissions_boundary)
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
        for role in self.get_roles():
            if role.name == role_name:
                del self.roles[role.id]
                return
        raise IAMNotFoundException("Role {0} not found".format(role_name))

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

    def list_role_policies(self, role_name):
        role = self.get_role(role_name)
        return role.policies.keys()

    def _validate_tag_key(self, tag_key, exception_param='tags.X.member.key'):
        """Validates the tag key.

        :param all_tags: Dict to check if there is a duplicate tag.
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
        match = re.findall(r'[\w\s_.:/=+\-@]+', tag_key)
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

        tag_index = tag_index[start_idx:start_idx + max_items]

        if len(role.tags) <= (start_idx + max_items):
            marker = None
        else:
            marker = str(start_idx + max_items)

        # Make the tag list of dict's:
        tags = [role.tags[tag] for tag in tag_index]

        return tags, marker

    def tag_role(self, role_name, tags):
        if len(tags) > 50:
            raise TooManyTags(tags)

        role = self.get_role(role_name)

        tag_keys = {}
        for tag in tags:
            # Need to index by the lowercase tag key since the keys are case insensitive, but their case is retained.
            ref_key = tag['Key'].lower()
            self._check_tag_duplicate(tag_keys, ref_key)
            self._validate_tag_key(tag['Key'])
            if len(tag['Value']) > 256:
                raise TagValueTooBig(tag['Value'])

            tag_keys[ref_key] = tag

        role.tags.update(tag_keys)

    def untag_role(self, role_name, tag_keys):
        if len(tag_keys) > 50:
            raise TooManyTags(tag_keys, param='tagKeys')

        role = self.get_role(role_name)

        for key in tag_keys:
            ref_key = key.lower()
            self._validate_tag_key(key, exception_param='tagKeys')

            role.tags.pop(ref_key, None)

    def create_policy_version(self, policy_arn, policy_document, set_as_default):
        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_document)
        iam_policy_document_validator.validate()

        policy = self.get_policy(policy_arn)
        if not policy:
            raise IAMNotFoundException("Policy not found")

        version = PolicyVersion(policy_arn, policy_document, set_as_default)
        policy.versions.append(version)
        version.version_id = 'v{0}'.format(policy.next_version_num)
        policy.next_version_num += 1
        if set_as_default:
            policy.default_version_id = version.version_id
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
                "Cannot delete the default version of a policy")
        for i, v in enumerate(policy.versions):
            if v.version_id == version_id:
                del policy.versions[i]
                return
        raise IAMNotFoundException("Policy not found")

    def create_instance_profile(self, name, path, role_ids):
        instance_profile_id = random_resource_id()

        roles = [iam_backend.get_role_by_id(role_id) for role_id in role_ids]
        instance_profile = InstanceProfile(
            instance_profile_id, name, path, roles)
        self.instance_profiles[instance_profile_id] = instance_profile
        return instance_profile

    def get_instance_profile(self, profile_name):
        for profile in self.get_instance_profiles():
            if profile.name == profile_name:
                return profile

        raise IAMNotFoundException(
            "Instance profile {0} not found".format(profile_name))

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

    def upload_server_cert(self, cert_name, cert_body, private_key, cert_chain=None, path=None):
        certificate_id = random_resource_id()
        cert = Certificate(cert_name, cert_body, private_key, cert_chain, path)
        self.certificates[certificate_id] = cert
        return cert

    def get_server_certificate(self, name):
        for key, cert in self.certificates.items():
            if name == cert.cert_name:
                return cert

        raise IAMNotFoundException(
            "The Server Certificate with name {0} cannot be "
            "found.".format(name))

    def delete_server_certificate(self, name):
        cert_id = None
        for key, cert in self.certificates.items():
            if name == cert.cert_name:
                cert_id = key
                break

        if cert_id is None:
            raise IAMNotFoundException(
                "The Server Certificate with name {0} cannot be "
                "found.".format(name))

        self.certificates.pop(cert_id, None)

    def create_group(self, group_name, path='/'):
        if group_name in self.groups:
            raise IAMConflictException(
                "Group {0} already exists".format(group_name))

        group = Group(group_name, path)
        self.groups[group_name] = group
        return group

    def get_group(self, group_name, marker=None, max_items=None):
        group = None
        try:
            group = self.groups[group_name]
        except KeyError:
            raise IAMNotFoundException(
                "Group {0} not found".format(group_name))

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

    def get_group_policy(self, group_name, policy_name):
        group = self.get_group(group_name)
        return group.get_policy(policy_name)

    def create_user(self, user_name, path='/'):
        if user_name in self.users:
            raise IAMConflictException(
                "EntityAlreadyExists", "User {0} already exists".format(user_name))

        user = User(user_name, path)
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
        except KeyError:
            raise IAMNotFoundException(
                "Users {0}, {1}, {2} not found".format(path_prefix, marker, max_items))

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

    def list_roles(self, path_prefix, marker, max_items):
        roles = None
        try:
            roles = self.roles.values()
        except KeyError:
            raise IAMNotFoundException(
                "Users {0}, {1}, {2} not found".format(path_prefix, marker, max_items))

        return roles

    def upload_signing_certificate(self, user_name, body):
        user = self.get_user(user_name)
        cert_id = random_resource_id(size=32)

        # Validate the signing cert:
        try:
            if sys.version_info < (3, 0):
                data = bytes(body)
            else:
                data = bytes(body, 'utf8')

            x509.load_pem_x509_certificate(data, default_backend())

        except Exception:
            raise MalformedCertificate(body)

        user.signing_certificates[cert_id] = SigningCertificate(cert_id, user_name, body)

        return user.signing_certificates[cert_id]

    def delete_signing_certificate(self, user_name, cert_id):
        user = self.get_user(user_name)

        try:
            del user.signing_certificates[cert_id]
        except KeyError:
            raise IAMNotFoundException("The Certificate with id {id} cannot be found.".format(id=cert_id))

    def list_signing_certificates(self, user_name):
        user = self.get_user(user_name)

        return list(user.signing_certificates.values())

    def update_signing_certificate(self, user_name, cert_id, status):
        user = self.get_user(user_name)

        try:
            user.signing_certificates[cert_id].status = status

        except KeyError:
            raise IAMNotFoundException("The Certificate with id {id} cannot be found.".format(id=cert_id))

    def create_login_profile(self, user_name, password):
        # This does not currently deal with PasswordPolicyViolation.
        user = self.get_user(user_name)
        if user.password:
            raise IAMConflictException(
                "User {0} already has password".format(user_name))
        user.password = password
        return user

    def get_login_profile(self, user_name):
        user = self.get_user(user_name)
        if not user.password:
            raise IAMNotFoundException(
                "Login profile for {0} not found".format(user_name))
        return user

    def update_login_profile(self, user_name, password, password_reset_required):
        # This does not currently deal with PasswordPolicyViolation.
        user = self.get_user(user_name)
        if not user.password:
            raise IAMNotFoundException(
                "Login profile for {0} not found".format(user_name))
        user.password = password
        user.password_reset_required = password_reset_required
        return user

    def delete_login_profile(self, user_name):
        user = self.get_user(user_name)
        if not user.password:
            raise IAMNotFoundException(
                "Login profile for {0} not found".format(user_name))
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
                "User {0} not in group {1}".format(user_name, group_name))

    def get_user_policy(self, user_name, policy_name):
        user = self.get_user(user_name)
        policy = user.get_policy(policy_name)
        return policy

    def list_user_policies(self, user_name):
        user = self.get_user(user_name)
        return user.policies.keys()

    def put_user_policy(self, user_name, policy_name, policy_json):
        user = self.get_user(user_name)

        iam_policy_document_validator = IAMPolicyDocumentValidator(policy_json)
        iam_policy_document_validator.validate()
        user.put_policy(policy_name, policy_json)

    def delete_user_policy(self, user_name, policy_name):
        user = self.get_user(user_name)
        user.delete_policy(policy_name)

    def create_access_key(self, user_name=None):
        user = self.get_user(user_name)
        key = user.create_access_key()
        return key

    def update_access_key(self, user_name, access_key_id, status):
        user = self.get_user(user_name)
        user.update_access_key(access_key_id, status)

    def get_access_key_last_used(self, access_key_id):
        access_keys_list = self.get_all_access_keys_for_all_users()
        for key in access_keys_list:
            if key.access_key_id == access_key_id:
                return {
                    'user_name': key.user_name,
                    'last_used': key.last_used_iso_8601,
                }
        else:
            raise IAMNotFoundException(
                "The Access Key with id {0} cannot be found".format(access_key_id))

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
        user.delete_access_key(access_key_id)

    def enable_mfa_device(self,
                          user_name,
                          serial_number,
                          authentication_code_1,
                          authentication_code_2):
        """Enable MFA Device for user."""
        user = self.get_user(user_name)
        if serial_number in user.mfa_devices:
            raise IAMConflictException(
                "EntityAlreadyExists",
                "Device {0} already exists".format(serial_number)
            )

        user.enable_mfa_device(
            serial_number,
            authentication_code_1,
            authentication_code_2
        )

    def deactivate_mfa_device(self, user_name, serial_number):
        """Deactivate and detach MFA Device from user if device exists."""
        user = self.get_user(user_name)
        if serial_number not in user.mfa_devices:
            raise IAMNotFoundException(
                "Device {0} not found".format(serial_number)
            )

        user.deactivate_mfa_device(serial_number)

    def list_mfa_devices(self, user_name):
        user = self.get_user(user_name)
        return user.mfa_devices.values()

    def delete_user(self, user_name):
        try:
            del self.users[user_name]
        except KeyError:
            raise IAMNotFoundException("User {0} not found".format(user_name))

    def report_generated(self):
        return self.credential_report

    def generate_report(self):
        self.credential_report = True

    def get_credential_report(self):
        if not self.credential_report:
            raise IAMReportNotPresentException("Credential report not present")
        report = 'user,arn,user_creation_time,password_enabled,password_last_used,password_last_changed,password_next_rotation,mfa_active,access_key_1_active,access_key_1_last_rotated,access_key_2_active,access_key_2_last_rotated,cert_1_active,cert_1_last_rotated,cert_2_active,cert_2_last_rotated\n'
        for user in self.users:
            report += self.users[user].to_csv()
        return base64.b64encode(report.encode('ascii')).decode('ascii')

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
                'instance_profiles': self.instance_profiles.values(),
                'roles': self.roles.values(),
                'groups': self.groups.values(),
                'users': self.users.values(),
                'managed_policies': self.managed_policies.values()
            }

        if 'AWSManagedPolicy' in filter:
            returned_policies = aws_managed_policies
        if 'LocalManagedPolicy' in filter:
            returned_policies = returned_policies + list(local_policies)

        return {
            'instance_profiles': self.instance_profiles.values(),
            'roles': self.roles.values() if 'Role' in filter else [],
            'groups': self.groups.values() if 'Group' in filter else [],
            'users': self.users.values() if 'User' in filter else [],
            'managed_policies': returned_policies
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
                "SAMLProvider {0} not found".format(saml_provider_arn))

    def list_saml_providers(self):
        return self.saml_providers.values()

    def get_saml_provider(self, saml_provider_arn):
        for saml_provider in self.list_saml_providers():
            if saml_provider.arn == saml_provider_arn:
                return saml_provider
        raise IAMNotFoundException("SamlProvider {0} not found".format(saml_provider_arn))


iam_backend = IAMBackend()
