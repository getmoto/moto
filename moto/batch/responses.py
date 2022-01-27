from moto.core.responses import BaseResponse
from .models import batch_backends
from urllib.parse import urlsplit

from .exceptions import AWSError

import json


class BatchResponse(BaseResponse):
    def _error(self, code, message):
        return json.dumps({"__type": code, "message": message}), dict(status=400)

    @property
    def batch_backend(self):
        """
        :return: Batch Backend
        :rtype: moto.batch.models.BatchBackend
        """
        return batch_backends[self.region]

    @property
    def json(self):
        if self.body is None or self.body == "":
            self._json = {}
        elif not hasattr(self, "_json"):
            try:
                self._json = json.loads(self.body)
            except ValueError:
                print()
        return self._json

    def _get_param(self, param_name, if_none=None):
        val = self.json.get(param_name)
        if val is not None:
            return val
        return if_none

    def _get_action(self):
        # Return element after the /v1/*
        return urlsplit(self.uri).path.lstrip("/").split("/")[1]

    # CreateComputeEnvironment
    def createcomputeenvironment(self):
        compute_env_name = self._get_param("computeEnvironmentName")
        compute_resource = self._get_param("computeResources")
        service_role = self._get_param("serviceRole")
        state = self._get_param("state")
        _type = self._get_param("type")

        try:
            name, arn = self.batch_backend.create_compute_environment(
                compute_environment_name=compute_env_name,
                _type=_type,
                state=state,
                compute_resources=compute_resource,
                service_role=service_role,
            )
        except AWSError as err:
            return err.response()

        result = {"computeEnvironmentArn": arn, "computeEnvironmentName": name}

        return json.dumps(result)

    # DescribeComputeEnvironments
    def describecomputeenvironments(self):
        compute_environments = self._get_param("computeEnvironments")
        max_results = self._get_param("maxResults")  # Ignored, should be int
        next_token = self._get_param("nextToken")  # Ignored

        envs = self.batch_backend.describe_compute_environments(
            compute_environments, max_results=max_results, next_token=next_token
        )

        result = {"computeEnvironments": envs}
        return json.dumps(result)

    # DeleteComputeEnvironment
    def deletecomputeenvironment(self):
        compute_environment = self._get_param("computeEnvironment")

        try:
            self.batch_backend.delete_compute_environment(compute_environment)
        except AWSError as err:
            return err.response()

        return ""

    # UpdateComputeEnvironment
    def updatecomputeenvironment(self):
        compute_env_name = self._get_param("computeEnvironment")
        compute_resource = self._get_param("computeResources")
        service_role = self._get_param("serviceRole")
        state = self._get_param("state")

        try:
            name, arn = self.batch_backend.update_compute_environment(
                compute_environment_name=compute_env_name,
                compute_resources=compute_resource,
                service_role=service_role,
                state=state,
            )
        except AWSError as err:
            return err.response()

        result = {"computeEnvironmentArn": arn, "computeEnvironmentName": name}

        return json.dumps(result)

    # CreateJobQueue
    def createjobqueue(self):
        compute_env_order = self._get_param("computeEnvironmentOrder")
        queue_name = self._get_param("jobQueueName")
        priority = self._get_param("priority")
        state = self._get_param("state")

        try:
            name, arn = self.batch_backend.create_job_queue(
                queue_name=queue_name,
                priority=priority,
                state=state,
                compute_env_order=compute_env_order,
            )
        except AWSError as err:
            return err.response()

        result = {"jobQueueArn": arn, "jobQueueName": name}

        return json.dumps(result)

    # DescribeJobQueues
    def describejobqueues(self):
        job_queues = self._get_param("jobQueues")
        max_results = self._get_param("maxResults")  # Ignored, should be int
        next_token = self._get_param("nextToken")  # Ignored

        queues = self.batch_backend.describe_job_queues(
            job_queues, max_results=max_results, next_token=next_token
        )

        result = {"jobQueues": queues}
        return json.dumps(result)

    # UpdateJobQueue
    def updatejobqueue(self):
        compute_env_order = self._get_param("computeEnvironmentOrder")
        queue_name = self._get_param("jobQueue")
        priority = self._get_param("priority")
        state = self._get_param("state")

        try:
            name, arn = self.batch_backend.update_job_queue(
                queue_name=queue_name,
                priority=priority,
                state=state,
                compute_env_order=compute_env_order,
            )
        except AWSError as err:
            return err.response()

        result = {"jobQueueArn": arn, "jobQueueName": name}

        return json.dumps(result)

    # DeleteJobQueue
    def deletejobqueue(self):
        queue_name = self._get_param("jobQueue")

        self.batch_backend.delete_job_queue(queue_name)

        return ""

    # RegisterJobDefinition
    def registerjobdefinition(self):
        container_properties = self._get_param("containerProperties")
        def_name = self._get_param("jobDefinitionName")
        parameters = self._get_param("parameters")
        tags = self._get_param("tags")
        retry_strategy = self._get_param("retryStrategy")
        _type = self._get_param("type")
        timeout = self._get_param("timeout")
        try:
            name, arn, revision = self.batch_backend.register_job_definition(
                def_name=def_name,
                parameters=parameters,
                _type=_type,
                tags=tags,
                retry_strategy=retry_strategy,
                container_properties=container_properties,
                timeout=timeout,
            )
        except AWSError as err:
            return err.response()

        result = {
            "jobDefinitionArn": arn,
            "jobDefinitionName": name,
            "revision": revision,
        }

        return json.dumps(result)

    # DeregisterJobDefinition
    def deregisterjobdefinition(self):
        queue_name = self._get_param("jobDefinition")

        self.batch_backend.deregister_job_definition(queue_name)

        return ""

    # DescribeJobDefinitions
    def describejobdefinitions(self):
        job_def_name = self._get_param("jobDefinitionName")
        job_def_list = self._get_param("jobDefinitions")
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")
        status = self._get_param("status")

        job_defs = self.batch_backend.describe_job_definitions(
            job_def_name, job_def_list, status, max_results, next_token
        )

        result = {"jobDefinitions": [job.describe() for job in job_defs]}
        return json.dumps(result)

    # SubmitJob
    def submitjob(self):
        container_overrides = self._get_param("containerOverrides")
        depends_on = self._get_param("dependsOn")
        job_def = self._get_param("jobDefinition")
        job_name = self._get_param("jobName")
        job_queue = self._get_param("jobQueue")
        parameters = self._get_param("parameters")
        retries = self._get_param("retryStrategy")
        timeout = self._get_param("timeout")

        try:
            name, job_id = self.batch_backend.submit_job(
                job_name,
                job_def,
                job_queue,
                parameters=parameters,
                retries=retries,
                depends_on=depends_on,
                container_overrides=container_overrides,
                timeout=timeout,
            )
        except AWSError as err:
            return err.response()

        result = {"jobId": job_id, "jobName": name}

        return json.dumps(result)

    # DescribeJobs
    def describejobs(self):
        jobs = self._get_param("jobs")

        try:
            return json.dumps({"jobs": self.batch_backend.describe_jobs(jobs)})
        except AWSError as err:
            return err.response()

    # ListJobs
    def listjobs(self):
        job_queue = self._get_param("jobQueue")
        job_status = self._get_param("jobStatus")
        max_results = self._get_param("maxResults")
        next_token = self._get_param("nextToken")

        try:
            jobs = self.batch_backend.list_jobs(
                job_queue, job_status, max_results, next_token
            )
        except AWSError as err:
            return err.response()

        result = {"jobSummaryList": [job.describe_short() for job in jobs]}
        return json.dumps(result)

    # TerminateJob
    def terminatejob(self):
        job_id = self._get_param("jobId")
        reason = self._get_param("reason")

        try:
            self.batch_backend.terminate_job(job_id, reason)
        except AWSError as err:
            return err.response()

        return ""

    # CancelJob
    def canceljob(self,):
        job_id = self._get_param("jobId")
        reason = self._get_param("reason")
        self.batch_backend.cancel_job(job_id, reason)

        return ""
