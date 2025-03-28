"""NetworkFirewallBackend class with methods for supported APIs."""

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService


class NetworkFirewallModel(BaseModel):
    def __init__(
        self,
        account_id,
        region_name,
        firewall_name,
        firewall_policy_arn,
        vpc_id,
        subnet_mappings,
        delete_protection,
        subnet_change_protection,
        firewall_policy_change_protection,
        description,
        tags,
        encryption_configuration,
        enabled_analysis_types,
    ):
        self.firewall_name = firewall_name
        self.firewall_policy_arn = firewall_policy_arn
        self.vpc_id = vpc_id
        self.subnet_mappings = subnet_mappings
        self.delete_protection = delete_protection
        self.subnet_change_protection = subnet_change_protection
        self.firewall_policy_change_protection = firewall_policy_change_protection
        self.description = description
        self.tags = tags
        self.encryption_configuration = encryption_configuration
        self.enabled_analysis_types = enabled_analysis_types

        self.arn = f"arn:aws:network-firewall:{region_name}:{account_id}:firewall/{self.firewall_name}"

        self.firewall_status = {
            "Status": "READY",
            "ConfigurationSyncStateSummary": "IN_SYNC",
        }

    def to_dict(self):
        return {
            "FirewallName": self.firewall_name,
            "FirewallPolicyArn": self.firewall_policy_arn,
            "VpcId": self.vpc_id,
            "SubnetMappings": self.subnet_mappings,
            "DeleteProtection": self.delete_protection,
            "SubnetChangeProtection": self.subnet_change_protection,
            "FirewallPolicyChangeProtection": self.firewall_policy_change_protection,
            "Description": self.description,
            "Tags": self.tags,
            "EncryptionConfiguration": self.encryption_configuration,
            "EnabledAnalysisTypes": self.enabled_analysis_types,
        }


class NetworkFirewallBackend(BaseBackend):
    """Implementation of NetworkFirewall APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.firewalls = {}
        self.tagger = TaggingService()

    def create_firewall(
        self,
        firewall_name,
        firewall_policy_arn,
        vpc_id,
        subnet_mappings,
        delete_protection,
        subnet_change_protection,
        firewall_policy_change_protection,
        description,
        tags,
        encryption_configuration,
        enabled_analysis_types,
    ) -> NetworkFirewallModel:
        firewall = NetworkFirewallModel(
            self.account_id,
            self.region_name,
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
        self.firewalls[firewall.arn] = firewall

        if tags:
            self.tagger.tag_resource(firewall.arn, tags)

        return firewall

    def describe_logging_configuration(self, firewall_arn, firewall_name):
        # implement here
        return firewall_arn, logging_configuration

    def update_logging_configuration(
        self, firewall_arn, firewall_name, logging_configuration
    ):
        # implement here
        return firewall_arn, firewall_name, logging_configuration

    def list_firewalls(self, next_token, vpc_ids, max_results):
        # implement here
        return next_token, firewalls

    def describe_firewall(self, firewall_name, firewall_arn):
        # implement here
        return update_token, firewall, firewall_status


networkfirewall_backends = BackendDict(NetworkFirewallBackend, "network-firewall")
