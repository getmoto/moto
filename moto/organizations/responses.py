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
        return json.dumps(
            self.organizations_backend.describe_organization()
        )

    def create_account(self):
        return json.dumps(
            self.organizations_backend.create_account(**self.request_params)
        )

    def describe_account(self):
        return json.dumps(
            self.organizations_backend.describe_account(**self.request_params)
        )

    def list_accounts(self):
        return json.dumps(
            self.organizations_backend.list_accounts()
        )
