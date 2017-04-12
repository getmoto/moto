from __future__ import unicode_literals
import uuid
from random import random

from moto.core import BaseBackend
from moto.ec2 import ec2_backends
from copy import copy


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
        response_object = copy(self.__dict__)
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
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:cluster/{0}'.format(
            cluster_name)
        self.name = cluster_name
        self.pending_tasks_count = 0
        self.registered_container_instances_count = 0
        self.running_tasks_count = 0
        self.status = 'ACTIVE'

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['clusterArn'] = self.arn
        response_object['clusterName'] = self.name
        del response_object['arn'], response_object['name']
        return response_object

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ecs_backend = ecs_backends[region_name]
        return ecs_backend.create_cluster(
            # ClusterName is optional in CloudFormation, thus create a random
            # name if necessary
            cluster_name=properties.get(
                'ClusterName', 'ecscluster{0}'.format(int(random() * 10 ** 6))),
        )

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        if original_resource.name != properties['ClusterName']:
            ecs_backend = ecs_backends[region_name]
            ecs_backend.delete_cluster(original_resource.arn)
            return ecs_backend.create_cluster(
                # ClusterName is optional in CloudFormation, thus create a
                # random name if necessary
                cluster_name=properties.get(
                    'ClusterName', 'ecscluster{0}'.format(int(random() * 10 ** 6))),
            )
        else:
            # no-op when nothing changed between old and new resources
            return original_resource


class TaskDefinition(BaseObject):

    def __init__(self, family, revision, container_definitions, volumes=None):
        self.family = family
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:task-definition/{0}:{1}'.format(
            family, revision)
        self.container_definitions = container_definitions
        if volumes is None:
            self.volumes = []
        else:
            self.volumes = volumes

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['taskDefinitionArn'] = response_object['arn']
        del response_object['arn']
        return response_object

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        family = properties.get(
            'Family', 'task-definition-{0}'.format(int(random() * 10 ** 6)))
        container_definitions = properties['ContainerDefinitions']
        volumes = properties['Volumes']

        ecs_backend = ecs_backends[region_name]
        return ecs_backend.register_task_definition(
            family=family, container_definitions=container_definitions, volumes=volumes)

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        family = properties.get(
            'Family', 'task-definition-{0}'.format(int(random() * 10 ** 6)))
        container_definitions = properties['ContainerDefinitions']
        volumes = properties['Volumes']
        if (original_resource.family != family or
            original_resource.container_definitions != container_definitions or
            original_resource.volumes != volumes
            # currently TaskRoleArn isn't stored at TaskDefinition instances
            ):
            ecs_backend = ecs_backends[region_name]
            ecs_backend.deregister_task_definition(original_resource.arn)
            return ecs_backend.register_task_definition(
                family=family, container_definitions=container_definitions, volumes=volumes)
        else:
            # no-op when nothing changed between old and new resources
            return original_resource


class ContainerDefinition(BaseObject):
    def __init__(self, name, image, cpu=0, memory=0, memoryReservation=0, links=[],
                 portMappings=[], essential=True, entryPoint=[], command=[], environment=[],
                 mountPoints=[], volumesFrom=[], hostname='', user='', workingDirectory='',
                 disableNetworking=False, privileged=False, readonlyRootFilesystem=False,
                 dnsServers=[], dnsSearchDomains=[], extraHosts=[], dockerSecurityOptions=[],
                 dockerLabels={}, uLimits=[], logConfiguration={}):
        self.name = name
        self.image = image
        self.cpu = cpu
        self.memory = memory
        self.memory_reservation = memoryReservation
        self.links = links
        self.portMappings = portMappings
        self.essential = essential
        self.entryPoint = entryPoint
        self.command = command
        self.environment = environment
        self.mountPoints = mountPoints
        self.volumesFrom = volumesFrom
        self.hostname = hostname
        self.user = user
        self.working_directory = workingDirectory
        self.disable_networking = disableNetworking
        self.priviliged = privileged
        self.readonly_root_filesystem = readonlyRootFilesystem
        self.dns_servers = dnsServers
        self.dns_search_domains = dnsSearchDomains
        self.extra_hosts = extraHosts
        self.docker_security_options = dockerSecurityOptions
        self.docker_labels = dockerLabels
        self.u_limits = uLimits
        self.log_configuration = logConfiguration

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return response_object


