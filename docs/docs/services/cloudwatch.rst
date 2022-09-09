.. _implementedservice_cloudwatch:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
cloudwatch
==========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cloudwatch
            def test_cloudwatch_behaviour:
                boto3.client("cloudwatch")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] delete_alarms
- [ ] delete_anomaly_detector
- [X] delete_dashboards
- [ ] delete_insight_rules
- [ ] delete_metric_stream
- [ ] describe_alarm_history
- [ ] describe_alarms
- [ ] describe_alarms_for_metric
- [ ] describe_anomaly_detectors
- [ ] describe_insight_rules
- [ ] disable_alarm_actions
- [ ] disable_insight_rules
- [ ] enable_alarm_actions
- [ ] enable_insight_rules
- [X] get_dashboard
- [ ] get_insight_rule_report
- [X] get_metric_data
- [X] get_metric_statistics
- [ ] get_metric_stream
- [ ] get_metric_widget_image
- [X] list_dashboards
- [ ] list_metric_streams
- [X] list_metrics
- [X] list_tags_for_resource
- [ ] put_anomaly_detector
- [ ] put_composite_alarm
- [X] put_dashboard
- [ ] put_insight_rule
- [X] put_metric_alarm
- [X] put_metric_data
- [ ] put_metric_stream
- [X] set_alarm_state
- [ ] start_metric_streams
- [ ] stop_metric_streams
- [X] tag_resource
- [X] untag_resource

