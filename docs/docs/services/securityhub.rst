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
- [ ] batch_update_standards_control_associations
- [ ] create_action_target
- [ ] create_automation_rule
- [ ] create_configuration_policy
- [ ] create_finding_aggregator
- [ ] create_insight
- [ ] create_members
- [ ] decline_invitations
- [ ] delete_action_target
- [ ] delete_configuration_policy
- [ ] delete_finding_aggregator
- [ ] delete_insight
- [ ] delete_invitations
- [ ] delete_members
- [ ] describe_action_targets
- [ ] describe_hub
- [ ] describe_organization_configuration
- [ ] describe_products
- [ ] describe_standards
- [ ] describe_standards_controls
- [ ] disable_import_findings_for_product
- [ ] disable_organization_admin_account
- [ ] disable_security_hub
- [ ] disassociate_from_administrator_account
- [ ] disassociate_from_master_account
- [ ] disassociate_members
- [ ] enable_import_findings_for_product
- [ ] enable_organization_admin_account
- [ ] enable_security_hub
- [ ] get_administrator_account
- [ ] get_configuration_policy
- [ ] get_configuration_policy_association
- [ ] get_enabled_standards
- [ ] get_finding_aggregator
- [ ] get_finding_history
- [X] get_findings
  
        Returns findings based on optional filters and sort criteria.
        

- [ ] get_insight_results
- [ ] get_insights
- [ ] get_invitations_count
- [ ] get_master_account
- [ ] get_members
- [ ] get_security_control_definition
- [ ] invite_members
- [ ] list_automation_rules
- [ ] list_configuration_policies
- [ ] list_configuration_policy_associations
- [ ] list_enabled_products_for_import
- [ ] list_finding_aggregators
- [ ] list_invitations
- [ ] list_members
- [ ] list_organization_admin_accounts
- [ ] list_security_control_definitions
- [ ] list_standards_control_associations
- [ ] list_tags_for_resource
- [ ] start_configuration_policy_association
- [ ] start_configuration_policy_disassociation
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_action_target
- [ ] update_configuration_policy
- [ ] update_finding_aggregator
- [ ] update_findings
- [ ] update_insight
- [ ] update_organization_configuration
- [ ] update_security_control
- [ ] update_security_hub_configuration
- [ ] update_standards_control