class Task(BaseObject):

    def __init__(self, cluster, task_definition, container_instance_arn, resource_requirements, overrides={}, started_by=''):
        self.cluster_arn = cluster.arn
        self.task_arn = 'arn:aws:ecs:us-east-1:012345678910:task/{0}'.format(
            str(uuid.uuid1()))
        self.container_instance_arn = container_instance_arn
        self.last_status = 'RUNNING'
        self.desired_status = 'RUNNING'
        self.task_definition_arn = task_definition.arn
        self.overrides = overrides
        self.containers = []
        self.started_by = started_by
        self.stopped_reason = ''
        self.resource_requirements = {
            'CPU': 0,
            'MEMORY': 0,
            'PORTS': []
        }
        

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return response_object


class Service(BaseObject):

    def __init__(self, cluster, service_name, task_definition, desired_count):
        self.cluster_arn = cluster.arn
        self.arn = 'arn:aws:ecs:us-east-1:012345678910:service/{0}'.format(
            service_name)
        self.name = service_name
        self.status = 'ACTIVE'
        self.running_count = 0
        self.task_definition = task_definition.arn
        self.desired_count = desired_count
        self.events = []
        self.load_balancers = []
        self.pending_count = 0

    @property
    def physical_resource_id(self):
        return self.arn

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        del response_object['name'], response_object['arn']
        response_object['serviceName'] = self.name
        response_object['serviceArn'] = self.arn
        return response_object

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        if isinstance(properties['Cluster'], Cluster):
            cluster = properties['Cluster'].name
        else:
            cluster = properties['Cluster']
        if isinstance(properties['TaskDefinition'], TaskDefinition):
            task_definition = properties['TaskDefinition'].family
        else:
            task_definition = properties['TaskDefinition']
        service_name = '{0}Service{1}'.format(cluster, int(random() * 10 ** 6))
        desired_count = properties['DesiredCount']
        # TODO: LoadBalancers
        # TODO: Role

        ecs_backend = ecs_backends[region_name]
        return ecs_backend.create_service(
            cluster, service_name, task_definition, desired_count)

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        if isinstance(properties['Cluster'], Cluster):
            cluster_name = properties['Cluster'].name
        else:
            cluster_name = properties['Cluster']
        if isinstance(properties['TaskDefinition'], TaskDefinition):
            task_definition = properties['TaskDefinition'].family
        else:
            task_definition = properties['TaskDefinition']
        desired_count = properties['DesiredCount']

        ecs_backend = ecs_backends[region_name]
        service_name = original_resource.name
        if original_resource.cluster_arn != Cluster(cluster_name).arn:
            # TODO: LoadBalancers
            # TODO: Role
            ecs_backend.delete_service(cluster_name, service_name)
            new_service_name = '{0}Service{1}'.format(
                cluster_name, int(random() * 10 ** 6))
            return ecs_backend.create_service(
                cluster_name, new_service_name, task_definition, desired_count)
        else:
            return ecs_backend.update_service(cluster_name, service_name, task_definition, desired_count)


class ContainerInstance(BaseObject):

    def __init__(self, ec2_instance_id):
        self.ec2_instance_id = ec2_instance_id
        self.status = 'ACTIVE'
        self.registeredResources = [
            {'doubleValue': 0.0,
             'integerValue': 4096,
             'longValue': 0,
             'name': 'CPU',
             'type': 'INTEGER'},
            {'doubleValue': 0.0,
             'integerValue': 7482,
             'longValue': 0,
             'name': 'MEMORY',
             'type': 'INTEGER'},
            {'doubleValue': 0.0,
             'integerValue': 0,
             'longValue': 0,
             'name': 'PORTS',
             'stringSetValue': ['22', '2376', '2375', '51678', '51679'],
             'type': 'STRINGSET'},
            {'doubleValue': 0.0,
             'integerValue': 0,
             'longValue': 0,
             'name': 'PORTS_UDP',
             'stringSetValue': [],
             'type': 'STRINGSET'}]
        self.agentConnected = True
        self.containerInstanceArn = "arn:aws:ecs:us-east-1:012345678910:container-instance/{0}".format(
            str(uuid.uuid1()))
        self.pendingTaskCount = 0
        self.remainingResources = [
            {'doubleValue': 0.0,
             'integerValue': 4096,
             'longValue': 0,
             'name': 'CPU',
             'type': 'INTEGER'},
            {'doubleValue': 0.0,
             'integerValue': 7482,
             'longValue': 0,
             'name': 'MEMORY',
             'type': 'INTEGER'},
            {'doubleValue': 0.0,
             'integerValue': 0,
             'longValue': 0,
             'name': 'PORTS',
             'stringSetValue': ['22', '2376', '2375', '51678', '51679'],
             'type': 'STRINGSET'},
            {'doubleValue': 0.0,
             'integerValue': 0,
             'longValue': 0,
             'name': 'PORTS_UDP',
             'stringSetValue': [],
             'type': 'STRINGSET'}
        ]
        self.runningTaskCount = 0
        self.versionInfo = {
            'agentVersion': "1.0.0",
            'agentHash': '4023248',
            'dockerVersion': 'DockerVersion: 1.5.0'
        }
            

        @property
        def response_object(self):
            response_object = self.gen_response_object()
            del response_object['name'], response_object['arn']
            return response_object


