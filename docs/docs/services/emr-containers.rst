.. _implementedservice_emr-containers:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==============
emr-containers
==============

.. autoclass:: moto.emrcontainers.models.EMRContainersBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_emrcontainers
            def test_emr-containers_behaviour:
                boto3.client("emr-containers")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] cancel_job_run
- [ ] create_managed_endpoint
- [X] create_virtual_cluster
- [ ] delete_managed_endpoint
- [X] delete_virtual_cluster
- [X] describe_job_run
- [ ] describe_managed_endpoint
- [X] describe_virtual_cluster
- [X] list_job_runs
- [ ] list_managed_endpoints
- [ ] list_tags_for_resource
- [X] list_virtual_clusters
- [X] start_job_run
- [ ] tag_resource
- [ ] untag_resource

