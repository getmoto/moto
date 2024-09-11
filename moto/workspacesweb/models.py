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


class FakeBrowserSettings(BaseModel):
    def __init__(
        self,
        additional_encryption_context,
        browser_policy,
        client_token,
        customer_managed_key,
        tags,
        region_name,
        account_id,
    ):
        self.browser_settings_id = uuid.uuid4()
        self.arn = self.arn_formatter(
            self.browser_settings_id, account_id, region_name)
        self.additional_encryption_context = additional_encryption_context
        self.browser_policy = browser_policy
        self.client_token = client_token
        self.customer_managed_key = customer_managed_key
        self.tags = tags
        self.associated_portal_arns = []

    def arn_formatter(self, _id, account_id, region_name):
        return f"arn:{get_partition(region_name)}:workspaces-web:{region_name}:{account_id}:browser-settings/{_id}"

    def to_dict(self):
        return {
            "associatedPortalArns": self.associated_portal_arns,
            "browserSettingsArn": self.arn,
            "additionalEncryptionContext": self.additional_encryption_context,
            "browserPolicy": self.browser_policy,
            "customerManagedKey": self.customer_managed_key,
            "tags": self.tags,
        }


class FakePortal(BaseModel):
    def __init__(
        self,
        additional_encryption_context,
        authentication_type,
        client_token,
        customer_managed_key,
        display_name,
        instance_type,
        max_concurrent_sessions,
        tags,
        region_name,
        account_id,
    ):
        self.portal_id = uuid.uuid4()
        self.arn = self.arn_formatter(
            self.portal_id, account_id, region_name)
        self.additional_encryption_context = additional_encryption_context
        self.authentication_type = authentication_type
        self.client_token = client_token
        self.customer_managed_key = customer_managed_key
        self.display_name = display_name
        self.instance_type = instance_type
        self.max_concurrent_sessions = max_concurrent_sessions
        self.tags = tags
        self.portal_endpoint = f"{self.portal_id}.portal.aws"
        self.browser_type = "Chrome"
        self.creation_time = datetime.datetime.now().isoformat()
        self.status = "CREATED"
        self.renderer_type = "AppStream"
        self.status_reason = "TestStatusReason"
        self.browser_settings_arn = None
        self.network_settings_arn = None
        self.trust_store_arn = None
        self.ip_access_settings_arn = None
        self.user_access_logging_settings_arn = None
        self.user_settings_arn = None

    def arn_formatter(self, _id, account_id, region_name):
        return f"arn:{get_partition(region_name)}:workspaces-web:{region_name}:{account_id}:portal/{_id}"

    def to_dict(self):
        return {
            "associatedBrowserSettingsArn": self.associated_browser_settings_arn,
            "associatedNetworkSettingsArn": self.associated_network_settings_arn,
            "portalArn": self.arn,
            "additionalEncryptionContext": self.additional_encryption_context,
            "authenticationType": self.authentication_type,
            "clientToken": self.client_token,
            "customerManagedKey": self.customer_managed_key,
            "displayName": self.display_name,
            "instanceType": self.instance_type,
            "maxConcurrentSessions": self.max_concurrent_sessions,
            "tags": self.tags,
        }


class WorkSpacesWebBackend(BaseBackend):
    """Implementation of WorkSpacesWeb APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.network_settings: Dict[str, FakeNetworkSettings] = {}
        self.browser_settings: Dict[str, FakeBrowserSettings] = {}
        self.portals: Dict[str, FakePortal] = {}

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
        return self.network_settings[network_settings_arn].to_dict()

    def delete_network_settings(self, network_settings_arn):
        # implement here
        return

    def create_browser_settings(self, additional_encryption_context, browser_policy, client_token, customer_managed_key, tags):
        browser_settings_object = FakeBrowserSettings(
            additional_encryption_context, browser_policy, client_token, customer_managed_key, tags, self.region_name, self.account_id)
        self.browser_settings[browser_settings_object.arn] = browser_settings_object
        return browser_settings_object.arn

    def list_browser_settings(self, max_results, next_token):
        browser_settings_fetched: Iterable[FakeBrowserSettings] = list(
            self.browser_settings.values()
        )
        browser_settings_summaries = [
            {
                "browserSettingsArn": browser_setting.arn,
            }

            for browser_setting in browser_settings_fetched
        ]
        return browser_settings_summaries, 0

    def get_browser_settings(self, browser_settings_arn):
        # implement here
        return browser_settings

    def delete_browser_settings(self, browser_settings_arn):
        # implement here
        return

    def create_portal(self, additional_encryption_context, authentication_type, client_token, customer_managed_key, display_name, instance_type, max_concurrent_sessions, tags):
        portal_object = FakePortal(
            additional_encryption_context, authentication_type, client_token, customer_managed_key, display_name, instance_type, max_concurrent_sessions, tags, self.region_name, self.account_id)
        self.portals[portal_object.arn] = portal_object
        return portal_object.arn, portal_object.portal_endpoint

    def list_portals(self, max_results, next_token):
        portals_fetched: Iterable[FakePortal] = list(
            self.portals.values()
        )

        portal_summaries = [
            {
                "authenticationType": portal.authentication_type,
                "browserSettingsArn": portal.browser_settings_arn,
                "browserType": portal.browser_type,
                "creationDate": portal.creation_time,
                "customerManagedKey": portal.customer_managed_key,
                "displayName": portal.display_name,
                "instanceType": portal.instance_type,
                "ipAccessSettingsArn": portal.ip_access_settings_arn,
                "maxConcurrentSessions": portal.max_concurrent_sessions,
                "networkSettingsArn": portal.network_settings_arn,
                "portalArn": portal.arn,
                "portalEndpoint": portal.portal_endpoint,
                "portalStatus": portal.status,
                "rendererType": portal.renderer_type,
                "statusReason": portal.status_reason,
                "trustStoreArn": portal.trust_store_arn,
                "userAccessLoggingSettingsArn": portal.user_access_logging_settings_arn,
                "userSettingsArn": portal.user_settings_arn,
            }
            for portal in portals_fetched

        ]
        return 0, portal_summaries

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
