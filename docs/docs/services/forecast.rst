.. _implementedservice_forecast:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
forecast
========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_forecast
            def test_forecast_behaviour:
                boto3.client("forecast")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_dataset
- [X] create_dataset_group
- [ ] create_dataset_import_job
- [ ] create_forecast
- [ ] create_forecast_export_job
- [ ] create_predictor
- [ ] create_predictor_backtest_export_job
- [ ] delete_dataset
- [X] delete_dataset_group
- [ ] delete_dataset_import_job
- [ ] delete_forecast
- [ ] delete_forecast_export_job
- [ ] delete_predictor
- [ ] delete_predictor_backtest_export_job
- [ ] delete_resource_tree
- [ ] describe_dataset
- [X] describe_dataset_group
- [ ] describe_dataset_import_job
- [ ] describe_forecast
- [ ] describe_forecast_export_job
- [ ] describe_predictor
- [ ] describe_predictor_backtest_export_job
- [ ] get_accuracy_metrics
- [X] list_dataset_groups
- [ ] list_dataset_import_jobs
- [ ] list_datasets
- [ ] list_forecast_export_jobs
- [ ] list_forecasts
- [ ] list_predictor_backtest_export_jobs
- [ ] list_predictors
- [ ] list_tags_for_resource
- [ ] stop_resource
- [ ] tag_resource
- [ ] untag_resource
- [X] update_dataset_group

