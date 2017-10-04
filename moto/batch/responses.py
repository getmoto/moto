from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import batch_backends
from six.moves.urllib.parse import urlsplit

from .exceptions import AWSError

import json


class BatchResponse(BaseResponse):
    def _error(self, code, message):
        return json.dumps({'__type': code, 'message': message}), dict(status=400)

    @property
    def batch_backend(self):
        """
        :return: Batch Backend
        :rtype: moto.batch.models.BatchBackend
        """
        return batch_backends[self.region]

    @property
    def json(self):
        if self.body is None or self.body == '':
            self._json = {}
        elif not hasattr(self, '_json'):
            try:
                self._json = json.loads(self.body)
            except json.JSONDecodeError:
                print()
        return self._json

    def _get_param(self, param_name, if_none=None):
        val = self.json.get(param_name)
        if val is not None:
            return val
        return if_none

    def _get_action(self):
        # Return element after the /v1/*
        return urlsplit(self.uri).path.lstrip('/').split('/')[1]

    # CreateComputeEnvironment
    def createcomputeenvironment(self):
        compute_env_name = self._get_param('computeEnvironmentName')
        compute_resource = self._get_param('computeResources')
        service_role = self._get_param('serviceRole')
        state = self._get_param('state')
        _type = self._get_param('type')

        try:
            name, arn = self.batch_backend.create_compute_environment(
                compute_environment_name=compute_env_name,
                _type=_type, state=state,
                compute_resources=compute_resource,
                service_role=service_role
            )
        except AWSError as err:
            return err.response()

        result = {
            'computeEnvironmentArn': arn,
            'computeEnvironmentName': name
        }

        return json.dumps(result)

    # DescribeComputeEnvironments
    def describecomputeenvironments(self):
        compute_environments = self._get_param('computeEnvironments')
        max_results = self._get_param('maxResults')  # Ignored, should be int
        next_token = self._get_param('nextToken')  # Ignored

        envs = self.batch_backend.describe_compute_environments(compute_environments, max_results=max_results, next_token=next_token)

        result = {'computeEnvironments': envs}
        return json.dumps(result)

    # DeleteComputeEnvironment
    def deletecomputeenvironment(self):
        compute_environment = self._get_param('computeEnvironment')

        try:
            self.batch_backend.delete_compute_environment(compute_environment)
        except AWSError as err:
            return err.response()

        return ''

    # UpdateComputeEnvironment
    def updatecomputeenvironment(self):
        compute_env_name = self._get_param('computeEnvironment')
        compute_resource = self._get_param('computeResources')
        service_role = self._get_param('serviceRole')
        state = self._get_param('state')

        try:
            name, arn = self.batch_backend.update_compute_environment(
                compute_environment_name=compute_env_name,
                compute_resources=compute_resource,
                service_role=service_role,
                state=state
            )
        except AWSError as err:
            return err.response()

        result = {
            'computeEnvironmentArn': arn,
            'computeEnvironmentName': name
        }

        return json.dumps(result)

    # CreateJobQueue
    def createjobqueue(self):
        compute_env_order = self._get_param('computeEnvironmentOrder')
        queue_name = self._get_param('jobQueueName')
        priority = self._get_param('priority')
        state = self._get_param('state')

        try:
            name, arn = self.batch_backend.create_job_queue(
                queue_name=queue_name,
                priority=priority,
                state=state,
                compute_env_order=compute_env_order
            )
        except AWSError as err:
            return err.response()

        result = {
            'jobQueueArn': arn,
            'jobQueueName': name
        }

        return json.dumps(result)

    # DescribeJobQueues
    def describejobqueues(self):
        job_queues = self._get_param('jobQueues')
        max_results = self._get_param('maxResults')  # Ignored, should be int
        next_token = self._get_param('nextToken')  # Ignored

        queues = self.batch_backend.describe_job_queues(job_queues, max_results=max_results, next_token=next_token)

        result = {'jobQueues': queues}
        return json.dumps(result)

    # UpdateJobQueue
    def updatejobqueue(self):
        compute_env_order = self._get_param('computeEnvironmentOrder')
        queue_name = self._get_param('jobQueue')
        priority = self._get_param('priority')
        state = self._get_param('state')

        try:
            name, arn = self.batch_backend.update_job_queue(
                queue_name=queue_name,
                priority=priority,
                state=state,
                compute_env_order=compute_env_order
            )
        except AWSError as err:
            return err.response()

        result = {
            'jobQueueArn': arn,
            'jobQueueName': name
        }

        return json.dumps(result)

    # DeleteJobQueue
    def deletejobqueue(self):
        queue_name = self._get_param('jobQueue')

        self.batch_backend.delete_job_queue(queue_name)

        return ''

    # RegisterJobDefinition
    def registerjobdefinition(self):
        container_properties = self._get_param('containerProperties')
        def_name = self._get_param('jobDefinitionName')
        parameters = self._get_param('parameters')
        retry_strategy = self._get_param('retryStrategy')
        _type = self._get_param('type')

        try:
            name, arn, revision = self.batch_backend.register_job_definition(
                def_name=def_name,
                parameters=parameters,
                _type=_type,
                retry_strategy=retry_strategy,
                container_properties=container_properties
            )
        except AWSError as err:
            return err.response()

        result = {
            'jobDefinitionArn': arn,
            'jobDefinitionName': name,
            'revision': revision
        }

        return json.dumps(result)
