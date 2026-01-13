.. _implementedservice_securityhub:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===========
securityhub
===========

.. autoclass:: moto.securityhub.models.SecurityHubBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] accept_administrator_invitation
- [ ] accept_invitation
- [ ] batch_delete_automation_rules
- [ ] batch_disable_standards
- [ ] batch_enable_standards
- [ ] batch_get_automation_rules
- [ ] batch_get_configuration_policy_associations
- [ ] batch_get_security_controls
- [ ] batch_get_standards_control_associations
- [X] batch_import_findings
  
        Import findings in batch to SecurityHub.

        Args:
            findings: List of finding dictionaries to import

        Returns:
            Tuple of (failed_count, success_count, failed_findings)
        

- [ ] batch_update_automation_rules
- [ ] batch_update_findings
- [ ] batch_update_findings_v2
- [ ] batch_update_standards_control_associations
- [ ] create_action_target
- [ ] create_aggregator_v2
- [ ] create_automation_rule
- [ ] create_automation_rule_v2
- [ ] create_configuration_policy
- [ ] create_connector_v2
- [ ] create_finding_aggregator
- [ ] create_insight
- [ ] create_members
- [ ] create_ticket_v2
- [ ] decline_invitations
- [ ] delete_action_target
- [ ] delete_aggregator_v2
- [ ] delete_automation_rule_v2
- [ ] delete_configuration_policy
- [ ] delete_connector_v2
- [ ] delete_finding_aggregator
- [ ] delete_insight
- [ ] delete_invitations
- [ ] delete_members
- [ ] describe_action_targets
- [X] describe_hub
- [X] describe_organization_configuration
- [ ] describe_products
- [ ] describe_products_v2
- [ ] describe_security_hub_v2
- [ ] describe_standards
- [ ] describe_standards_controls
- [ ] disable_import_findings_for_product
- [ ] disable_organization_admin_account
- [X] disable_security_hub
- [ ] disable_security_hub_v2
- [ ] disassociate_from_administrator_account
- [ ] disassociate_from_master_account
- [ ] disassociate_members
- [ ] enable_import_findings_for_product
- [X] enable_organization_admin_account
- [X] enable_security_hub
- [ ] enable_security_hub_v2
- [X] get_administrator_account
- [ ] get_aggregator_v2
- [ ] get_automation_rule_v2
- [ ] get_configuration_policy
- [ ] get_configuration_policy_association
- [ ] get_connector_v2
- [ ] get_enabled_standards
- [ ] get_finding_aggregator
- [ ] get_finding_history
- [ ] get_finding_statistics_v2
- [X] get_findings
  
        Returns findings based on optional filters and sort criteria.
        

- [ ] get_findings_trends_v2
- [ ] get_findings_v2
- [ ] get_insight_results
- [ ] get_insights
- [ ] get_invitations_count
- [ ] get_master_account
- [ ] get_members
- [ ] get_resources_statistics_v2
- [ ] get_resources_trends_v2
- [ ] get_resources_v2
- [ ] get_security_control_definition
- [ ] invite_members
- [ ] list_aggregators_v2
- [ ] list_automation_rules
- [ ] list_automation_rules_v2
- [ ] list_configuration_policies
- [ ] list_configuration_policy_associations
- [ ] list_connectors_v2
- [ ] list_enabled_products_for_import
- [ ] list_finding_aggregators
- [ ] list_invitations
- [ ] list_members
- [ ] list_organization_admin_accounts
- [ ] list_security_control_definitions
- [ ] list_standards_control_associations
- [ ] list_tags_for_resource
- [ ] register_connector_v2
- [ ] start_configuration_policy_association
- [ ] start_configuration_policy_disassociation
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_action_target
- [ ] update_aggregator_v2
- [ ] update_automation_rule_v2
- [ ] update_configuration_policy
- [ ] update_connector_v2
- [ ] update_finding_aggregator
- [ ] update_findings
- [ ] update_insight
- [X] update_organization_configuration
- [ ] update_security_control
- [ ] update_security_hub_configuration
- [ ] update_standards_control

