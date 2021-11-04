.. _implementedservice_batch:

=====
batch
=====



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
        

- [X] delete_compute_environment
- [X] delete_job_queue
- [X] deregister_job_definition
- [X] describe_compute_environments
- [X] describe_job_definitions
- [X] describe_job_queues
- [X] describe_jobs
- [X] list_jobs
- [ ] list_tags_for_resource
- [X] register_job_definition
- [X] submit_job
- [ ] tag_resource
- [X] terminate_job
- [ ] untag_resource
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
        


