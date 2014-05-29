from moto.core import BaseBackend

from .utils import random_resource_id


class Role(object):

    def __init__(self, role_id, name, assume_role_policy_document, path, policies):
        self.id = role_id
        self.name = name
        self.assume_role_policy_document = assume_role_policy_document
        self.path = path
        self.policies = policies

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
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


class InstanceProfile(object):
    def __init__(self, instance_profile_id, name, path, roles):
        self.id = instance_profile_id
        self.name = name
        self.path = path
        self.roles = roles if roles else []

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
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


class IAMBackend(BaseBackend):

    def __init__(self):
        self.instance_profiles = {}
        self.roles = {}
        self.certificates = {}
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

iam_backend = IAMBackend()
