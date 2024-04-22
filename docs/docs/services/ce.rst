.. _implementedservice_ce:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==
ce
==

.. autoclass:: moto.ce.models.CostExplorerBackend

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
- [ ] get_approximate_usage_records
- [X] get_cost_and_usage
  
        There is no validation yet on any of the input parameters.

        Cost or usage is not tracked by Moto, so this call will return nothing by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `get_cost_and_usage` will take the first result from that queue, and assign it to the provided parameters. Subsequent requests using the same parameters will return the same result. Other requests using different parameters will take the next result from the queue, or return an empty result if the queue is empty.

        Configure this queue by making an HTTP request to `/moto-api/static/ce/cost-and-usage-results`. An example invocation looks like this:

        .. sourcecode:: python

            result = {
                "results": [
                    {
                        "ResultsByTime": [
                            {
                                "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-02"},
                                "Total": {
                                    "BlendedCost": {"Amount": "0.0101516483", "Unit": "USD"}
                                },
                                "Groups": [],
                                "Estimated": False
                            }
                        ],
                        "DimensionValueAttributes": [{"Value": "v", "Attributes": {"a": "b"}}]
                    },
                    {
                        ...
                    },
                ]
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com/moto-api/static/ce/cost-and-usage-results",
                json=expected_results,
            )
            assert resp.status_code == 201

            ce = boto3.client("ce", region_name="us-east-1")
            resp = ce.get_cost_and_usage(...)
        

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
- [ ] list_cost_allocation_tag_backfill_history
- [ ] list_cost_allocation_tags
- [ ] list_cost_category_definitions
- [ ] list_savings_plans_purchase_recommendation_generation
- [X] list_tags_for_resource
- [ ] provide_anomaly_feedback
- [ ] start_cost_allocation_tag_backfill
- [ ] start_savings_plans_purchase_recommendation_generation
- [X] tag_resource
- [X] untag_resource
- [ ] update_anomaly_monitor
- [ ] update_anomaly_subscription
- [ ] update_cost_allocation_tags_status
- [X] update_cost_category_definition
  
        The EffectiveOn-parameter is not yet implemented
        


