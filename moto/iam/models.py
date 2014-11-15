from __future__ import unicode_literals

from boto.exception import BotoServerError
from moto.core import BaseBackend
from .utils import random_access_key, random_alphanumeric, random_resource_id
from datetime import datetime


class Role(object):

    def __init__(self, role_id, name, assume_role_policy_document, path, policies):
        self.id = role_id
        self.name = name
        self.assume_role_policy_document = assume_role_policy_document
        self.path = path
        self.policies = policies

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        return iam_backend.create_role(
            role_name=resource_name,
            assume_role_policy_document=properties['AssumeRolePolicyDocument'],
            path=properties['Path'],
            policies=properties.get('Policies', []),
        )

    @property
    def physical_resource_id(self):
        return self.id

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()


class InstanceProfile(object):
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
            path=properties['Path'],
            role_ids=role_ids,
        )

    @property
    def physical_resource_id(self):
        return self.name

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()


class Certificate(object):
    def __init__(self, cert_name, cert_body, private_key, cert_chain=None, path=None):
        self.cert_name = cert_name
        self.cert_body = cert_body
        self.private_key = private_key
        self.path = path
        self.cert_chain = cert_chain

    @property
    def physical_resource_id(self):
        return self.name


class AccessKey(object):
    def __init__(self, user_name):
        self.user_name = user_name
        self.access_key_id = random_access_key()
        self.secret_access_key = random_alphanumeric(32)
        self.status = 'Active'
        self.create_date = datetime.strftime(
            datetime.utcnow(),
            "%Y-%m-%d-%H-%M-%S"
        )

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'SecretAccessKey':
            return self.secret_access_key
        raise UnformattedGetAttTemplateException()


class Group(object):
    def __init__(self, name, path='/'):
        self.name = name
        self.id = random_resource_id()
        self.path = path
        self.created = datetime.strftime(
            datetime.utcnow(),
            "%Y-%m-%d-%H-%M-%S"
        )

        self.users = []

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()


class User(object):
    def __init__(self, name, path='/'):
        self.name = name
        self.id = random_resource_id()
        self.path = path
        self.created = datetime.strftime(
            datetime.utcnow(),
            "%Y-%m-%d-%H-%M-%S"
        )

        self.policies = {}
        self.access_keys = []
        self.password = None

    def get_policy(self, policy_name):
        policy_json = None
        try:
            policy_json = self.policies[policy_name]
        except:
            raise BotoServerError(404, 'Not Found')

        return {
            'policy_name': policy_name,
            'policy_document': policy_json,
            'user_name': self.name,
        }

    def put_policy(self, policy_name, policy_json):
        self.policies[policy_name] = policy_json

    def delete_policy(self, policy_name):
        if policy_name not in self.policies:
            raise BotoServerError(404, 'Not Found')

        del self.policies[policy_name]

    def create_access_key(self):
        access_key = AccessKey(self.name)
        self.access_keys.append(access_key)
        return access_key

    def get_all_access_keys(self):
        return self.access_keys

    def delete_access_key(self, access_key_id):
        for key in self.access_keys:
            if key.access_key_id == access_key_id:
                self.access_keys.remove(key)
                break
        else:
            raise BotoServerError(404, 'Not Found')

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "Arn" ]"')
        raise UnformattedGetAttTemplateException()


