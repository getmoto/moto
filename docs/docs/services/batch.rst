.. _implementedservice_batch:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
batch
=====

.. autoclass:: moto.batch.models.BatchBackend

|start-h3| Implemented features for this service |end-h3|

- [X] cancel_job
- [X] create_compute_environment
- [ ] create_consumable_resource
- [X] create_job_queue
- [X] create_scheduling_policy
- [ ] create_service_environment
- [X] delete_compute_environment
- [ ] delete_consumable_resource
- [X] delete_job_queue
- [X] delete_scheduling_policy
- [ ] delete_service_environment
- [X] deregister_job_definition
- [X] describe_compute_environments
  
        Pagination is not yet implemented
        

- [ ] describe_consumable_resource
- [X] describe_job_definitions
  
        Pagination is not yet implemented
        

- [X] describe_job_queues
  
        Pagination is not yet implemented
        

- [X] describe_jobs
- [X] describe_scheduling_policies
- [ ] describe_service_environments
- [ ] describe_service_job
- [ ] get_job_queue_snapshot
- [ ] list_consumable_resources
- [X] list_jobs
  
        TODO: Pagination is not yet implemented
        TODO: According to Boto3 documentation, filters are not supported when filtering by batch array job id.
            Current implementation does not differentiate between array job listing and normal job listing.
        

- [ ] list_jobs_by_consumable_resource
- [X] list_scheduling_policies
  
        Pagination is not yet implemented
        

- [ ] list_service_jobs
- [X] list_tags_for_resource
- [X] register_job_definition
- [X] submit_job
  
        Parameters RetryStrategy and Parameters are not yet implemented.
        

- [ ] submit_service_job
- [X] tag_resource
- [X] terminate_job
- [ ] terminate_service_job
- [X] untag_resource
- [X] update_compute_environment
- [ ] update_consumable_resource
- [X] update_job_queue
- [X] update_scheduling_policy
- [ ] update_service_environment

