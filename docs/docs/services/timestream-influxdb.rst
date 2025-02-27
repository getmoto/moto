.. _implementedservice_timestream-influxdb:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===================
timestream-influxdb
===================

.. autoclass:: moto.timestreaminfluxdb.models.TimestreamInfluxDBBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] create_db_cluster
- [X] create_db_instance
  
        dbParameterGroupIdentifier argument is not yet handled
        deploymentType currently is auto set to 'SINGLE_AZ' if not passed in.
        publicAccessible is not yet handled
        logDeliveryConfiguration is not yet handled
        AvailabilityZone and SecondaryAvailabilityZone are not yet handled
        influxAuthParametersSecretArn is not yet handled
        

- [ ] create_db_parameter_group
- [ ] delete_db_cluster
- [X] delete_db_instance
- [ ] get_db_cluster
- [X] get_db_instance
- [ ] get_db_parameter_group
- [ ] list_db_clusters
- [X] list_db_instances
  
        Pagination is not yet implemented
        

- [ ] list_db_instances_for_cluster
- [ ] list_db_parameter_groups
- [X] list_tags_for_resource
- [X] tag_resource
- [X] untag_resource
- [ ] update_db_cluster
- [ ] update_db_instance