class ContainerInstanceFailure(BaseObject):

    def __init__(self, reason, container_instance_id):
        self.reason = reason
        self.arn = "arn:aws:ecs:us-east-1:012345678910:container-instance/{0}".format(
            container_instance_id)

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object['reason'] = self.reason
        response_object['arn'] = self.arn
        return response_object


class EC2ContainerServiceBackend(BaseBackend):

    def __init__(self):
        self.clusters = {}
        self.task_definitions = {}
        self.tasks = {}
        self.services = {}
        self.container_instances = {}

    def describe_task_definition(self, task_definition_str):
        task_definition_name = task_definition_str.split('/')[-1]
        if ':' in task_definition_name:
            family, revision = task_definition_name.split(':')
            revision = int(revision)
        else:
            family = task_definition_name
            revision = len(self.task_definitions.get(family, []))

        if family in self.task_definitions and 0 < revision <= len(self.task_definitions[family]):
            return self.task_definitions[family][revision - 1]
        elif family in self.task_definitions and revision == -1:
            return self.task_definitions[family][revision]
        else:
            raise Exception(
                "{0} is not a task_definition".format(task_definition_name))

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
                    list_clusters.append(
                        self.clusters[cluster_name].response_object)
                else:
                    raise Exception(
                        "{0} is not a cluster".format(cluster_name))
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
        task_definition = TaskDefinition(
            family, revision, container_definitions, volumes)
        self.task_definitions[family].append(task_definition)

        return task_definition

    def list_task_definitions(self):
        """
        Filtering not implemented
        """
        task_arns = []
        for task_definition_list in self.task_definitions.values():
            task_arns.extend(
                [task_definition.arn for task_definition in task_definition_list])
        return task_arns

    def deregister_task_definition(self, task_definition_str):
        task_definition_name = task_definition_str.split('/')[-1]
        family, revision = task_definition_name.split(':')
        revision = int(revision)
        if family in self.task_definitions and 0 < revision <= len(self.task_definitions[family]):
            return self.task_definitions[family].pop(revision - 1)
        else:
            raise Exception(
                "{0} is not a task_definition".format(task_definition_name))

    def run_task(self, cluster_str, task_definition_str, count, overrides, started_by):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        task_definition = self.describe_task_definition(task_definition_str)
        if cluster_name not in self.tasks:
            self.tasks[cluster_name] = {}
        tasks = []
        container_instances = list(
            self.container_instances.get(cluster_name, {}).keys())
        if not container_instances:
            raise Exception("No instances found in cluster {}".format(cluster_name))
        active_container_instances = [x for x in container_instances if
                                      self.container_instances[cluster_name][x].status == 'ACTIVE']
        resource_requirements = self._calculate_task_resource_requirements(task_definition)
        # TODO: return event about unable to place task if not able to place enough tasks to meet count
        placed_count = 0
        for container_instance in active_container_instances:
            container_instance = self.container_instances[cluster_name][container_instance]
            container_instance_arn = container_instance.containerInstanceArn
            try_to_place = True
            while try_to_place:
                can_be_placed, message = self._can_be_placed(container_instance, resource_requirements)
                if can_be_placed:
                    task = Task(cluster, task_definition, container_instance_arn, resource_requirements, overrides or {}, started_by or '')
                    self.update_container_instance_resources(container_instance, resource_requirements)
                    tasks.append(task)
                    self.tasks[cluster_name][task.task_arn] = task
                    placed_count += 1
                    if placed_count == count:
                        return tasks
                else:
                    try_to_place = False
        return tasks

    @staticmethod
    def _calculate_task_resource_requirements(task_definition):
        resource_requirements = {"CPU": 0, "MEMORY": 0, "PORTS": [], "PORTS_UDP": []}
        for container_definition in task_definition.container_definitions:
            resource_requirements["CPU"] += container_definition.get('cpu')
            resource_requirements["MEMORY"] += container_definition.get("memory")
            for port_mapping in container_definition.get("portMappings", []):
                resource_requirements["PORTS"].append(port_mapping.get('hostPort'))
        return resource_requirements


    @staticmethod
    def _can_be_placed(container_instance, task_resource_requirements):
        """

        :param container_instance: The container instance trying to be placed onto
        :param task_resource_requirements: The calculated resource requirements of the task in the form of a dict
        :return: A boolean stating whether the given container instance has enough resources to have the task placed on
        it as well as a description, if it cannot be placed this will describe why.
        """
        # TODO: Implement default and other placement strategies as well as constraints: 
        # docs.aws.amazon.com/AmazonECS/latest/developerguide/task-placement.html
        remaining_cpu = 0
        remaining_memory = 0
        reserved_ports = []
        for resource in container_instance.remainingResources:
            if resource.get("name") == "CPU":
                remaining_cpu = resource.get("integerValue")
            elif resource.get("name") == "MEMORY":
                remaining_memory = resource.get("integerValue")
            elif resource.get("name") == "PORTS":
                reserved_ports = resource.get("stringSetValue")
        if task_resource_requirements.get("CPU") > remaining_cpu:
            return False, "Not enough CPU credits"
        if task_resource_requirements.get("MEMORY") > remaining_memory:
            return False, "Not enough memory"
        ports_needed = task_resource_requirements.get("PORTS")
        for port in ports_needed:
            if str(port) in reserved_ports:
                return False, "Port clash"
        return True, "Can be placed"

    def start_task(self, cluster_str, task_definition_str, container_instances, overrides, started_by):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        task_definition = self.describe_task_definition(task_definition_str)
        if cluster_name not in self.tasks:
            self.tasks[cluster_name] = {}
        tasks = []
        if not container_instances:
            raise Exception("No container instance list provided")

        container_instance_ids = [x.split('/')[-1]
                                  for x in container_instances]
        resource_requirements = self._calculate_task_resource_requirements(task_definition)
        for container_instance_id in container_instance_ids:
            container_instance_arn = self.container_instances[cluster_name][
                container_instance_id
            ].containerInstanceArn
            task = Task(cluster, task_definition, container_instance_arn, resource_requirements,
                        overrides or {}, started_by or '')
            tasks.append(task)
            self.tasks[cluster_name][task.task_arn] = task
        return tasks

    def describe_tasks(self, cluster_str, tasks):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        if not tasks:
            raise Exception("tasks cannot be empty")
        response = []
        for cluster, cluster_tasks in self.tasks.items():
            for task_id, task in cluster_tasks.items():
                if task_id in tasks or task.task_arn in tasks:
                    response.append(task)
        return response

    def list_tasks(self, cluster_str, container_instance, family, started_by, service_name, desiredStatus):
        filtered_tasks = []
        for cluster, tasks in self.tasks.items():
            for arn, task in tasks.items():
                filtered_tasks.append(task)
        if cluster_str:
            cluster_name = cluster_str.split('/')[-1]
            if cluster_name not in self.clusters:
                raise Exception("{0} is not a cluster".format(cluster_name))
            filtered_tasks = list(
                filter(lambda t: cluster_name in t.cluster_arn, filtered_tasks))

        if container_instance:
            filtered_tasks = list(filter(
                lambda t: container_instance in t.container_instance_arn, filtered_tasks))

        if started_by:
            filtered_tasks = list(
                filter(lambda t: started_by == t.started_by, filtered_tasks))
        return [t.task_arn for t in filtered_tasks]

    def stop_task(self, cluster_str, task_str, reason):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))

        if not task_str:
            raise Exception("A task ID or ARN is required")
        task_id = task_str.split('/')[-1]
        tasks = self.tasks.get(cluster_name, None)
        if not tasks:
            raise Exception(
                "Cluster {} has no registered tasks".format(cluster_name))
        for task in tasks.keys():
            if task.endswith(task_id):
                container_instance_arn = tasks[task].container_instance_arn
                container_instance = self.container_instances[cluster_name][container_instance_arn.split('/')[-1]]
                self.update_container_instance_resources(container_instance, tasks[task].resource_requirements, removing=True)
                tasks[task].last_status = 'STOPPED'
                tasks[task].desired_status = 'STOPPED'
                tasks[task].stopped_reason = reason
                return tasks[task]
        raise Exception("Could not find task {} on cluster {}".format(
            task_str, cluster_name))

    def create_service(self, cluster_str, service_name, task_definition_str, desired_count):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        task_definition = self.describe_task_definition(task_definition_str)
        desired_count = desired_count if desired_count is not None else 0
        service = Service(cluster, service_name,
                          task_definition, desired_count)
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

    def describe_services(self, cluster_str, service_names_or_arns):
        cluster_name = cluster_str.split('/')[-1]
        result = []
        for existing_service_name, existing_service_obj in sorted(self.services.items()):
            for requested_name_or_arn in service_names_or_arns:
                cluster_service_pair = '{0}:{1}'.format(
                    cluster_name, requested_name_or_arn)
                if cluster_service_pair == existing_service_name or existing_service_obj.arn == requested_name_or_arn:
                    result.append(existing_service_obj)
        return result

    def update_service(self, cluster_str, service_name, task_definition_str, desired_count):
        cluster_name = cluster_str.split('/')[-1]
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            if task_definition_str is not None:
                self.describe_task_definition(task_definition_str)
                self.services[
                    cluster_service_pair].task_definition = task_definition_str
            if desired_count is not None:
                self.services[
                    cluster_service_pair].desired_count = desired_count
            return self.services[cluster_service_pair]
        else:
            raise Exception("cluster {0} or service {1} does not exist".format(
                cluster_name, service_name))

    def delete_service(self, cluster_name, service_name):
        cluster_service_pair = '{0}:{1}'.format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            service = self.services[cluster_service_pair]
            if service.desired_count > 0:
                raise Exception("Service must have desiredCount=0")
            else:
                return self.services.pop(cluster_service_pair)
        else:
            raise Exception("cluster {0} or service {1} does not exist".format(
                cluster_name, service_name))

    def register_container_instance(self, cluster_str, ec2_instance_id):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        container_instance = ContainerInstance(ec2_instance_id)
        if not self.container_instances.get(cluster_name):
            self.container_instances[cluster_name] = {}
        container_instance_id = container_instance.containerInstanceArn.split(
            '/')[-1]
        self.container_instances[cluster_name][
            container_instance_id] = container_instance
        return container_instance

    def list_container_instances(self, cluster_str):
        cluster_name = cluster_str.split('/')[-1]
        container_instances_values = self.container_instances.get(
            cluster_name, {}).values()
        container_instances = [
            ci.containerInstanceArn for ci in container_instances_values]
        return sorted(container_instances)

    def describe_container_instances(self, cluster_str, list_container_instance_ids):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        failures = []
        container_instance_objects = []
        for container_instance_id in list_container_instance_ids:
            container_instance = self.container_instances[
                cluster_name].get(container_instance_id, None)
            if container_instance is not None:
                container_instance_objects.append(container_instance)
            else:
                failures.append(ContainerInstanceFailure(
                    'MISSING', container_instance_id))

        return container_instance_objects, failures

    def update_container_instances_state(self, cluster_str, list_container_instance_ids, status):
        cluster_name = cluster_str.split('/')[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        status = status.upper()
        if status not in ['ACTIVE', 'DRAINING']:
            raise Exception("An error occurred (InvalidParameterException) when calling the UpdateContainerInstancesState operation: \
                            Container instances status should be one of [ACTIVE,DRAINING]")
        failures = []
        container_instance_objects = []
        for container_instance_id in list_container_instance_ids:
            container_instance = self.container_instances[cluster_name].get(container_instance_id, None)
            if container_instance is not None:
                container_instance.status = status
                container_instance_objects.append(container_instance)
            else:
                failures.append(ContainerInstanceFailure('MISSING', container_instance_id))

        return container_instance_objects, failures

        
    def update_container_instance_resources(self, container_instance, task_resources, removing=False):
        resource_multiplier = 1
        if removing:
            resource_multiplier = -1
        for resource in container_instance.remainingResources:
            if resource.get("name") == "CPU":
                resource["integerValue"] -= task_resources.get('CPU') * resource_multiplier
            elif resource.get("name") == "MEMORY":
                resource["integerValue"] -= task_resources.get('MEMORY') * resource_multiplier
            elif resource.get("name") == "PORTS":
                for port in task_resources.get("PORTS"):
                    if removing:
                        resource["stringSetValue"].remove(str(port))
                    else:
                        resource["stringSetValue"].append(str(port))

    def deregister_container_instance(self, cluster_str, container_instance_str):
        pass


ecs_backends = {}
for region, ec2_backend in ec2_backends.items():
    ecs_backends[region] = EC2ContainerServiceBackend()
