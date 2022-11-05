.. _implementedservice_amp:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
amp
===

.. autoclass:: moto.amp.models.PrometheusServiceBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_amp
            def test_amp_behaviour:
                boto3.client("amp")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_alert_manager_definition
- [X] create_logging_configuration
- [X] create_rule_groups_namespace
  
        The ClientToken-parameter is not yet implemented
        

- [X] create_workspace
  
        The ClientToken-parameter is not yet implemented
        

- [ ] delete_alert_manager_definition
- [X] delete_logging_configuration
- [X] delete_rule_groups_namespace
  
        The ClientToken-parameter is not yet implemented
        

- [X] delete_workspace
  
        The ClientToken-parameter is not yet implemented
        

- [ ] describe_alert_manager_definition
- [X] describe_logging_configuration
- [X] describe_rule_groups_namespace
- [X] describe_workspace
- [X] list_rule_groups_namespaces
- [X] list_tags_for_resource
- [X] list_workspaces
- [ ] put_alert_manager_definition
- [X] put_rule_groups_namespace
  
        The ClientToken-parameter is not yet implemented
        

- [X] tag_resource
- [X] untag_resource
- [X] update_logging_configuration
- [X] update_workspace_alias
  
        The ClientToken-parameter is not yet implemented
        


