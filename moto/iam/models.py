from __future__ import unicode_literals
import base64
from datetime import datetime
import json

import pytz
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_without_milliseconds

from .aws_managed_policies import aws_managed_policies_data
from .exceptions import IAMNotFoundException, IAMConflictException, IAMReportNotPresentException
from .utils import random_access_key, random_alphanumeric, random_resource_id, random_policy_id

ACCOUNT_ID = 123456789012


class MFADevice(object):
    """MFA Device class."""

    def __init__(self,
                 serial_number,
                 authentication_code_1,
                 authentication_code_2):
        self.enable_date = datetime.now(pytz.utc)
        self.serial_number = serial_number
        self.authentication_code_1 = authentication_code_1
        self.authentication_code_2 = authentication_code_2


class Policy(BaseModel):

    is_attachable = False

    def __init__(self,
                 name,
                 default_version_id=None,
                 description=None,
                 document=None,
                 path=None):
        self.name = name

        self.attachment_count = 0
        self.description = description or ''
        self.id = random_policy_id()
        self.path = path or '/'
        self.default_version_id = default_version_id or 'v1'
        self.versions = [PolicyVersion(self.arn, document, True)]

        self.create_datetime = datetime.now(pytz.utc)
        self.update_datetime = datetime.now(pytz.utc)


class PolicyVersion(object):

    def __init__(self,
                 policy_arn,
                 document,
                 is_default=False):
        self.policy_arn = policy_arn
        self.document = document or {}
        self.is_default = is_default
        self.version_id = 'v1'

        self.create_datetime = datetime.now(pytz.utc)


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
                   document=data.get('Document'))

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

    def __init__(self, role_id, name, assume_role_policy_document, path):
        self.id = role_id
        self.name = name
        self.assume_role_policy_document = assume_role_policy_document
        self.path = path
        self.policies = {}
        self.managed_policies = {}

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        role = iam_backend.create_role(
            role_name=resource_name,
            assume_role_policy_document=properties['AssumeRolePolicyDocument'],
            path=properties.get('Path', '/'),
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


class InstanceProfile(BaseModel):

    def __init__(self, instance_profile_id, name, path, roles):
        self.id = instance_profile_id
        self.name = name
        self.path = path
        self.roles = roles if roles else []

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
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
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


class AccessKey(BaseModel):

    def __init__(self, user_name):
        self.user_name = user_name
        self.access_key_id = random_access_key()
        self.secret_access_key = random_alphanumeric(32)
        self.status = 'Active'
        self.create_date = datetime.strftime(
            datetime.utcnow(),
            "%Y-%m-%dT%H:%M:%SZ"
        )

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
        self.created = datetime.strftime(
            datetime.utcnow(),
            "%Y-%m-%d-%H-%M-%S"
        )

        self.users = []
        self.managed_policies = {}
        self.policies = {}

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

    @property
    def create_date(self):
        return self.created

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
        self.created = datetime.utcnow()
        self.mfa_devices = {}
        self.policies = {}
        self.managed_policies = {}
        self.access_keys = []
        self.password = None
        self.password_reset_required = False

    @property
    def arn(self):
        return "arn:aws:iam::{0}:user{1}{2}".format(ACCOUNT_ID, self.path, self.name)

    @property
    def created_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.created)

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
        for key in self.access_keys:
            if key.access_key_id == access_key_id:
                self.access_keys.remove(key)
                break
        else:
            raise IAMNotFoundException(
                "Key {0} not found".format(access_key_id))

    def update_access_key(self, access_key_id, status):
        for key in self.access_keys:
            if key.access_key_id == access_key_id:
                key.status = status
                break
        else:
            raise IAMNotFoundException("The Access Key with id {0} cannot be found".format(access_key_id))

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()

    def to_csv(self):
        date_format = '%Y-%m-%dT%H:%M:%S+00:00'
        date_created = self.created
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
        super(IAMBackend, self).__init__()

    def _init_managed_policies(self):
        return dict((p.name, p) for p in aws_managed_policies)

    def attach_role_policy(self, policy_arn, role_name):
        arns = dict((p.arn, p) for p in self.managed_policies.values())
        policy = arns[policy_arn]
        policy.attach_to(self.get_role(role_name))

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

    def create_role(self, role_name, assume_role_policy_document, path):
        role_id = random_resource_id()
        role = Role(role_id, role_name, assume_role_policy_document, path)
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

    def create_policy_version(self, policy_arn, policy_document, set_as_default):
        policy = self.get_policy(policy_arn)
        if not policy:
            raise IAMNotFoundException("Policy not found")
        version = PolicyVersion(policy_arn, policy_document, set_as_default)
        policy.versions.append(version)
        version.version_id = 'v{0}'.format(len(policy.versions))
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


iam_backend = IAMBackend()
