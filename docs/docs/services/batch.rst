.. _implementedservice_batch:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
batch
=====

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_batch
            def test_batch_behaviour:
                boto3.client("batch")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] cancel_job
- [X] create_compute_environment
- [X] create_job_queue
  
        Create a job queue

        :param queue_name: Queue name
        :type queue_name: str
        :param priority: Queue priority
        :type priority: int
        :param state: Queue state
        :type state: string
        :param compute_env_order: Compute environment list
        :type compute_env_order: list of dict
        :return: Tuple of Name, ARN
        :rtype: tuple of str
        

- [ ] create_scheduling_policy
- [X] delete_compute_environment
- [X] delete_job_queue
- [ ] delete_scheduling_policy
- [X] deregister_job_definition
- [X] describe_compute_environments
  
        Pagination is not yet implemented
        

- [X] describe_job_definitions
  
        Pagination is not yet implemented
        

- [X] describe_job_queues
  
        Pagination is not yet implemented
        

- [X] describe_jobs
- [ ] describe_scheduling_policies
- [X] list_jobs
  
        Pagination is not yet implemented
        

- [ ] list_scheduling_policies
- [X] list_tags_for_resource
- [X] register_job_definition
- [X] submit_job
  
        Parameters RetryStrategy and Parameters are not yet implemented.
        

- [X] tag_resource
- [X] terminate_job
- [X] untag_resource
- [X] update_compute_environment
- [X] update_job_queue
  
        Update a job queue

        :param queue_name: Queue name
        :type queue_name: str
        :param priority: Queue priority
        :type priority: int
        :param state: Queue state
        :type state: string
        :param compute_env_order: Compute environment list
        :type compute_env_order: list of dict
        :return: Tuple of Name, ARN
        :rtype: tuple of str
        

- [ ] update_scheduling_policy

