from moto.core.responses import BaseResponse
from .models import batch_backends, BatchBackend
from urllib.parse import urlsplit, unquote

import json


class BatchResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="batch")

    @property
    def batch_backend(self) -> BatchBackend:
        """
        :return: Batch Backend
        :rtype: moto.batch.models.BatchBackend
        """
        return batch_backends[self.current_account][self.region]

    def _get_action(self) -> str:
        # Return element after the /v1/*
        return urlsplit(self.uri).path.lstrip("/").split("/")[1]

    # CreateComputeEnvironment
    def createcomputeenvironment(self) -> str:
        compute_env_name = self._get_param("computeEnvironmentName")
        compute_resource = self._get_param("computeResources")
        service_role = self._get_param("serviceRole")
        state = self._get_param("state")
        _type = self._get_param("type")

        name, arn = self.batch_backend.create_compute_environment(
            compute_environment_name=compute_env_name,
            _type=_type,
            state=state,
            compute_resources=compute_resource,
            service_role=service_role,
        )

        result = {"computeEnvironmentArn": arn, "computeEnvironmentName": name}

        return json.dumps(result)

    # DescribeComputeEnvironments
    def describecomputeenvironments(self) -> str:
        compute_environments = self._get_param("computeEnvironments")

        envs = self.batch_backend.describe_compute_environments(compute_environments)

        result = {"computeEnvironments": envs}
        return json.dumps(result)

    # DeleteComputeEnvironment
    def deletecomputeenvironment(self) -> str:
        compute_environment = self._get_param("computeEnvironment")

        self.batch_backend.delete_compute_environment(compute_environment)

        return ""

    # UpdateComputeEnvironment
    def updatecomputeenvironment(self) -> str:
        compute_env_name = self._get_param("computeEnvironment")
        compute_resource = self._get_param("computeResources")
        service_role = self._get_param("serviceRole")
        state = self._get_param("state")

        name, arn = self.batch_backend.update_compute_environment(
            compute_environment_name=compute_env_name,
            compute_resources=compute_resource,
            service_role=service_role,
            state=state,
        )

        result = {"computeEnvironmentArn": arn, "computeEnvironmentName": name}

        return json.dumps(result)

    # CreateJobQueue
    def createjobqueue(self) -> str:
        compute_env_order = self._get_param("computeEnvironmentOrder")
        queue_name = self._get_param("jobQueueName")
        priority = self._get_param("priority")
        state = self._get_param("state")
        tags = self._get_param("tags")

        name, arn = self.batch_backend.create_job_queue(
            queue_name=queue_name,
            priority=priority,
            state=state,
            compute_env_order=compute_env_order,
            tags=tags,
        )

        result = {"jobQueueArn": arn, "jobQueueName": name}

        return json.dumps(result)

    # DescribeJobQueues
    def describejobqueues(self) -> str:
        job_queues = self._get_param("jobQueues")

        queues = self.batch_backend.describe_job_queues(job_queues)

        result = {"jobQueues": queues}
        return json.dumps(result)

    # UpdateJobQueue
    def updatejobqueue(self) -> str:
        compute_env_order = self._get_param("computeEnvironmentOrder")
        queue_name = self._get_param("jobQueue")
        priority = self._get_param("priority")
        state = self._get_param("state")

        name, arn = self.batch_backend.update_job_queue(
            queue_name=queue_name,
            priority=priority,
            state=state,
            compute_env_order=compute_env_order,
        )

        result = {"jobQueueArn": arn, "jobQueueName": name}

        return json.dumps(result)

    # DeleteJobQueue
    def deletejobqueue(self) -> str:
        queue_name = self._get_param("jobQueue")

        self.batch_backend.delete_job_queue(queue_name)

        return ""

    # RegisterJobDefinition
    def registerjobdefinition(self) -> str:
        container_properties = self._get_param("containerProperties")
        def_name = self._get_param("jobDefinitionName")
        parameters = self._get_param("parameters")
        tags = self._get_param("tags")
        retry_strategy = self._get_param("retryStrategy")
        _type = self._get_param("type")
        timeout = self._get_param("timeout")
        platform_capabilities = self._get_param("platformCapabilities")
        propagate_tags = self._get_param("propagateTags")
        name, arn, revision = self.batch_backend.register_job_definition(
            def_name=def_name,
            parameters=parameters,
            _type=_type,
            tags=tags,
            retry_strategy=retry_strategy,
            container_properties=container_properties,
            timeout=timeout,
            platform_capabilities=platform_capabilities,
            propagate_tags=propagate_tags,
        )

        result = {
            "jobDefinitionArn": arn,
            "jobDefinitionName": name,
            "revision": revision,
        }

        return json.dumps(result)

    # DeregisterJobDefinition
    def deregisterjobdefinition(self) -> str:
        queue_name = self._get_param("jobDefinition")

        self.batch_backend.deregister_job_definition(queue_name)

        return ""

    # DescribeJobDefinitions
    def describejobdefinitions(self) -> str:
        job_def_name = self._get_param("jobDefinitionName")
        job_def_list = self._get_param("jobDefinitions")
        status = self._get_param("status")

        job_defs = self.batch_backend.describe_job_definitions(
            job_def_name, job_def_list, status
        )

        result = {"jobDefinitions": [job.describe() for job in job_defs]}
        return json.dumps(result)

    # SubmitJob
    def submitjob(self) -> str:
        container_overrides = self._get_param("containerOverrides")
        depends_on = self._get_param("dependsOn")
        job_def = self._get_param("jobDefinition")
        job_name = self._get_param("jobName")
        job_queue = self._get_param("jobQueue")
        timeout = self._get_param("timeout")

        name, job_id = self.batch_backend.submit_job(
            job_name,
            job_def,
            job_queue,
            depends_on=depends_on,
            container_overrides=container_overrides,
            timeout=timeout,
        )

        result = {"jobId": job_id, "jobName": name}

        return json.dumps(result)

    # DescribeJobs
    def describejobs(self) -> str:
        jobs = self._get_param("jobs")

        return json.dumps({"jobs": self.batch_backend.describe_jobs(jobs)})

    # ListJobs
    def listjobs(self) -> str:
        job_queue = self._get_param("jobQueue")
        job_status = self._get_param("jobStatus")

        jobs = self.batch_backend.list_jobs(job_queue, job_status)

        result = {"jobSummaryList": [job.describe_short() for job in jobs]}
        return json.dumps(result)

    # TerminateJob
    def terminatejob(self) -> str:
        job_id = self._get_param("jobId")
        reason = self._get_param("reason")

        self.batch_backend.terminate_job(job_id, reason)

        return ""

    # CancelJob
    def canceljob(self) -> str:
        job_id = self._get_param("jobId")
        reason = self._get_param("reason")
        self.batch_backend.cancel_job(job_id, reason)

        return ""

    def tags(self) -> str:
        resource_arn = unquote(self.path).split("/v1/tags/")[-1]
        tags = self._get_param("tags")
        if self.method == "POST":
            self.batch_backend.tag_resource(resource_arn, tags)
        if self.method == "GET":
            tags = self.batch_backend.list_tags_for_resource(resource_arn)
            return json.dumps({"tags": tags})
        if self.method == "DELETE":
            tag_keys = self.querystring.get("tagKeys")
            self.batch_backend.untag_resource(resource_arn, tag_keys)  # type: ignore[arg-type]
        return ""
