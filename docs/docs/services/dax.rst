.. _implementedservice_dax:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
dax
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_dax
            def test_dax_behaviour:
                boto3.client("dax")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_cluster
  
        The following parameters are not yet processed:
        AvailabilityZones, SubnetGroupNames, SecurityGroups, PreferredMaintenanceWindow, NotificationTopicArn, ParameterGroupName
        

- [ ] create_parameter_group
- [ ] create_subnet_group
- [X] decrease_replication_factor
  
        The AvailabilityZones-parameter is not yet implemented
        

- [X] delete_cluster
- [ ] delete_parameter_group
- [ ] delete_subnet_group
- [X] describe_clusters
- [ ] describe_default_parameters
- [ ] describe_events
- [ ] describe_parameter_groups
- [ ] describe_parameters
- [ ] describe_subnet_groups
- [X] increase_replication_factor
  
        The AvailabilityZones-parameter is not yet implemented
        

- [X] list_tags
  
        Pagination is not yet implemented
        

- [ ] reboot_node
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_cluster
- [ ] update_parameter_group
- [ ] update_subnet_group

