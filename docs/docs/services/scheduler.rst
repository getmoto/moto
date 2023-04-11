.. _implementedservice_scheduler:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=========
scheduler
=========

.. autoclass:: moto.scheduler.models.EventBridgeSchedulerBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_scheduler
            def test_scheduler_behaviour:
                boto3.client("scheduler")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_schedule
  
        The ClientToken parameter is not yet implemented
        

- [X] create_schedule_group
  
        The ClientToken parameter is not yet implemented
        

- [X] delete_schedule
- [X] delete_schedule_group
- [X] get_schedule
- [X] get_schedule_group
- [X] list_schedule_groups
  
        The MaxResults-parameter and pagination options are not yet implemented
        

- [X] list_schedules
  
        The following parameters are not yet implemented: MaxResults, NamePrefix, NextToken
        

- [X] list_tags_for_resource
- [X] tag_resource
- [X] untag_resource
- [X] update_schedule
  
        The ClientToken is not yet implemented
        


