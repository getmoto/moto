import json
import boto3
from typing import Any, Dict, List, Optional, Tuple
from moto.core.exceptions import InvalidNextTokenException
from moto.core.common_models import ConfigQueryModel
from moto.iam import iam_backends


class RoleConfigQuery(ConfigQueryModel):
    def list_config_service_resources(
        self,
        account_id: str,
        resource_ids: Optional[List[str]],
        resource_name: Optional[str],
        limit: int,
        next_token: Optional[str],
        backend_region: Optional[str] = None,
        resource_region: Optional[str] = None,
        aggregator: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        # IAM roles are "global" and aren't assigned into any availability zone
        # The resource ID is a AWS-assigned random string like "AROA0BSVNSZKXVHS00SBJ"
        # The resource name is a user-assigned string like "MyDevelopmentAdminRole"
        # Stored in moto backend with the AWS-assigned random string like "AROA0BSVNSZKXVHS00SBJ"

        # Grab roles from backend; need the full values since names and id's are different
        role_list = list(self.backends[account_id]["global"].roles.values())

        if not role_list:
            return [], None

        # Filter by resource name or ids
        if resource_name or resource_ids:
            filtered_roles = []
            # resource_name takes precedence over resource_ids
            if resource_name:
                for role in role_list:
                    if role.name == resource_name:
                        filtered_roles = [role]
                        break
                # but if both are passed, it must be a subset
                if filtered_roles and resource_ids:
                    if filtered_roles[0].id not in resource_ids:
                        return [], None
            else:
                for role in role_list:
                    if role.id in resource_ids:  # type: ignore[operator]
                        filtered_roles.append(role)

            # Filtered roles are now the subject for the listing
            role_list = filtered_roles

        if aggregator:
            # IAM is a little special; Roles are created in us-east-1 (which AWS calls the "global" region)
            # However, the resource will return in the aggregator (in duplicate) for each region in the aggregator
            # Therefore, we'll need to find out the regions where the aggregators are running, and then duplicate the resource there

            # In practice, it looks like AWS will only duplicate these resources if you've "used" any roles in the region, but since
            # we can't really tell if this has happened in moto, we'll just bind this to the regions in your aggregator
            aggregated_regions = []
            aggregator_sources = aggregator.get(
                "account_aggregation_sources"
            ) or aggregator.get("organization_aggregation_source")
            for source in aggregator_sources:  # type: ignore[union-attr]
                source_dict = source.__dict__
                if source_dict.get("all_aws_regions", False):
                    aggregated_regions = boto3.Session().get_available_regions("config")
                    break
                for region in source_dict.get("aws_regions", []):
                    aggregated_regions.append(region)

            duplicate_role_list = []
            for region in list(set(aggregated_regions)):
                for role in role_list:
                    duplicate_role_list.append(
                        {
                            "_id": f"{role.id}{region}",  # this is only for sorting, isn't returned outside of this function
                            "type": "AWS::IAM::Role",
                            "id": role.id,
                            "name": role.name,
                            "region": region,
                        }
                    )

            # Pagination logic, sort by role id
            sorted_roles = sorted(duplicate_role_list, key=lambda role: role["_id"])
        else:
            # Non-aggregated queries are in the else block, and we can treat these like a normal config resource
            # Pagination logic, sort by role id
            sorted_roles = sorted(role_list, key=lambda role: role.id)  # type: ignore[attr-defined]

        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            try:
                # Find the index of the next
                start = next(
                    index
                    for (index, r) in enumerate(sorted_roles)
                    if next_token == (r["_id"] if aggregator else r.id)  # type: ignore[attr-defined]
                )
            except StopIteration:
                raise InvalidNextTokenException()

        # Get the list of items to collect:
        role_list = sorted_roles[start : (start + limit)]

        if len(sorted_roles) > (start + limit):
            record = sorted_roles[start + limit]
            new_token = record["_id"] if aggregator else record.id  # type: ignore[attr-defined]

        return (
            [
                {
                    "type": "AWS::IAM::Role",
                    "id": role["id"] if aggregator else role.id,  # type: ignore[attr-defined]
                    "name": role["name"] if aggregator else role.name,  # type: ignore[attr-defined]
                    "region": role["region"] if aggregator else "global",
                }
                for role in role_list
            ],
            new_token,
        )

    def get_config_resource(
        self,
        account_id: str,
        resource_id: str,
        resource_name: Optional[str] = None,
        backend_region: Optional[str] = None,
        resource_region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        role = self.backends[account_id]["global"].roles.get(resource_id, {})

        if not role:
            return None

        if resource_name and role.name != resource_name:
            return None

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
        account_id: str,
        resource_ids: Optional[List[str]],
        resource_name: Optional[str],
        limit: int,
        next_token: Optional[str],
        backend_region: Optional[str] = None,
        resource_region: Optional[str] = None,
        aggregator: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        # IAM policies are "global" and aren't assigned into any availability zone
        # The resource ID is a AWS-assigned random string like "ANPA0BSVNSZK00SJSPVUJ"
        # The resource name is a user-assigned string like "my-development-policy"
        # Stored in moto backend with the arn like "arn:aws:iam::123456789012:policy/my-development-policy"

        policy_list = list(
            self.backends[account_id]["global"].managed_policies.values()
        )

        # We don't want to include AWS Managed Policies. This technically needs to
        # respect the configuration recorder's 'includeGlobalResourceTypes' setting,
        # but it's default set be default, and moto's config doesn't yet support
        # custom configuration recorders, we'll just behave as default.
        policy_list = list(
            filter(
                lambda policy: not policy.arn.startswith("arn:aws:iam::aws"),
                policy_list,
            )
        )

        if not policy_list:
            return [], None

        # Filter by resource name or ids
        if resource_name or resource_ids:
            filtered_policies = []
            # resource_name takes precedence over resource_ids
            if resource_name:
                for policy in policy_list:
                    if policy.name == resource_name:
                        filtered_policies = [policy]
                        break
                # but if both are passed, it must be a subset
                if filtered_policies and resource_ids:
                    if filtered_policies[0].id not in resource_ids:
                        return [], None

            else:
                for policy in policy_list:
                    if policy.id in resource_ids:  # type: ignore[operator]
                        filtered_policies.append(policy)

            # Filtered roles are now the subject for the listing
            policy_list = filtered_policies

        if aggregator:
            # IAM is a little special; Policies are created in us-east-1 (which AWS calls the "global" region)
            # However, the resource will return in the aggregator (in duplicate) for each region in the aggregator
            # Therefore, we'll need to find out the regions where the aggregators are running, and then duplicate the resource there

            # In practice, it looks like AWS will only duplicate these resources if you've "used" any policies in the region, but since
            # we can't really tell if this has happened in moto, we'll just bind this to the regions in your aggregator
            aggregated_regions = []
            aggregator_sources = aggregator.get(
                "account_aggregation_sources"
            ) or aggregator.get("organization_aggregation_source")
            for source in aggregator_sources:  # type: ignore[union-attr]
                source_dict = source.__dict__
                if source_dict.get("all_aws_regions", False):
                    aggregated_regions = boto3.Session().get_available_regions("config")
                    break
                for region in source_dict.get("aws_regions", []):
                    aggregated_regions.append(region)

            duplicate_policy_list = []
            for region in list(set(aggregated_regions)):
                for policy in policy_list:
                    duplicate_policy_list.append(
                        {
                            "_id": f"{policy.id}{region}",  # this is only for sorting, isn't returned outside of this function
                            "type": "AWS::IAM::Policy",
                            "id": policy.id,
                            "name": policy.name,
                            "region": region,
                        }
                    )

            # Pagination logic, sort by role id
            sorted_policies = sorted(
                duplicate_policy_list, key=lambda policy: policy["_id"]
            )

        else:
            # Non-aggregated queries are in the else block, and we can treat these like a normal config resource
            # Pagination logic, sort by role id
            sorted_policies = sorted(policy_list, key=lambda role: role.id)  # type: ignore[attr-defined]

        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            try:
                # Find the index of the next
                start = next(
                    index
                    for (index, p) in enumerate(sorted_policies)
                    if next_token == (p["_id"] if aggregator else p.id)  # type: ignore[attr-defined]
                )
            except StopIteration:
                raise InvalidNextTokenException()

        # Get the list of items to collect:
        policy_list = sorted_policies[start : (start + limit)]

        if len(sorted_policies) > (start + limit):
            record = sorted_policies[start + limit]
            new_token = record["_id"] if aggregator else record.id  # type: ignore[attr-defined]

        return (
            [
                {
                    "type": "AWS::IAM::Policy",
                    "id": policy["id"] if aggregator else policy.id,  # type: ignore[attr-defined]
                    "name": policy["name"] if aggregator else policy.name,  # type: ignore[attr-defined]
                    "region": policy["region"] if aggregator else "global",
                }
                for policy in policy_list
            ],
            new_token,
        )

    def get_config_resource(
        self,
        account_id: str,
        resource_id: str,
        resource_name: Optional[str] = None,
        backend_region: Optional[str] = None,
        resource_region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        # policies are listed in the backend as arns, but we have to accept the PolicyID as the resource_id
        # we'll make a really crude search for it
        policy = None
        for arn in self.backends[account_id]["global"].managed_policies.keys():
            policy_candidate = self.backends[account_id]["global"].managed_policies[arn]
            if policy_candidate.id == resource_id:
                policy = policy_candidate
                break

        if not policy:
            return None

        if resource_name and policy.name != resource_name:
            return None

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
