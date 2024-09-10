"""Handles incoming workspacesweb requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import workspacesweb_backends


class WorkSpacesWebResponse(BaseResponse):
    """Handler for WorkSpacesWeb requests and responses."""

    def __init__(self):
        super().__init__(service_name="workspaces-web")

    @property
    def workspacesweb_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # workspacesweb_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return workspacesweb_backends[self.current_account][self.region]

    # add methods from here

    def create_browser_settings(self):
        params = self._get_params()
        additional_encryption_context = self._get_param(
            "additionalEncryptionContext")
        browser_policy = self._get_param("browserPolicy")
        client_token = self._get_param("clientToken")
        customer_managed_key = self._get_param("customerManagedKey")
        tags = self._get_param("tags")
        browser_settings_arn = self.workspacesweb_backend.create_browser_settings(
            additional_encryption_context=additional_encryption_context,
            browser_policy=browser_policy,
            client_token=client_token,
            customer_managed_key=customer_managed_key,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(browserSettingsArn=browser_settings_arn))

    def create_network_settings(self):
        client_token = self._get_param("clientToken")
        security_group_ids = self._get_param("securityGroupIds")
        subnet_ids = self._get_param("subnetIds")
        tags = self._get_param("tags")
        vpc_id = self._get_param("vpcId")
        network_settings_arn = self.workspacesweb_backend.create_network_settings(
            client_token=client_token,
            security_group_ids=security_group_ids,
            subnet_ids=subnet_ids,
            tags=tags,
            vpc_id=vpc_id,
        )
        # TODO: adjust response
        return json.dumps(dict(networkSettingsArn=network_settings_arn))

    def get_network_settings(self):
        network_settings_arn = self._get_param("networkSettingsArn")
        network_settings = self.workspacesweb_backend.get_network_settings(
            network_settings_arn=network_settings_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(networkSettings=network_settings))

    def create_portal(self):
        params = self._get_params()
        additional_encryption_context = self._get_param(
            "additionalEncryptionContext")
        authentication_type = self._get_param("authenticationType")
        client_token = self._get_param("clientToken")
        customer_managed_key = self._get_param("customerManagedKey")
        display_name = self._get_param("displayName")
        instance_type = self._get_param("instanceType")
        max_concurrent_sessions = self._get_param("maxConcurrentSessions")
        tags = self._get_param("tags")
        portal_arn, portal_endpoint = self.workspacesweb_backend.create_portal(
            additional_encryption_context=additional_encryption_context,
            authentication_type=authentication_type,
            client_token=client_token,
            customer_managed_key=customer_managed_key,
            display_name=display_name,
            instance_type=instance_type,
            max_concurrent_sessions=max_concurrent_sessions,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(portalArn=portal_arn, portalEndpoint=portal_endpoint))

    def list_browser_settings(self):
        params = self._get_params()
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")
        browser_settings, next_token = self.workspacesweb_backend.list_browser_settings(
            max_results=max_results,
            next_token=next_token,
        )
        # TODO: adjust response
        return json.dumps(dict(browserSettings=browser_settings, nextToken=next_token))

    def list_network_settings(self):
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")
        network_settings, next_token = self.workspacesweb_backend.list_network_settings(
            max_results=max_results,
            next_token=next_token,
        )
        # TODO: adjust response
        return json.dumps(dict(networkSettings=network_settings, nextToken=next_token))

    def list_portals(self):
        params = self._get_params()
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")
        next_token, portals = self.workspacesweb_backend.list_portals(
            max_results=max_results,
            next_token=next_token,
        )
        # TODO: adjust response
        return json.dumps(dict(nextToken=next_token, portals=portals))

    def get_browser_settings(self):
        params = self._get_params()
        browser_settings_arn = self._get_param("browserSettingsArn")
        browser_settings = self.workspacesweb_backend.get_browser_settings(
            browser_settings_arn=browser_settings_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(browserSettings=browser_settings))

    def delete_browser_settings(self):
        params = self._get_params()
        browser_settings_arn = self._get_param("browserSettingsArn")
        self.workspacesweb_backend.delete_browser_settings(
            browser_settings_arn=browser_settings_arn,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def delete_network_settings(self):
        params = self._get_params()
        network_settings_arn = self._get_param("networkSettingsArn")
        self.workspacesweb_backend.delete_network_settings(
            network_settings_arn=network_settings_arn,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def get_portal(self):
        params = self._get_params()
        portal_arn = self._get_param("portalArn")
        portal = self.workspacesweb_backend.get_portal(
            portal_arn=portal_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(portal=portal))

    def get_portal(self):
        params = self._get_params()
        portal_arn = self._get_param("portalArn")
        portal = self.workspacesweb_backend.get_portal(
            portal_arn=portal_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(portal=portal))

    def delete_portal(self):
        params = self._get_params()
        portal_arn = self._get_param("portalArn")
        self.workspacesweb_backend.delete_portal(
            portal_arn=portal_arn,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def associate_browser_settings(self):
        params = self._get_params()
        browser_settings_arn = self._get_param("browserSettingsArn")
        portal_arn = self._get_param("portalArn")
        browser_settings_arn, portal_arn = self.workspacesweb_backend.associate_browser_settings(
            browser_settings_arn=browser_settings_arn,
            portal_arn=portal_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(browserSettingsArn=browser_settings_arn, portalArn=portal_arn))

    def associate_network_settings(self):
        params = self._get_params()
        network_settings_arn = self._get_param("networkSettingsArn")
        portal_arn = self._get_param("portalArn")
        network_settings_arn, portal_arn = self.workspacesweb_backend.associate_network_settings(
            network_settings_arn=network_settings_arn,
            portal_arn=portal_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(networkSettingsArn=network_settings_arn, portalArn=portal_arn))
