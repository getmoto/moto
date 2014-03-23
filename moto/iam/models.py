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
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, resources_map):
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
        self.roles = roles if roles else {}

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, resources_map):
        properties = cloudformation_json['Properties']

        roles = {}
        for role_ref in properties['Roles']:
            role = resources_map[role_ref['Ref']]
            roles[role.name] = role

        return iam_backend.create_instance_profile(
            name=resource_name,
            path=properties['Path'],
            roles=roles,
        )

    @property
    def physical_resource_id(self):
        return self.id


class IAMBackend(BaseBackend):

    def __init__(self):
        self.instance_profiles = {}
        self.roles = {}
        super(IAMBackend, self).__init__()

    def create_role(self, role_name, assume_role_policy_document, path, policies):
        role_id = random_resource_id()
        role = Role(role_id, role_name, assume_role_policy_document, path, policies)
        self.roles[role_id] = role
        return role

    def get_role(self, role_name):
        for role in self.get_roles():
            if role.name == role_name:
                return role

    def get_roles(self):
        return self.roles.values()

    def create_instance_profile(self, name, path, roles):
        instance_profile_id = random_resource_id()
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
        profile.roles[role.id] = role

iam_backend = IAMBackend()
