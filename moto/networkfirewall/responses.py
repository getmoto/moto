"""Handles incoming networkfirewall requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse

from .models import (
    NetworkFirewallBackend,
    NetworkFirewallModel,
    networkfirewall_backends,
)


def _firewall(firewall: NetworkFirewallModel) -> dict[str, Any]:
    return {
        "FirewallName": firewall.firewall_name,
        "FirewallArn": firewall.arn,
        "FirewallPolicyArn": firewall.firewall_policy_arn,
        "VpcId": firewall.vpc_id,
        "SubnetMappings": firewall.subnet_mappings,
        "DeleteProtection": firewall.delete_protection,
        "SubnetChangeProtection": firewall.subnet_change_protection,
        "FirewallPolicyChangeProtection": firewall.firewall_policy_change_protection,
        "Description": firewall.description,
        "Tags": firewall.tags,
        "EncryptionConfiguration": firewall.encryption_configuration,
        "EnabledAnalysisTypes": firewall.enabled_analysis_types,
    }


class NetworkFirewallResponse(BaseResponse):
    """Handler for NetworkFirewall requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="network-firewall")
        self.automated_parameter_parsing = True

    @property
    def networkfirewall_backend(self) -> NetworkFirewallBackend:
        """Return backend instance specific for this region."""
        return networkfirewall_backends[self.current_account][self.region]

    def create_firewall(self) -> ActionResult:
        firewall_name = self._get_param("FirewallName")
        firewall_policy_arn = self._get_param("FirewallPolicyArn")
        vpc_id = self._get_param("VpcId")
        subnet_mappings = self._get_param("SubnetMappings")
        delete_protection = self._get_bool_param("DeleteProtection")
        subnet_change_protection = self._get_bool_param("SubnetChangeProtection")
        firewall_policy_change_protection = self._get_bool_param(
            "FirewallPolicyChangeProtection"
        )
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        encryption_configuration = self._get_param("EncryptionConfiguration")
        enabled_analysis_types = self._get_param("EnabledAnalysisTypes")
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
        result = {
            "Firewall": _firewall(firewall),
            "FirewallStatus": firewall.firewall_status,
        }
        return ActionResult(result)

    def describe_logging_configuration(self) -> ActionResult:
        firewall_arn = self._get_param("FirewallArn")
        firewall_name = self._get_param("FirewallName")
        firewall = self.networkfirewall_backend.describe_logging_configuration(
            firewall_arn=firewall_arn,
            firewall_name=firewall_name,
        )
        result = {
            "FirewallArn": firewall.arn,
            "LoggingConfiguration": firewall.logging_configs,
        }
        return ActionResult(result)

    def update_logging_configuration(self) -> ActionResult:
        firewall_arn = self._get_param("FirewallArn")
        firewall_name = self._get_param("FirewallName")
        logging_configuration = self._get_param("LoggingConfiguration")
        firewall = self.networkfirewall_backend.update_logging_configuration(
            firewall_arn=firewall_arn,
            firewall_name=firewall_name,
            logging_configuration=logging_configuration,
        )
        result = {
            "FirewallArn": firewall.arn,
            "FirewallName": firewall.firewall_name,
            "LoggingConfiguration": firewall.logging_configs,
        }
        return ActionResult(result)

    def list_firewalls(self) -> ActionResult:
        next_token = self._get_param("NextToken")
        vpc_ids = self._get_param("VpcIds")
        max_results = self._get_param("MaxResults")
        firewalls, next_token = self.networkfirewall_backend.list_firewalls(
            next_token=next_token,
            vpc_ids=vpc_ids,
            max_results=max_results,
        )
        firewall_list = [
            {"FirewallName": fw.firewall_name, "FirewallArn": fw.arn}
            for fw in firewalls
        ]
        return ActionResult({"NextToken": next_token, "Firewalls": firewall_list})

    def describe_firewall(self) -> ActionResult:
        firewall_name = self._get_param("FirewallName")
        firewall_arn = self._get_param("FirewallArn")
        firewall = self.networkfirewall_backend.describe_firewall(
            firewall_name=firewall_name,
            firewall_arn=firewall_arn,
        )
        result = {
            "UpdateToken": firewall.update_token,
            "Firewall": _firewall(firewall),
            "FirewallStatus": firewall.firewall_status,
        }
        return ActionResult(result)
