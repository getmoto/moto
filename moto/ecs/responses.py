from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import ecs_backends


class EC2ContainerServiceResponse(BaseResponse):

    @property
    def ecs_backend(self):
        """
        ECS Backend

        :return: ECS Backend object
        :rtype: moto.ecs.models.EC2ContainerServiceBackend
        """
        return ecs_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

    def create_cluster(self):
        cluster_name = self._get_param('clusterName')
        if cluster_name is None:
            cluster_name = 'default'
        cluster = self.ecs_backend.create_cluster(cluster_name)
        return json.dumps({
            'cluster': cluster.response_object
        })

    def list_clusters(self):
        cluster_arns = self.ecs_backend.list_clusters()
        return json.dumps({
            'clusterArns': cluster_arns
            #  'nextToken': str(uuid.uuid4())
        })

    def describe_clusters(self):
        list_clusters_name = self._get_param('clusters')
        clusters = self.ecs_backend.describe_clusters(list_clusters_name)
        return json.dumps({
            'clusters': clusters,
            'failures': []
        })

    def delete_cluster(self):
        cluster_str = self._get_param('cluster')
        cluster = self.ecs_backend.delete_cluster(cluster_str)
        return json.dumps({
            'cluster': cluster.response_object
        })

    def register_task_definition(self):
        family = self._get_param('family')
        container_definitions = self._get_param('containerDefinitions')
        volumes = self._get_param('volumes')
        task_definition = self.ecs_backend.register_task_definition(
            family, container_definitions, volumes)
        return json.dumps({
            'taskDefinition': task_definition.response_object
        })

    def list_task_definitions(self):
        task_definition_arns = self.ecs_backend.list_task_definitions()
        return json.dumps({
            'taskDefinitionArns': task_definition_arns
            #  'nextToken': str(uuid.uuid4())
        })

    def describe_task_definition(self):
        task_definition_str = self._get_param('taskDefinition')
        data = self.ecs_backend.describe_task_definition(task_definition_str)
        return json.dumps({
            'taskDefinition': data.response_object,
            'failures': []
        })

    def deregister_task_definition(self):
        task_definition_str = self._get_param('taskDefinition')
        task_definition = self.ecs_backend.deregister_task_definition(
            task_definition_str)
        return json.dumps({
            'taskDefinition': task_definition.response_object
        })

    def run_task(self):
        cluster_str = self._get_param('cluster')
        overrides = self._get_param('overrides')
        task_definition_str = self._get_param('taskDefinition')
        count = self._get_int_param('count')
        started_by = self._get_param('startedBy')
        tasks = self.ecs_backend.run_task(
            cluster_str, task_definition_str, count, overrides, started_by)
        return json.dumps({
            'tasks': [task.response_object for task in tasks],
            'failures': []
        })

    def describe_tasks(self):
        cluster = self._get_param('cluster')
        tasks = self._get_param('tasks')
        data = self.ecs_backend.describe_tasks(cluster, tasks)
        return json.dumps({
            'tasks': [task.response_object for task in data],
            'failures': []
        })

    def start_task(self):
        cluster_str = self._get_param('cluster')
        overrides = self._get_param('overrides')
        task_definition_str = self._get_param('taskDefinition')
        container_instances = self._get_param('containerInstances')
        started_by = self._get_param('startedBy')
        tasks = self.ecs_backend.start_task(
            cluster_str, task_definition_str, container_instances, overrides, started_by)
        return json.dumps({
            'tasks': [task.response_object for task in tasks],
            'failures': []
        })

    def list_tasks(self):
        cluster_str = self._get_param('cluster')
        container_instance = self._get_param('containerInstance')
        family = self._get_param('family')
        started_by = self._get_param('startedBy')
        service_name = self._get_param('serviceName')
        desiredStatus = self._get_param('desiredStatus')
        task_arns = self.ecs_backend.list_tasks(
            cluster_str, container_instance, family, started_by, service_name, desiredStatus)
        return json.dumps({
            'taskArns': task_arns
        })

    def stop_task(self):
        cluster_str = self._get_param('cluster')
        task = self._get_param('task')
        reason = self._get_param('reason')
        task = self.ecs_backend.stop_task(cluster_str, task, reason)
        return json.dumps({
            'task': task.response_object
        })

    def create_service(self):
        cluster_str = self._get_param('cluster')
        service_name = self._get_param('serviceName')
        task_definition_str = self._get_param('taskDefinition')
        desired_count = self._get_int_param('desiredCount')
        load_balancers = self._get_param('loadBalancers')
        service = self.ecs_backend.create_service(
            cluster_str, service_name, task_definition_str, desired_count, load_balancers)
        return json.dumps({
            'service': service.response_object
        })

    def list_services(self):
        cluster_str = self._get_param('cluster')
        service_arns = self.ecs_backend.list_services(cluster_str)
        return json.dumps({
            'serviceArns': service_arns
            # ,
            # 'nextToken': str(uuid.uuid4())
        })

    def describe_services(self):
        cluster_str = self._get_param('cluster')
        service_names = self._get_param('services')
        services = self.ecs_backend.describe_services(
            cluster_str, service_names)
        return json.dumps({
            'services': [service.response_object for service in services],
            'failures': []
        })

    def update_service(self):
        cluster_str = self._get_param('cluster')
        service_name = self._get_param('service')
        task_definition = self._get_param('taskDefinition')
        desired_count = self._get_int_param('desiredCount')
        service = self.ecs_backend.update_service(
            cluster_str, service_name, task_definition, desired_count)
        return json.dumps({
            'service': service.response_object
        })

    def delete_service(self):
        service_name = self._get_param('service')
        cluster_name = self._get_param('cluster')
        service = self.ecs_backend.delete_service(cluster_name, service_name)
        return json.dumps({
            'service': service.response_object
        })

    def register_container_instance(self):
        cluster_str = self._get_param('cluster')
        instance_identity_document_str = self._get_param(
            'instanceIdentityDocument')
        instance_identity_document = json.loads(instance_identity_document_str)
        ec2_instance_id = instance_identity_document["instanceId"]
        container_instance = self.ecs_backend.register_container_instance(
            cluster_str, ec2_instance_id)
        return json.dumps({
            'containerInstance': container_instance.response_object
        })

    def deregister_container_instance(self):
        cluster_str = self._get_param('cluster')
        if not cluster_str:
            cluster_str = 'default'
        container_instance_str = self._get_param('containerInstance')
        force = self._get_param('force')
        container_instance, failures = self.ecs_backend.deregister_container_instance(
            cluster_str, container_instance_str, force
        )
        return json.dumps({
            'containerInstance': container_instance.response_object
        })

    def list_container_instances(self):
        cluster_str = self._get_param('cluster')
        container_instance_arns = self.ecs_backend.list_container_instances(
            cluster_str)
        return json.dumps({
            'containerInstanceArns': container_instance_arns
        })

    def describe_container_instances(self):
        cluster_str = self._get_param('cluster')
        list_container_instance_arns = self._get_param('containerInstances')
        container_instances, failures = self.ecs_backend.describe_container_instances(
            cluster_str, list_container_instance_arns)
        return json.dumps({
            'failures': [ci.response_object for ci in failures],
            'containerInstances': [ci.response_object for ci in container_instances]
        })

    def update_container_instances_state(self):
        cluster_str = self._get_param('cluster')
        list_container_instance_arns = self._get_param('containerInstances')
        status_str = self._get_param('status')
        container_instances, failures = self.ecs_backend.update_container_instances_state(cluster_str,
                                                                                          list_container_instance_arns,
                                                                                          status_str)
        return json.dumps({
            'failures': [ci.response_object for ci in failures],
            'containerInstances': [ci.response_object for ci in container_instances]
        })

    def put_attributes(self):
        cluster_name = self._get_param('cluster')
        attributes = self._get_param('attributes')

        self.ecs_backend.put_attributes(cluster_name, attributes)

        return json.dumps({'attributes': attributes})

    def list_attributes(self):
        cluster_name = self._get_param('cluster')
        attr_name = self._get_param('attributeName')
        attr_value = self._get_param('attributeValue')
        target_type = self._get_param('targetType')
        max_results = self._get_param('maxResults')
        next_token = self._get_param('nextToken')

        results = self.ecs_backend.list_attributes(target_type, cluster_name, attr_name, attr_value, max_results, next_token)
        # Result will be [item will be {0 cluster_name, 1 arn, 2 name, 3 value}]

        formatted_results = []
        for _, arn, name, value in results:
            tmp_result = {
                'name': name,
                'targetId': arn
            }
            if value is not None:
                tmp_result['value'] = value
            formatted_results.append(tmp_result)

        return json.dumps({'attributes': formatted_results})

    def delete_attributes(self):
        cluster_name = self._get_param('cluster')
        attributes = self._get_param('attributes')

        self.ecs_backend.delete_attributes(cluster_name, attributes)

        return json.dumps({'attributes': attributes})

    def discover_poll_endpoint(self):
        # Here are the arguments, this api is used by the ecs client so obviously no decent
        # documentation. Hence I've responded with valid but useless data
        # cluster_name = self._get_param('cluster')
        # instance = self._get_param('containerInstance')
        return json.dumps({
            'endpoint': 'http://localhost',
            'telemetryEndpoint': 'http://localhost'
        })

    def list_task_definition_families(self):
        family_prefix = self._get_param('familyPrefix')
        status = self._get_param('status')
        max_results = self._get_param('maxResults')
        next_token = self._get_param('nextToken')

        results = self.ecs_backend.list_task_definition_families(family_prefix, status, max_results, next_token)

        return json.dumps({'families': list(results)})
