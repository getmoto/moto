"""Handles incoming networkfirewall requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import networkfirewall_backends


class NetworkFirewallResponse(BaseResponse):
    """Handler for NetworkFirewall requests and responses."""

    def __init__(self):
        super().__init__(service_name="networkfirewall")

    @property
    def networkfirewall_backend(self):
        """Return backend instance specific for this region."""
        return networkfirewall_backends[self.current_account][self.region]

    def create_firewall(self):
        params = self._get_params()
        firewall_name = self._get_param("FirewallName")
        firewall_policy_arn = self._get_param("FirewallPolicyArn")
        vpc_id = params.get("VpcId")
        subnet_mappings = params.get("SubnetMappings")
        delete_protection = params.get("DeleteProtection")
        subnet_change_protection = params.get("SubnetChangeProtection")
        firewall_policy_change_protection = params.get("FirewallPolicyChangeProtection")
        description = params.get("Description")
        tags = params.get("Tags")
        encryption_configuration = params.get("EncryptionConfiguration")
        enabled_analysis_types = params.get("EnabledAnalysisTypes")
        firewall = self.networkfirewall_backend.create_firewall(
            firewall_name=firewall_name,
            firewall_policy_arn=firewall_policy_arn,
            vpc_id=vpc_id,
            subnet_mappings=subnet_mappings,
            delete_protection=delete_protection,
            subnet_change_protection=subnet_change_protection,
            firewall_policy_change_protection=firewall_policy_change_protection,
            description=description,
            tags=tags,
            encryption_configuration=encryption_configuration,
            enabled_analysis_types=enabled_analysis_types,
        )

        return json.dumps(
            dict(Firewall=firewall.to_dict(), FirewallStatus=firewall.firewall_status)
        )

    def describe_logging_configuration(self):
        params = self._get_params()
        firewall_arn = params.get("FirewallArn")
        firewall_name = params.get("FirewallName")
        firewall_arn, logging_configuration = (
            self.networkfirewall_backend.describe_logging_configuration(
                firewall_arn=firewall_arn,
                firewall_name=firewall_name,
            )
        )
        # TODO: adjust response
        return json.dumps(
            dict(firewallArn=firewall_arn, loggingConfiguration=logging_configuration)
        )

    # add templates from here

    def update_logging_configuration(self):
        params = self._get_params()
        firewall_arn = params.get("FirewallArn")
        firewall_name = params.get("FirewallName")
        logging_configuration = params.get("LoggingConfiguration")
        firewall_arn, firewall_name, logging_configuration = (
            self.networkfirewall_backend.update_logging_configuration(
                firewall_arn=firewall_arn,
                firewall_name=firewall_name,
                logging_configuration=logging_configuration,
            )
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                firewallArn=firewall_arn,
                firewallName=firewall_name,
                loggingConfiguration=logging_configuration,
            )
        )

    def list_firewalls(self):
        params = self._get_params()
        next_token = params.get("NextToken")
        vpc_ids = params.get("VpcIds")
        max_results = params.get("MaxResults")
        firewalls, next_token = self.networkfirewall_backend.list_firewalls(
            next_token=next_token,
            vpc_ids=vpc_ids,
            max_results=max_results,
        )
        firewall_list = [fw.to_dict() for fw in firewalls]
        return json.dumps(dict(nextToken=next_token, Firewalls=firewall_list))

    def describe_firewall(self):
        params = self._get_params()
        firewall_name = params.get("FirewallName")
        firewall_arn = params.get("FirewallArn")
        update_token, firewall, firewall_status = (
            self.networkfirewall_backend.describe_firewall(
                firewall_name=firewall_name,
                firewall_arn=firewall_arn,
            )
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                updateToken=update_token,
                firewall=firewall,
                firewallStatus=firewall_status,
            )
        )
