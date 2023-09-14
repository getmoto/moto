.. _implementedservice_ce:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==
ce
==

.. autoclass:: moto.ce.models.CostExplorerBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ce
            def test_ce_behaviour:
                boto3.client("ce")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_anomaly_monitor
- [ ] create_anomaly_subscription
- [X] create_cost_category_definition
  
        The EffectiveOn and ResourceTags-parameters are not yet implemented
        

- [ ] delete_anomaly_monitor
- [ ] delete_anomaly_subscription
- [X] delete_cost_category_definition
  
        The EffectiveOn-parameter is not yet implemented
        

- [X] describe_cost_category_definition
  
        The EffectiveOn-parameter is not yet implemented
        

- [ ] get_anomalies
- [ ] get_anomaly_monitors
- [ ] get_anomaly_subscriptions
- [ ] get_cost_and_usage
- [ ] get_cost_and_usage_with_resources
- [ ] get_cost_categories
- [ ] get_cost_forecast
- [ ] get_dimension_values
- [ ] get_reservation_coverage
- [ ] get_reservation_purchase_recommendation
- [ ] get_reservation_utilization
- [ ] get_rightsizing_recommendation
- [ ] get_savings_plan_purchase_recommendation_details
- [ ] get_savings_plans_coverage
- [ ] get_savings_plans_purchase_recommendation
- [ ] get_savings_plans_utilization
- [ ] get_savings_plans_utilization_details
- [ ] get_tags
- [ ] get_usage_forecast
- [ ] list_cost_allocation_tags
- [ ] list_cost_category_definitions
- [ ] list_savings_plans_purchase_recommendation_generation
- [X] list_tags_for_resource
- [ ] provide_anomaly_feedback
- [ ] start_savings_plans_purchase_recommendation_generation
- [X] tag_resource
- [X] untag_resource
- [ ] update_anomaly_monitor
- [ ] update_anomaly_subscription
- [ ] update_cost_allocation_tags_status
- [X] update_cost_category_definition
  
        The EffectiveOn-parameter is not yet implemented
        


