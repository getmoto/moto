import json

from moto.core.responses import BaseResponse
from .models import organizations_backend


class OrganizationsResponse(BaseResponse):
    @property
    def organizations_backend(self):
        return organizations_backend

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param_name, if_none=None):
        return self.request_params.get(param_name, if_none)

    def create_organization(self):
        return json.dumps(
            self.organizations_backend.create_organization(**self.request_params)
        )

    def describe_organization(self):
        return json.dumps(self.organizations_backend.describe_organization())

    def delete_organization(self):
        return json.dumps(self.organizations_backend.delete_organization())

    def list_roots(self):
        return json.dumps(self.organizations_backend.list_roots())

    def create_organizational_unit(self):
        return json.dumps(
            self.organizations_backend.create_organizational_unit(**self.request_params)
        )

    def update_organizational_unit(self):
        return json.dumps(
            self.organizations_backend.update_organizational_unit(**self.request_params)
        )

    def describe_organizational_unit(self):
        return json.dumps(
            self.organizations_backend.describe_organizational_unit(
                **self.request_params
            )
        )

    def list_organizational_units_for_parent(self):
        return json.dumps(
            self.organizations_backend.list_organizational_units_for_parent(
                **self.request_params
            )
        )

    def list_parents(self):
        return json.dumps(
            self.organizations_backend.list_parents(**self.request_params)
        )

    def create_account(self):
        return json.dumps(
            self.organizations_backend.create_account(**self.request_params)
        )

    def describe_account(self):
        return json.dumps(
            self.organizations_backend.describe_account(**self.request_params)
        )

    def describe_create_account_status(self):
        return json.dumps(
            self.organizations_backend.describe_create_account_status(
                **self.request_params
            )
        )

    def list_create_account_status(self):
        return json.dumps(
            self.organizations_backend.list_create_account_status(**self.request_params)
        )

    def list_accounts(self):
        max_results = self._get_int_param("MaxResults")
        next_token = self._get_param("NextToken")
        accounts, next_token = self.organizations_backend.list_accounts(
            max_results=max_results, next_token=next_token
        )
        response = {"Accounts": accounts}
        if next_token:
            response["NextToken"] = next_token
        return json.dumps(response)

    def list_accounts_for_parent(self):
        return json.dumps(
            self.organizations_backend.list_accounts_for_parent(**self.request_params)
        )

    def move_account(self):
        return json.dumps(
            self.organizations_backend.move_account(**self.request_params)
        )

    def list_children(self):
        return json.dumps(
            self.organizations_backend.list_children(**self.request_params)
        )

    def create_policy(self):
        return json.dumps(
            self.organizations_backend.create_policy(**self.request_params)
        )

    def describe_policy(self):
        return json.dumps(
            self.organizations_backend.describe_policy(**self.request_params)
        )

    def update_policy(self):
        return json.dumps(
            self.organizations_backend.update_policy(**self.request_params)
        )

    def attach_policy(self):
        return json.dumps(
            self.organizations_backend.attach_policy(**self.request_params)
        )

    def list_policies(self):
        return json.dumps(self.organizations_backend.list_policies())

    def delete_policy(self):
        self.organizations_backend.delete_policy(**self.request_params)
        return json.dumps({})

    def list_policies_for_target(self):
        return json.dumps(
            self.organizations_backend.list_policies_for_target(**self.request_params)
        )

    def list_targets_for_policy(self):
        return json.dumps(
            self.organizations_backend.list_targets_for_policy(**self.request_params)
        )

    def tag_resource(self):
        return json.dumps(
            self.organizations_backend.tag_resource(**self.request_params)
        )

    def list_tags_for_resource(self):
        return json.dumps(
            self.organizations_backend.list_tags_for_resource(**self.request_params)
        )

    def untag_resource(self):
        return json.dumps(
            self.organizations_backend.untag_resource(**self.request_params)
        )

    def enable_aws_service_access(self):
        return json.dumps(
            self.organizations_backend.enable_aws_service_access(**self.request_params)
        )

    def list_aws_service_access_for_organization(self):
        return json.dumps(
            self.organizations_backend.list_aws_service_access_for_organization()
        )

    def disable_aws_service_access(self):
        return json.dumps(
            self.organizations_backend.disable_aws_service_access(**self.request_params)
        )

    def register_delegated_administrator(self):
        return json.dumps(
            self.organizations_backend.register_delegated_administrator(
                **self.request_params
            )
        )

    def list_delegated_administrators(self):
        return json.dumps(
            self.organizations_backend.list_delegated_administrators(
                **self.request_params
            )
        )

    def list_delegated_services_for_account(self):
        return json.dumps(
            self.organizations_backend.list_delegated_services_for_account(
                **self.request_params
            )
        )

    def deregister_delegated_administrator(self):
        return json.dumps(
            self.organizations_backend.deregister_delegated_administrator(
                **self.request_params
            )
        )

    def enable_policy_type(self):
        return json.dumps(
            self.organizations_backend.enable_policy_type(**self.request_params)
        )

    def disable_policy_type(self):
        return json.dumps(
            self.organizations_backend.disable_policy_type(**self.request_params)
        )

    def detach_policy(self):
        return json.dumps(
            self.organizations_backend.detach_policy(**self.request_params)
        )

    def remove_account_from_organization(self):
        return json.dumps(
            self.organizations_backend.remove_account_from_organization(
                **self.request_params
            )
        )
