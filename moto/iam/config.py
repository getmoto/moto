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
        # Stored in moto backend with the AWS-assigned random string like "AROA0BSVNSZKXVHS00SBJ"

        # Grab roles from backend; need the full values since names and id's are different
        role_list = list(self.backends["global"].roles.values())

        if not role_list:
            return [], None

        # Filter by resource name or ids
        if resource_name or resource_ids:
            filtered_roles = []
            # resource_name takes precendence over resource_ids
            if resource_name:
                for role in role_list:
                    if role.name == resource_name:
                        filtered_roles = [role]
                        break
            else:
                for role in role_list:
                    if role.id in resource_ids:
                        filtered_roles.append(role)

            # Filtered roles are now the subject for the listing
            role_list = filtered_roles

        # Pagination logic, sort by role id
        sorted_roles = sorted(role_list, key=lambda role: role.id)
        # sorted_role_ids matches indicies of sorted_roles
        sorted_role_ids = list(map(lambda role: role.id, sorted_roles))
        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            if next_token not in sorted_role_ids:
                raise InvalidNextTokenException()

            start = sorted_role_ids.index(next_token)

        # Get the list of items to collect:
        role_list = sorted_roles[start : (start + limit)]

        if len(sorted_roles) > (start + limit):
            new_token = sorted_role_ids[start + limit]

        return (
            [
                {
                    "type": "AWS::IAM::Role",
                    "id": role.id,
                    "name": role.name,
                    "region": "global",
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
        # Stored in moto backend with the arn like "arn:aws:iam::123456789012:policy/my-development-policy"

        policy_list = list(self.backends["global"].managed_policies.values())

        # We don't want to include AWS Managed Policies. This technically needs to
        # respect the configuration recorder's 'includeGlobalResourceTypes' setting,
        # but it's default set be default, and moto's config doesn't yet support
        # custom configuration recorders, we'll just behave as default.
        policy_list = filter(
            lambda policy: not policy.arn.startswith("arn:aws:iam::aws"), policy_list,
        )

        if not policy_list:
            return [], None

        # Filter by resource name or ids
        if resource_name or resource_ids:
            filtered_policies = []
            # resource_name takes precendence over resource_ids
            if resource_name:
                for policy in policy_list:
                    if policy.name == resource_name:
                        filtered_policies = [policy]
                        break
            else:
                for policy in policy_list:
                    if policy.id in resource_ids:
                        filtered_policies.append(policy)

            # Filtered roles are now the subject for the listing
            policy_list = filtered_policies

        # Pagination logic, sort by role id
        sorted_policies = sorted(policy_list, key=lambda role: role.id)
        # sorted_policy_ids matches indicies of sorted_policies
        sorted_policy_ids = list(map(lambda policy: policy.id, sorted_policies))

        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            if next_token not in sorted_policy_ids:
                raise InvalidNextTokenException()

            start = sorted_policy_ids.index(next_token)

        # Get the list of items to collect:
        policy_list = sorted_policies[start : (start + limit)]

        if len(sorted_policies) > (start + limit):
            new_token = sorted_policy_ids[start + limit]

        return (
            [
                {
                    "type": "AWS::IAM::Policy",
                    "id": policy.id,
                    "name": policy.name,
                    "region": "global",
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
