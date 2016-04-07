from __future__ import unicode_literals
import uuid

from moto.core import BaseBackend
from moto.ec2 import ec2_backends


class BaseObject(object):
    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split('_')):
            if i > 0:
                words.append(word.title())
            else:
                words.append(word)
        return ''.join(words)

    def gen_response_object(self):
        response_object = self.__dict__.copy()
        for key, value in response_object.items():
            if '_' in key:
                response_object[self.camelCase(key)] = value
                del response_object[key]
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class Cluster(BaseObject):
    def __init__(self, cluster_name):
        self.active_services_count = 0
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:cluster/{0}'.format(cluster_name)
        self.name = cluster_name
        self.pending_tasks_count = 0
        self.registered_container_instances_count = 0
        self.running_tasks_count = 0
        self.status = 'ACTIVE'

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['clusterArn'] = self.arn
        response_object['clusterName'] = self.name
        del response_object['arn'], response_object['name']
        return response_object


class TaskDefinition(BaseObject):
    def __init__(self, family, revision, container_definitions, volumes=None):
        self.family = family
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:task-definition/{0}:{1}'.format(family, revision)
        self.container_definitions = container_definitions
        if volumes is not None:
            self.volumes = volumes

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['taskDefinitionArn'] = response_object['arn']
        del response_object['arn']
        return response_object


class Service(BaseObject):
    def __init__(self, cluster, service_name, task_definition, desired_count):
        self.cluster_arn = cluster.arn
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:service/{0}'.format(service_name)
        self.name = service_name
        self.status = 'ACTIVE'
        self.running_count = 0
        self.task_definition = task_definition.arn
        self.desired_count = desired_count
        self.events = []
        self.load_balancers = []
        self.pending_count = 0

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        del response_object['name'], response_object['arn']
        response_object['serviceName'] = self.name
        response_object['serviceArn'] = self.arn
        return response_object


class EC2ContainerServiceBackend(BaseBackend):
    def __init__(self):
        self.clusters = {}
        self.task_definitions = {}
        self.services = {}

    def fetch_task_definition(self, task_definition_str):
        task_definition_components = task_definition_str.split(':')
        if len(task_definition_components) == 2:
            family, revision = task_definition_components
            revision = int(revision)
        else:
            family = task_definition_components[0]
            revision = -1
        if family in self.task_definitions and 0 < revision <= len(self.task_definitions[family]):
            return self.task_definitions[family][revision - 1]
        elif family in self.task_definitions and revision == -1:
            return self.task_definitions[family][revision]
        else:
            raise Exception("{0} is not a task_definition".format(task_definition_str))

    def create_cluster(self, cluster_name):
        cluster = Cluster(cluster_name)
        self.clusters[cluster_name] = cluster
        return cluster

    def list_clusters(self):
        """
        maxSize and pagination not implemented
        """
        return [cluster.arn for cluster in self.clusters.values()]

    def describe_clusters(self, list_clusters_name=None):
        list_clusters = []
        if list_clusters_name is None:
            if 'default' in self.clusters:
                list_clusters.append(self.clusters['default'].response_object)
        else:
            for cluster in list_clusters_name:
                cluster_name = cluster.split('/')[-1]
                if cluster_name in self.clusters:
                    list_clusters.append(self.clusters[cluster_name].response_object)
                else:
                    raise Exception("{0} is not a cluster".format(cluster_name))
        return list_clusters

    def delete_cluster(self, cluster_str):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            return self.clusters.pop(cluster_name)
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))

    def register_task_definition(self, family, container_definitions, volumes):
        if family in self.task_definitions:
            revision = len(self.task_definitions[family]) + 1
        else:
            self.task_definitions[family] = []
            revision = 1
        task_definition = TaskDefinition(family, revision, container_definitions, volumes)
        self.task_definitions[family].append(task_definition)

        return task_definition

    def list_task_definitions(self):
        """
        Filtering not implemented
        """
        task_arns = []
        for task_definition_list in self.task_definitions.values():
            task_arns.extend([task_definition.arn for task_definition in task_definition_list])
        return task_arns

    def deregister_task_definition(self, task_definition_str):
        task_definition_name = task_definition_str.split('/')[-1]
        family, revision = task_definition_name.split(':')
        revision = int(revision)
        if family in self.task_definitions and 0 < revision <= len(self.task_definitions[family]):
            return self.task_definitions[family].pop(revision - 1)
        else:
            raise Exception("{0} is not a task_definition".format(task_definition_name))

    def create_service(self, cluster_str, service_name, task_definition_str, desired_count):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        task_definition = self.fetch_task_definition(task_definition_str)
        desired_count = desired_count if desired_count is not None else 0
        service = Service(cluster, service_name, task_definition, desired_count)
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        self.services[cluster_service_pair] = service
        return service

    def list_services(self, cluster_str):
        cluster_name = cluster_str.split('/')[-1]
        service_arns = []
        for key, value in self.services.items():
            if cluster_name + ':' in key:
                service_arns.append(self.services[key].arn)
        return sorted(service_arns)

    def update_service(self, cluster_str, service_name, task_definition_str, desired_count):
        cluster_name = cluster_str.split('/')[-1]
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            if task_definition_str is not None:
                task_definition = self.fetch_task_definition(task_definition_str)
                self.services[cluster_service_pair].task_definition = task_definition
            if desired_count is not None:
                self.services[cluster_service_pair].desired_count = desired_count
            return self.services[cluster_service_pair]
        else:
            raise Exception("cluster {0} or service {1} does not exist".format(cluster_name, service_name))

    def delete_service(self, cluster_name, service_name):
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            service = self.services[cluster_service_pair]
            if service.desired_count > 0:
                raise Exception("Service must have desiredCount=0")
            else:
                return self.services.pop(cluster_service_pair)
        else:
            raise Exception("cluster {0} or service {1} does not exist".format(cluster_name, service_name))


ecs_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecs_backends[region] = EC2ContainerServiceBackend()