class IAMBackend(BaseBackend):

    def __init__(self):
        self.instance_profiles = {}
        self.roles = {}
        self.certificates = {}
        self.groups = {}
        self.users = {}
        super(IAMBackend, self).__init__()

    def create_role(self, role_name, assume_role_policy_document, path, policies):
        role_id = random_resource_id()
        role = Role(role_id, role_name, assume_role_policy_document, path, policies)
        self.roles[role_id] = role
        return role

    def get_role_by_id(self, role_id):
        return self.roles.get(role_id)

    def get_role(self, role_name):
        for role in self.get_roles():
            if role.name == role_name:
                return role

    def get_roles(self):
        return self.roles.values()

    def create_instance_profile(self, name, path, role_ids):
        instance_profile_id = random_resource_id()

        roles = [iam_backend.get_role_by_id(role_id) for role_id in role_ids]
        instance_profile = InstanceProfile(instance_profile_id, name, path, roles)
        self.instance_profiles[instance_profile_id] = instance_profile
        return instance_profile

    def get_instance_profile(self, profile_name):
        for profile in self.get_instance_profiles():
            if profile.name == profile_name:
                return profile

    def get_instance_profiles(self):
        return self.instance_profiles.values()

    def add_role_to_instance_profile(self, profile_name, role_name):
        profile = self.get_instance_profile(profile_name)
        role = self.get_role(role_name)
        profile.roles.append(role)

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

    def create_group(self, group_name, path='/'):
        if group_name in self.groups:
            raise BotoServerError(409, 'Conflict')

        group = Group(group_name, path)
        self.groups[group_name] = group
        return group

    def get_group(self, group_name, marker=None, max_items=None):
        group = None
        try:
            group = self.groups[group_name]
        except KeyError:
            raise BotoServerError(404, 'Not Found')

        return group

    def create_user(self, user_name, path='/'):
        if user_name in self.users:
            raise BotoServerError(409, 'Conflict')

        user = User(user_name, path)
        self.users[user_name] = user
        return user

    def get_user(self, user_name):
        user = None
        try:
            user = self.users[user_name]
        except KeyError:
            raise BotoServerError(404, 'Not Found')

        return user

    def create_login_profile(self, user_name, password):
        if user_name not in self.users:
            raise BotoServerError(404, 'Not Found')

        # This does not currently deal with PasswordPolicyViolation.
        user = self.users[user_name]
        if user.password:
            raise BotoServerError(409, 'Conflict')
        user.password = password

    def add_user_to_group(self, group_name, user_name):
        group = None
        user = None

        try:
            group = self.groups[group_name]
            user = self.users[user_name]
        except KeyError:
            raise BotoServerError(404, 'Not Found')

        group.users.append(user)

    def remove_user_from_group(self, group_name, user_name):
        group = None
        user = None

        try:
            group = self.groups[group_name]
            user = self.users[user_name]
            group.users.remove(user)
        except (KeyError, ValueError):
            raise BotoServerError(404, 'Not Found')

    def get_user_policy(self, user_name, policy_name):
        policy = None
        try:
            user = self.users[user_name]
            policy = user.get_policy(policy_name)
        except KeyError:
            raise BotoServerError(404, 'Not Found')

        return policy

    def put_user_policy(self, user_name, policy_name, policy_json):
        try:
            user = self.users[user_name]
            user.put_policy(policy_name, policy_json)
        except KeyError:
            raise BotoServerError(404, 'Not Found')

    def delete_user_policy(self, user_name, policy_name):
        try:
            user = self.users[user_name]
            user.delete_policy(policy_name)
        except KeyError:
            raise BotoServerError(404, 'Not Found')

    def create_access_key(self, user_name=None):
        key = None
        try:
            user = self.users[user_name]
            key = user.create_access_key()
        except KeyError:
            raise BotoServerError(404, 'Not Found')

        return key

    def get_all_access_keys(self, user_name, marker=None, max_items=None):
        keys = None
        try:
            user = self.users[user_name]
            keys = user.get_all_access_keys()
        except KeyError:
            raise BotoServerError(404, 'Not Found')

        return keys

    def delete_access_key(self, access_key_id, user_name):
        try:
            user = self.users[user_name]
            user.delete_access_key(access_key_id)
        except KeyError:
            raise BotoServerError(404, 'Not Found')

    def delete_user(self, user_name):
        try:
            del self.users[user_name]
        except KeyError:
            raise BotoServerError(404, 'Not Found')


iam_backend = IAMBackend()
