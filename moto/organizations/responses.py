from __future__ import unicode_literals
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

    def _get_param(self, param, default=None):
        return self.request_params.get(param, default)

    def create_organization(self):
        return json.dumps(
            self.organizations_backend.create_organization(**self.request_params)
        )

    def describe_organization(self):
        return json.dumps(self.organizations_backend.describe_organization())

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

    def list_accounts(self):
        return json.dumps(self.organizations_backend.list_accounts())

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

    def attach_policy(self):
        return json.dumps(
            self.organizations_backend.attach_policy(**self.request_params)
        )

    def list_policies(self):
        return json.dumps(
            self.organizations_backend.list_policies(**self.request_params)
        )

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
