.. _implementedservice_config:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
config
======



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_config
            def test_config_behaviour:
                boto3.client("config")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] batch_get_aggregate_resource_config
  Returns configuration of resource for current regional backend.

        Item is returned in AWS Config format.

        As far a moto goes -- the only real difference between this function
        and the `batch_get_resource_config` function is that this will require
        a Config Aggregator be set up a priori and can search based on resource
        regions.

        Note: moto will IGNORE the resource account ID in the search query.
        

- [X] batch_get_resource_config
  Returns configuration of resource for the current regional backend.

        Item is returned in AWS Config format.

        :param resource_keys:
        :param backend_region:
        

- [X] delete_aggregation_authorization
- [X] delete_config_rule
  Delete config rule used for evaluating resource compliance.

- [X] delete_configuration_aggregator
- [X] delete_configuration_recorder
- [ ] delete_conformance_pack
- [X] delete_delivery_channel
- [ ] delete_evaluation_results
- [ ] delete_organization_config_rule
- [X] delete_organization_conformance_pack
- [ ] delete_pending_aggregation_request
- [ ] delete_remediation_configuration
- [ ] delete_remediation_exceptions
- [ ] delete_resource_config
- [ ] delete_retention_configuration
- [ ] delete_stored_query
- [ ] deliver_config_snapshot
- [ ] describe_aggregate_compliance_by_config_rules
- [ ] describe_aggregate_compliance_by_conformance_packs
- [X] describe_aggregation_authorizations
- [ ] describe_compliance_by_config_rule
- [ ] describe_compliance_by_resource
- [ ] describe_config_rule_evaluation_status
- [X] describe_config_rules
  Return details for the given ConfigRule names or for all rules.

- [ ] describe_configuration_aggregator_sources_status
- [X] describe_configuration_aggregators
- [X] describe_configuration_recorder_status
- [X] describe_configuration_recorders
- [ ] describe_conformance_pack_compliance
- [ ] describe_conformance_pack_status
- [ ] describe_conformance_packs
- [ ] describe_delivery_channel_status
- [X] describe_delivery_channels
- [ ] describe_organization_config_rule_statuses
- [ ] describe_organization_config_rules
- [X] describe_organization_conformance_pack_statuses
- [X] describe_organization_conformance_packs
- [ ] describe_pending_aggregation_requests
- [ ] describe_remediation_configurations
- [ ] describe_remediation_exceptions
- [ ] describe_remediation_execution_status
- [ ] describe_retention_configurations
- [ ] get_aggregate_compliance_details_by_config_rule
- [ ] get_aggregate_config_rule_compliance_summary
- [ ] get_aggregate_conformance_pack_compliance_summary
- [ ] get_aggregate_discovered_resource_counts
- [ ] get_aggregate_resource_config
- [ ] get_compliance_details_by_config_rule
- [ ] get_compliance_details_by_resource
- [ ] get_compliance_summary_by_config_rule
- [ ] get_compliance_summary_by_resource_type
- [ ] get_conformance_pack_compliance_details
- [ ] get_conformance_pack_compliance_summary
- [ ] get_discovered_resource_counts
- [ ] get_organization_config_rule_detailed_status
- [X] get_organization_conformance_pack_detailed_status
- [X] get_resource_config_history
  Returns configuration of resource for the current regional backend.

        Item returned in AWS Config format.

        NOTE: This is --NOT-- returning history as it is not supported in
        moto at this time. (PR's welcome!)

        As such, the later_time, earlier_time, limit, and next_token are
        ignored as this will only return 1 item. (If no items, it raises an
        exception).
        

- [ ] get_stored_query
- [X] list_aggregate_discovered_resources
  Queries AWS Config listing function that must exist for resource backend.

        As far a moto goes -- the only real difference between this function
        and the `list_discovered_resources` function is that this will require
        a Config Aggregator be set up a priori and can search based on resource
        regions.

        :param aggregator_name:
        :param resource_type:
        :param filters:
        :param limit:
        :param next_token:
        :return:
        

- [X] list_discovered_resources
  Queries against AWS Config (non-aggregated) listing function.

        The listing function must exist for the resource backend.

        :param resource_type:
        :param backend_region:
        :param ids:
        :param name:
        :param limit:
        :param next_token:
        :return:
        

- [ ] list_stored_queries
- [X] list_tags_for_resource
  Return list of tags for AWS Config resource.

- [X] put_aggregation_authorization
- [X] put_config_rule
  Add/Update config rule for evaluating resource compliance.

        TBD - Only the "accounting" of config rules are handled at the
        moment.  No events are created or triggered.  There is no
        interaction with the config recorder.
        

- [X] put_configuration_aggregator
- [X] put_configuration_recorder
- [ ] put_conformance_pack
- [X] put_delivery_channel
- [X] put_evaluations
- [ ] put_external_evaluation
- [ ] put_organization_config_rule
- [X] put_organization_conformance_pack
- [ ] put_remediation_configurations
- [ ] put_remediation_exceptions
- [ ] put_resource_config
- [ ] put_retention_configuration
- [ ] put_stored_query
- [ ] select_aggregate_resource_config
- [ ] select_resource_config
- [ ] start_config_rules_evaluation
- [X] start_configuration_recorder
- [ ] start_remediation_execution
- [X] stop_configuration_recorder
- [X] tag_resource
  Add tags in config with a matching ARN.

- [X] untag_resource
  Remove tags in config with a matching ARN.

        If the tags in the tag_keys don't match any keys for that
        ARN, they're just ignored.
        


