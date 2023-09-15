.. _implementedservice_robomaker:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=========
robomaker
=========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_robomaker
            def test_robomaker_behaviour:
                boto3.client("robomaker")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_delete_worlds
- [ ] batch_describe_simulation_job
- [ ] cancel_deployment_job
- [ ] cancel_simulation_job
- [ ] cancel_simulation_job_batch
- [ ] cancel_world_export_job
- [ ] cancel_world_generation_job
- [ ] create_deployment_job
- [ ] create_fleet
- [ ] create_robot
- [X] create_robot_application
  
        The tags and environment parameters are not yet implemented
        

- [ ] create_robot_application_version
- [ ] create_simulation_application
- [ ] create_simulation_application_version
- [ ] create_simulation_job
- [ ] create_world_export_job
- [ ] create_world_generation_job
- [ ] create_world_template
- [ ] delete_fleet
- [ ] delete_robot
- [X] delete_robot_application
- [ ] delete_simulation_application
- [ ] delete_world_template
- [ ] deregister_robot
- [ ] describe_deployment_job
- [ ] describe_fleet
- [ ] describe_robot
- [X] describe_robot_application
- [ ] describe_simulation_application
- [ ] describe_simulation_job
- [ ] describe_simulation_job_batch
- [ ] describe_world
- [ ] describe_world_export_job
- [ ] describe_world_generation_job
- [ ] describe_world_template
- [ ] get_world_template_body
- [ ] list_deployment_jobs
- [ ] list_fleets
- [X] list_robot_applications
  
        Currently returns all applications - none of the parameters are taken into account
        

- [ ] list_robots
- [ ] list_simulation_applications
- [ ] list_simulation_job_batches
- [ ] list_simulation_jobs
- [ ] list_tags_for_resource
- [ ] list_world_export_jobs
- [ ] list_world_generation_jobs
- [ ] list_world_templates
- [ ] list_worlds
- [ ] register_robot
- [ ] restart_simulation_job
- [ ] start_simulation_job_batch
- [ ] sync_deployment_job
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_robot_application
- [ ] update_simulation_application
- [ ] update_world_template

