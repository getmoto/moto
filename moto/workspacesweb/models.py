"""WorkSpacesWebBackend class with methods for supported APIs."""

import datetime
import uuid

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.utilities.utils import get_partition

from typing import Dict, Iterable


class FakeNetworkSettings(BaseModel):

    def __init__(
        self,
        security_group_ids,
        subnet_ids,
        tags,
        vpc_id,
        region_name,
        account_id,
    ):
        self.network_settings_id = uuid.uuid4()
        self.arn = self.arn_formatter(
            self.network_settings_id, account_id, region_name)
        self.security_group_ids = security_group_ids
        self.subnet_ids = subnet_ids
        self.tags = tags
        self.vpc_id = vpc_id
        self.associated_portal_arns = []

    def arn_formatter(self, _id, account_id, region_name):
        return f"arn:{get_partition(region_name)}:workspaces-web:{region_name}:{account_id}:network-settings/{_id}"

    def to_dict(self):
        return {
            "associatedPortalArns": self.associated_portal_arns,
            "networkSettingsArn": self.arn,
            "securityGroupIds": self.security_group_ids,
            "subnetIds": self.subnet_ids,
            "Tags": self.tags,
            "vpcId": self.vpc_id,
        }


class WorkSpacesWebBackend(BaseBackend):
    """Implementation of WorkSpacesWeb APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.network_settings: Dict[str, FakeNetworkSettings] = {}

    def create_browser_settings(self, additional_encryption_context, browser_policy, client_token, customer_managed_key, tags):
        # implement here
        return browser_settings_arn

    def list_browser_settings(self, max_results, next_token):
        # implement here
        return browser_settings, next_token

    def get_browser_settings(self, browser_settings_arn):
        # implement here
        return browser_settings

    def delete_browser_settings(self, browser_settings_arn):
        # implement here
        return

    def create_network_settings(self, client_token, security_group_ids, subnet_ids, tags, vpc_id):
        network_settings_object = FakeNetworkSettings(
            security_group_ids, subnet_ids, tags, vpc_id, self.region_name, self.account_id)
        self.network_settings[network_settings_object.arn] = network_settings_object
        return network_settings_object.arn

    def list_network_settings(self, max_results, next_token):
        network_settings_fetched: Iterable[FakeNetworkSettings] = list(
            self.network_settings.values()
        )
        network_settings_summaries = [
            {
                "networkSettingsArn": network_setting.arn,
                "vpcId": network_setting.vpc_id,
            }

            for network_setting in network_settings_fetched
        ]
        return network_settings_summaries, 0

    def get_network_settings(self, network_settings_arn):
        print(self.network_settings)
        return self.network_settings[network_settings_arn].to_dict()

    def delete_network_settings(self, network_settings_arn):
        # implement here
        return

    def create_browser_settings(self, additional_encryption_context, browser_policy, client_token, customer_managed_key, tags):
        # implement here
        return browser_settings_arn

    def list_browser_settings(self, max_results, next_token):
        # implement here
        return browser_settings, next_token

    def get_browser_settings(self, browser_settings_arn):
        # implement here
        return browser_settings

    def delete_browser_settings(self, browser_settings_arn):
        # implement here
        return

    def create_portal(self, additional_encryption_context, authentication_type, client_token, customer_managed_key, display_name, instance_type, max_concurrent_sessions, tags):
        # implement here
        return portal_arn, portal_endpoint

    def list_portals(self, max_results, next_token):
        # implement here
        return next_token, portals

    def get_portal(self, portal_arn):
        # implement here
        return portal

    def delete_portal(self, portal_arn):
        # implement here
        return

    def associate_browser_settings(self, browser_settings_arn, portal_arn):
        # implement here
        return browser_settings_arn, portal_arn

    def associate_network_settings(self, network_settings_arn, portal_arn):
        # implement here
        return network_settings_arn, portal_arn


workspacesweb_backends = BackendDict(WorkSpacesWebBackend, "workspaces-web")
