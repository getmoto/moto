import json

from moto.core.exceptions import InvalidNextTokenException
from moto.core.models import ConfigQueryModel
from moto.iam import iam_backends

CONFIG_BACKEND_DELIM = "\x1e"  # Record Seperator "RS" ASCII Character


class RoleConfigQuery(ConfigQueryModel):
    def list_config_service_resources(
        self,
        resource_ids,
        resource_name,
        limit,
        next_token,
        backend_region=None,
        resource_region=None,
    ):
        # IAM roles are "global" and aren't assigned into any availability zone
        # The resource ID is a AWS-assigned random string like "AROA0BSVNSZKXVHS00SBJ"
        # The resource name is a user-assigned string like "MyDevelopmentAdminRole"

        # Grab roles from backend
        role_list = self.aggregate_regions("roles", "global", None)

        if not role_list:
            return [], None

        # Pagination logic
        sorted_roles = sorted(role_list)
        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            # "Tokens" are region + \x1e + resource ID.
            if next_token not in sorted_roles:
                raise InvalidNextTokenException()

            start = sorted_roles.index(next_token)

        # Get the list of items to collect:
        role_list = sorted_roles[start : (start + limit)]

        if len(sorted_roles) > (start + limit):
            new_token = sorted_roles[start + limit]

        # Each element is a string of "region\x1eresource_id"
        return (
            [
                {
                    "type": "AWS::IAM::Role",
                    "id": role.split(CONFIG_BACKEND_DELIM)[1],
                    "name": self.backends["global"]
                    .roles[role.split(CONFIG_BACKEND_DELIM)[1]]
                    .name,
                    "region": role.split(CONFIG_BACKEND_DELIM)[0],
                }
                for role in role_list
            ],
            new_token,
        )

    def get_config_resource(
        self, resource_id, resource_name=None, backend_region=None, resource_region=None
    ):

        role = self.backends["global"].roles.get(resource_id, {})

        if not role:
            return

        if resource_name and role.name != resource_name:
            return

        # Format the role to the AWS Config format:
        config_data = role.to_config_dict()

        # The 'configuration' field is also a JSON string:
        config_data["configuration"] = json.dumps(config_data["configuration"])

        # Supplementary config need all values converted to JSON strings if they are not strings already:
        for field, value in config_data["supplementaryConfiguration"].items():
            if not isinstance(value, str):
                config_data["supplementaryConfiguration"][field] = json.dumps(value)

        return config_data


class PolicyConfigQuery(ConfigQueryModel):
    def list_config_service_resources(
        self,
        resource_ids,
        resource_name,
        limit,
        next_token,
        backend_region=None,
        resource_region=None,
    ):
        # IAM policies are "global" and aren't assigned into any availability zone
        # The resource ID is a AWS-assigned random string like "ANPA0BSVNSZK00SJSPVUJ"
        # The resource name is a user-assigned string like "my-development-policy"

        # We don't want to include AWS Managed Policies. This technically needs to
        # respect the configuration recorder's 'includeGlobalResourceTypes' setting,
        # but it's default set be default, and moto's config doesn't yet support
        # custom configuration recorders, we'll just behave as default.
        policy_list = filter(
            lambda policy: not policy.split(CONFIG_BACKEND_DELIM)[1].startswith(
                "arn:aws:iam::aws"
            ),
            self.aggregate_regions("managed_policies", "global", None),
        )

        if not policy_list:
            return [], None

        # Pagination logic:
        sorted_policies = sorted(policy_list)
        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            # "Tokens" are region + \x1e + resource ID.
            if next_token not in sorted_policies:
                raise InvalidNextTokenException()

            start = sorted_policies.index(next_token)

        # Get the list of items to collect:
        policy_list = sorted_policies[start : (start + limit)]

        if len(sorted_policies) > (start + limit):
            new_token = sorted_policies[start + limit]

        return (
            [
                {
                    "type": "AWS::IAM::Policy",
                    "id": self.backends["global"]
                    .managed_policies[policy.split(CONFIG_BACKEND_DELIM)[1]]
                    .id,
                    "name": self.backends["global"]
                    .managed_policies[policy.split(CONFIG_BACKEND_DELIM)[1]]
                    .name,
                    "region": policy.split(CONFIG_BACKEND_DELIM)[0],
                }
                for policy in policy_list
            ],
            new_token,
        )

    def get_config_resource(
        self, resource_id, resource_name=None, backend_region=None, resource_region=None
    ):
        # policies are listed in the backend as arns, but we have to accept the PolicyID as the resource_id
        # we'll make a really crude search for it
        policy = None
        for arn in self.backends["global"].managed_policies.keys():
            policy_candidate = self.backends["global"].managed_policies[arn]
            if policy_candidate.id == resource_id:
                policy = policy_candidate
                break

        if not policy:
            return

        if resource_name and policy.name != resource_name:
            return

        # Format the policy to the AWS Config format:
        config_data = policy.to_config_dict()

        # The 'configuration' field is also a JSON string:
        config_data["configuration"] = json.dumps(config_data["configuration"])

        # Supplementary config need all values converted to JSON strings if they are not strings already:
        for field, value in config_data["supplementaryConfiguration"].items():
            if not isinstance(value, str):
                config_data["supplementaryConfiguration"][field] = json.dumps(value)

        return config_data


role_config_query = RoleConfigQuery(iam_backends)
policy_config_query = PolicyConfigQuery(iam_backends)
