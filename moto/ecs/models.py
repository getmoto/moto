from __future__ import unicode_literals
import re
import uuid
from datetime import datetime
from random import random, randint

import pytz
from boto3 import Session

from moto.core.exceptions import JsonRESTError
from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time
from moto.ec2 import ec2_backends
from copy import copy

from .exceptions import (
    ServiceNotFoundException,
    TaskDefinitionNotFoundException,
    TaskSetNotFoundException,
    ClusterNotFoundException,
)


class BaseObject(BaseModel):
    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split("_")):
            if i > 0:
                words.append(word.title())
            else:
                words.append(word)
        return "".join(words)

    def gen_response_object(self):
        response_object = copy(self.__dict__)
        for key, value in self.__dict__.items():
            if "_" in key:
                response_object[self.camelCase(key)] = value
                del response_object[key]
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class Cluster(BaseObject):
    def __init__(self, cluster_name, region_name):
        self.active_services_count = 0
        self.arn = "arn:aws:ecs:{0}:012345678910:cluster/{1}".format(
            region_name, cluster_name
        )
        self.name = cluster_name
        self.pending_tasks_count = 0
        self.registered_container_instances_count = 0
        self.running_tasks_count = 0
        self.status = "ACTIVE"
        self.region_name = region_name

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["clusterArn"] = self.arn
        response_object["clusterName"] = self.name
        del response_object["arn"], response_object["name"]
        return response_object

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # if properties is not provided, cloudformation will use the default values for all properties
        if "Properties" in cloudformation_json:
            properties = cloudformation_json["Properties"]
        else:
            properties = {}

        ecs_backend = ecs_backends[region_name]
        return ecs_backend.create_cluster(
            # ClusterName is optional in CloudFormation, thus create a random
            # name if necessary
            cluster_name=properties.get(
                "ClusterName", "ecscluster{0}".format(int(random() * 10 ** 6))
            )
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        if original_resource.name != properties["ClusterName"]:
            ecs_backend = ecs_backends[region_name]
            ecs_backend.delete_cluster(original_resource.arn)
            return ecs_backend.create_cluster(
                # ClusterName is optional in CloudFormation, thus create a
                # random name if necessary
                cluster_name=properties.get(
                    "ClusterName", "ecscluster{0}".format(int(random() * 10 ** 6))
                )
            )
        else:
            # no-op when nothing changed between old and new resources
            return original_resource

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()


class TaskDefinition(BaseObject):
    def __init__(
        self,
        family,
        revision,
        container_definitions,
        region_name,
        network_mode=None,
        volumes=None,
        tags=None,
        placement_constraints=None,
    ):
        self.family = family
        self.revision = revision
        self.arn = "arn:aws:ecs:{0}:012345678910:task-definition/{1}:{2}".format(
            region_name, family, revision
        )
        self.container_definitions = container_definitions
        self.tags = tags if tags is not None else []
        if volumes is None:
            self.volumes = []
        else:
            self.volumes = volumes
        if network_mode is None:
            self.network_mode = "bridge"
        else:
            self.network_mode = network_mode
        self.placement_constraints = (
            placement_constraints if placement_constraints is not None else []
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["taskDefinitionArn"] = response_object["arn"]
        del response_object["arn"]
        del response_object["tags"]
        return response_object

    @property
    def physical_resource_id(self):
        return self.arn

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        family = properties.get(
            "Family", "task-definition-{0}".format(int(random() * 10 ** 6))
        )
        container_definitions = properties["ContainerDefinitions"]
        volumes = properties.get("Volumes")

        ecs_backend = ecs_backends[region_name]
        return ecs_backend.register_task_definition(
            family=family, container_definitions=container_definitions, volumes=volumes
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        family = properties.get(
            "Family", "task-definition-{0}".format(int(random() * 10 ** 6))
        )
        container_definitions = properties["ContainerDefinitions"]
        volumes = properties.get("Volumes")
        if (
            original_resource.family != family
            or original_resource.container_definitions != container_definitions
            or original_resource.volumes != volumes
        ):
            # currently TaskRoleArn isn't stored at TaskDefinition
            # instances
            ecs_backend = ecs_backends[region_name]
            ecs_backend.deregister_task_definition(original_resource.arn)
            return ecs_backend.register_task_definition(
                family=family,
                container_definitions=container_definitions,
                volumes=volumes,
            )
        else:
            # no-op when nothing changed between old and new resources
            return original_resource


class Task(BaseObject):
    def __init__(
        self,
        cluster,
        task_definition,
        container_instance_arn,
        resource_requirements,
        overrides={},
        started_by="",
    ):
        self.cluster_arn = cluster.arn
        self.task_arn = "arn:aws:ecs:{0}:012345678910:task/{1}".format(
            cluster.region_name, str(uuid.uuid4())
        )
        self.container_instance_arn = container_instance_arn
        self.last_status = "RUNNING"
        self.desired_status = "RUNNING"
        self.task_definition_arn = task_definition.arn
        self.overrides = overrides
        self.containers = []
        self.started_by = started_by
        self.stopped_reason = ""
        self.resource_requirements = resource_requirements

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        return response_object


class Service(BaseObject):
    def __init__(
        self,
        cluster,
        service_name,
        desired_count,
        task_definition=None,
        load_balancers=None,
        scheduling_strategy=None,
        tags=None,
        deployment_controller=None,
    ):
        self.cluster_arn = cluster.arn
        self.arn = "arn:aws:ecs:{0}:012345678910:service/{1}".format(
            cluster.region_name, service_name
        )
        self.name = service_name
        self.status = "ACTIVE"
        self.running_count = 0
        if task_definition:
            self.task_definition = task_definition.arn
        else:
            self.task_definition = None
        self.desired_count = desired_count
        self.task_sets = []
        self.deployment_controller = deployment_controller or {"type": "ECS"}
        self.events = []
        if self.deployment_controller["type"] == "ECS":
            self.deployments = [
                {
                    "createdAt": datetime.now(pytz.utc),
                    "desiredCount": self.desired_count,
                    "id": "ecs-svc/{}".format(randint(0, 32 ** 12)),
                    "pendingCount": self.desired_count,
                    "runningCount": 0,
                    "status": "PRIMARY",
                    "taskDefinition": self.task_definition,
                    "updatedAt": datetime.now(pytz.utc),
                }
            ]
        else:
            self.deployments = []
        self.load_balancers = load_balancers if load_balancers is not None else []
        self.scheduling_strategy = (
            scheduling_strategy if scheduling_strategy is not None else "REPLICA"
        )
        self.tags = tags if tags is not None else []
        self.pending_count = 0

    @property
    def physical_resource_id(self):
        return self.arn

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        del response_object["name"], response_object["arn"], response_object["tags"]
        response_object["serviceName"] = self.name
        response_object["serviceArn"] = self.arn
        response_object["schedulingStrategy"] = self.scheduling_strategy
        if response_object["deploymentController"]["type"] == "ECS":
            del response_object["deploymentController"]
            del response_object["taskSets"]
        else:
            response_object["taskSets"] = [
                t.response_object for t in response_object["taskSets"]
            ]

        for deployment in response_object["deployments"]:
            if isinstance(deployment["createdAt"], datetime):
                deployment["createdAt"] = unix_time(
                    deployment["createdAt"].replace(tzinfo=None)
                )
            if isinstance(deployment["updatedAt"], datetime):
                deployment["updatedAt"] = unix_time(
                    deployment["updatedAt"].replace(tzinfo=None)
                )

        return response_object

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        if isinstance(properties["Cluster"], Cluster):
            cluster = properties["Cluster"].name
        else:
            cluster = properties["Cluster"]
        if isinstance(properties["TaskDefinition"], TaskDefinition):
            task_definition = properties["TaskDefinition"].family
        else:
            task_definition = properties["TaskDefinition"]
        service_name = "{0}Service{1}".format(cluster, int(random() * 10 ** 6))
        desired_count = properties["DesiredCount"]
        # TODO: LoadBalancers
        # TODO: Role

        ecs_backend = ecs_backends[region_name]
        return ecs_backend.create_service(
            cluster, service_name, desired_count, task_definition_str=task_definition
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        if isinstance(properties["Cluster"], Cluster):
            cluster_name = properties["Cluster"].name
        else:
            cluster_name = properties["Cluster"]
        if isinstance(properties["TaskDefinition"], TaskDefinition):
            task_definition = properties["TaskDefinition"].family
        else:
            task_definition = properties["TaskDefinition"]
        desired_count = properties["DesiredCount"]

        ecs_backend = ecs_backends[region_name]
        service_name = original_resource.name
        if original_resource.cluster_arn != Cluster(cluster_name, region_name).arn:
            # TODO: LoadBalancers
            # TODO: Role
            ecs_backend.delete_service(cluster_name, service_name)
            new_service_name = "{0}Service{1}".format(
                cluster_name, int(random() * 10 ** 6)
            )
            return ecs_backend.create_service(
                cluster_name,
                new_service_name,
                desired_count,
                task_definition_str=task_definition,
            )
        else:
            return ecs_backend.update_service(
                cluster_name, service_name, task_definition, desired_count
            )

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Name":
            return self.name
        raise UnformattedGetAttTemplateException()


class ContainerInstance(BaseObject):
    def __init__(self, ec2_instance_id, region_name):
        self.ec2_instance_id = ec2_instance_id
        self.agent_connected = True
        self.status = "ACTIVE"
        self.registered_resources = [
            {
                "doubleValue": 0.0,
                "integerValue": 4096,
                "longValue": 0,
                "name": "CPU",
                "type": "INTEGER",
            },
            {
                "doubleValue": 0.0,
                "integerValue": 7482,
                "longValue": 0,
                "name": "MEMORY",
                "type": "INTEGER",
            },
            {
                "doubleValue": 0.0,
                "integerValue": 0,
                "longValue": 0,
                "name": "PORTS",
                "stringSetValue": ["22", "2376", "2375", "51678", "51679"],
                "type": "STRINGSET",
            },
            {
                "doubleValue": 0.0,
                "integerValue": 0,
                "longValue": 0,
                "name": "PORTS_UDP",
                "stringSetValue": [],
                "type": "STRINGSET",
            },
        ]
        self.container_instance_arn = "arn:aws:ecs:{0}:012345678910:container-instance/{1}".format(
            region_name, str(uuid.uuid4())
        )
        self.pending_tasks_count = 0
        self.remaining_resources = [
            {
                "doubleValue": 0.0,
                "integerValue": 4096,
                "longValue": 0,
                "name": "CPU",
                "type": "INTEGER",
            },
            {
                "doubleValue": 0.0,
                "integerValue": 7482,
                "longValue": 0,
                "name": "MEMORY",
                "type": "INTEGER",
            },
            {
                "doubleValue": 0.0,
                "integerValue": 0,
                "longValue": 0,
                "name": "PORTS",
                "stringSetValue": ["22", "2376", "2375", "51678", "51679"],
                "type": "STRINGSET",
            },
            {
                "doubleValue": 0.0,
                "integerValue": 0,
                "longValue": 0,
                "name": "PORTS_UDP",
                "stringSetValue": [],
                "type": "STRINGSET",
            },
        ]
        self.running_tasks_count = 0
        self.version_info = {
            "agentVersion": "1.0.0",
            "agentHash": "4023248",
            "dockerVersion": "DockerVersion: 1.5.0",
        }
        ec2_backend = ec2_backends[region_name]
        ec2_instance = ec2_backend.get_instance(ec2_instance_id)
        self.attributes = {
            "ecs.ami-id": ec2_instance.image_id,
            "ecs.availability-zone": ec2_instance.placement,
            "ecs.instance-type": ec2_instance.instance_type,
            "ecs.os-type": ec2_instance.platform
            if ec2_instance.platform == "windows"
            else "linux",  # options are windows and linux, linux is default
        }

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["attributes"] = [
            self._format_attribute(name, value)
            for name, value in response_object["attributes"].items()
        ]
        return response_object

    def _format_attribute(self, name, value):
        formatted_attr = {"name": name}
        if value is not None:
            formatted_attr["value"] = value
        return formatted_attr


class ClusterFailure(BaseObject):
    def __init__(self, reason, cluster_name, region_name):
        self.reason = reason
        self.arn = "arn:aws:ecs:{0}:012345678910:cluster/{1}".format(
            region_name, cluster_name
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["reason"] = self.reason
        response_object["arn"] = self.arn
        return response_object


class ContainerInstanceFailure(BaseObject):
    def __init__(self, reason, container_instance_id, region_name):
        self.reason = reason
        self.arn = "arn:aws:ecs:{0}:012345678910:container-instance/{1}".format(
            region_name, container_instance_id
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["reason"] = self.reason
        response_object["arn"] = self.arn
        return response_object


class TaskSet(BaseObject):
    def __init__(
        self,
        service,
        cluster,
        task_definition,
        region_name,
        external_id=None,
        network_configuration=None,
        load_balancers=None,
        service_registries=None,
        launch_type=None,
        capacity_provider_strategy=None,
        platform_version=None,
        scale=None,
        client_token=None,
        tags=None,
    ):
        self.service = service
        self.cluster = cluster
        self.status = "ACTIVE"
        self.task_definition = task_definition or ""
        self.region_name = region_name
        self.external_id = external_id or ""
        self.network_configuration = network_configuration or {}
        self.load_balancers = load_balancers or []
        self.service_registries = service_registries or []
        self.launch_type = launch_type
        self.capacity_provider_strategy = capacity_provider_strategy or []
        self.platform_version = platform_version or ""
        self.scale = scale or {"value": 100.0, "unit": "PERCENT"}
        self.client_token = client_token or ""
        self.tags = tags or []
        self.stabilityStatus = "STEADY_STATE"
        self.createdAt = datetime.now(pytz.utc)
        self.updatedAt = datetime.now(pytz.utc)
        self.stabilityStatusAt = datetime.now(pytz.utc)
        self.id = "ecs-svc/{}".format(randint(0, 32 ** 12))
        self.service_arn = ""
        self.cluster_arn = ""

        cluster_name = self.cluster.split("/")[-1]
        service_name = self.service.split("/")[-1]
        self.task_set_arn = "arn:aws:ecs:{0}:012345678910:task-set/{1}/{2}/{3}".format(
            region_name, cluster_name, service_name, self.id
        )

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        if isinstance(response_object["createdAt"], datetime):
            response_object["createdAt"] = unix_time(
                self.createdAt.replace(tzinfo=None)
            )
        if isinstance(response_object["updatedAt"], datetime):
            response_object["updatedAt"] = unix_time(
                self.updatedAt.replace(tzinfo=None)
            )
        if isinstance(response_object["stabilityStatusAt"], datetime):
            response_object["stabilityStatusAt"] = unix_time(
                self.stabilityStatusAt.replace(tzinfo=None)
            )
        del response_object["service"]
        del response_object["cluster"]
        return response_object


class EC2ContainerServiceBackend(BaseBackend):
    def __init__(self, region_name):
        super(EC2ContainerServiceBackend, self).__init__()
        self.clusters = {}
        self.task_definitions = {}
        self.tasks = {}
        self.services = {}
        self.container_instances = {}
        self.task_sets = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def describe_task_definition(self, task_definition_str):
        task_definition_name = task_definition_str.split("/")[-1]
        if ":" in task_definition_name:
            family, revision = task_definition_name.split(":")
            revision = int(revision)
        else:
            family = task_definition_name
            revision = self._get_last_task_definition_revision_id(family)

        if (
            family in self.task_definitions
            and revision in self.task_definitions[family]
        ):
            return self.task_definitions[family][revision]
        else:
            raise Exception("{0} is not a task_definition".format(task_definition_name))

    def create_cluster(self, cluster_name):
        cluster = Cluster(cluster_name, self.region_name)
        self.clusters[cluster_name] = cluster
        return cluster

    def list_clusters(self):
        """
        maxSize and pagination not implemented
        """
        return [cluster.arn for cluster in self.clusters.values()]

    def describe_clusters(self, list_clusters_name=None):
        list_clusters = []
        failures = []
        if list_clusters_name is None:
            if "default" in self.clusters:
                list_clusters.append(self.clusters["default"].response_object)
        else:
            for cluster in list_clusters_name:
                cluster_name = cluster.split("/")[-1]
                if cluster_name in self.clusters:
                    list_clusters.append(self.clusters[cluster_name].response_object)
                else:
                    failures.append(
                        ClusterFailure("MISSING", cluster_name, self.region_name)
                    )
        return list_clusters, failures

    def delete_cluster(self, cluster_str):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name in self.clusters:
            return self.clusters.pop(cluster_name)
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))

    def register_task_definition(
        self,
        family,
        container_definitions,
        volumes=None,
        network_mode=None,
        tags=None,
        placement_constraints=None,
    ):
        if family in self.task_definitions:
            last_id = self._get_last_task_definition_revision_id(family)
            revision = (last_id or 0) + 1
        else:
            self.task_definitions[family] = {}
            revision = 1
        task_definition = TaskDefinition(
            family,
            revision,
            container_definitions,
            self.region_name,
            volumes=volumes,
            network_mode=network_mode,
            tags=tags,
            placement_constraints=placement_constraints,
        )
        self.task_definitions[family][revision] = task_definition

        return task_definition

    def list_task_definitions(self, family_prefix):
        task_arns = []
        for task_definition_list in self.task_definitions.values():
            task_arns.extend(
                [
                    task_definition.arn
                    for task_definition in task_definition_list.values()
                    if family_prefix is None or task_definition.family == family_prefix
                ]
            )
        return task_arns

    def deregister_task_definition(self, task_definition_str):
        task_definition_name = task_definition_str.split("/")[-1]
        family, revision = task_definition_name.split(":")
        revision = int(revision)
        if (
            family in self.task_definitions
            and revision in self.task_definitions[family]
        ):
            return self.task_definitions[family].pop(revision)
        else:
            raise Exception("{0} is not a task_definition".format(task_definition_name))

    def run_task(self, cluster_str, task_definition_str, count, overrides, started_by):
        if cluster_str:
            cluster_name = cluster_str.split("/")[-1]
        else:
            cluster_name = "default"
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        task_definition = self.describe_task_definition(task_definition_str)
        if cluster_name not in self.tasks:
            self.tasks[cluster_name] = {}
        tasks = []
        container_instances = list(
            self.container_instances.get(cluster_name, {}).keys()
        )
        if not container_instances:
            raise Exception("No instances found in cluster {}".format(cluster_name))
        active_container_instances = [
            x
            for x in container_instances
            if self.container_instances[cluster_name][x].status == "ACTIVE"
        ]
        resource_requirements = self._calculate_task_resource_requirements(
            task_definition
        )
        # TODO: return event about unable to place task if not able to place enough tasks to meet count
        placed_count = 0
        for container_instance in active_container_instances:
            container_instance = self.container_instances[cluster_name][
                container_instance
            ]
            container_instance_arn = container_instance.container_instance_arn
            try_to_place = True
            while try_to_place:
                can_be_placed, message = self._can_be_placed(
                    container_instance, resource_requirements
                )
                if can_be_placed:
                    task = Task(
                        cluster,
                        task_definition,
                        container_instance_arn,
                        resource_requirements,
                        overrides or {},
                        started_by or "",
                    )
                    self.update_container_instance_resources(
                        container_instance, resource_requirements
                    )
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
            # cloudformation uses capitalized properties, while boto uses all lower case

            # CPU is optional
            resource_requirements["CPU"] += container_definition.get(
                "cpu", container_definition.get("Cpu", 0)
            )

            # either memory or memory reservation must be provided
            if (
                "Memory" in container_definition
                or "MemoryReservation" in container_definition
            ):
                resource_requirements["MEMORY"] += container_definition.get(
                    "Memory", container_definition.get("MemoryReservation")
                )
            else:
                resource_requirements["MEMORY"] += container_definition.get(
                    "memory", container_definition.get("memoryReservation")
                )

            port_mapping_key = (
                "PortMappings"
                if "PortMappings" in container_definition
                else "portMappings"
            )
            for port_mapping in container_definition.get(port_mapping_key, []):
                if "hostPort" in port_mapping:
                    resource_requirements["PORTS"].append(port_mapping.get("hostPort"))
                elif "HostPort" in port_mapping:
                    resource_requirements["PORTS"].append(port_mapping.get("HostPort"))

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
        for resource in container_instance.remaining_resources:
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

    def start_task(
        self,
        cluster_str,
        task_definition_str,
        container_instances,
        overrides,
        started_by,
    ):
        cluster_name = cluster_str.split("/")[-1]
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

        container_instance_ids = [x.split("/")[-1] for x in container_instances]
        resource_requirements = self._calculate_task_resource_requirements(
            task_definition
        )
        for container_instance_id in container_instance_ids:
            container_instance = self.container_instances[cluster_name][
                container_instance_id
            ]
            task = Task(
                cluster,
                task_definition,
                container_instance.container_instance_arn,
                resource_requirements,
                overrides or {},
                started_by or "",
            )
            tasks.append(task)
            self.update_container_instance_resources(
                container_instance, resource_requirements
            )
            self.tasks[cluster_name][task.task_arn] = task
        return tasks

    def describe_tasks(self, cluster_str, tasks):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        if not tasks:
            raise Exception("tasks cannot be empty")
        response = []
        for cluster, cluster_tasks in self.tasks.items():
            for task_arn, task in cluster_tasks.items():
                task_id = task_arn.split("/")[-1]
                if (
                    task_arn in tasks
                    or task.task_arn in tasks
                    or any(task_id in task for task in tasks)
                ):
                    response.append(task)
        return response

    def list_tasks(
        self,
        cluster_str,
        container_instance,
        family,
        started_by,
        service_name,
        desiredStatus,
    ):
        filtered_tasks = []
        for cluster, tasks in self.tasks.items():
            for arn, task in tasks.items():
                filtered_tasks.append(task)
        if cluster_str:
            cluster_name = cluster_str.split("/")[-1]
            if cluster_name not in self.clusters:
                raise Exception("{0} is not a cluster".format(cluster_name))
            filtered_tasks = list(
                filter(lambda t: cluster_name in t.cluster_arn, filtered_tasks)
            )

        if container_instance:
            filtered_tasks = list(
                filter(
                    lambda t: container_instance in t.container_instance_arn,
                    filtered_tasks,
                )
            )

        if started_by:
            filtered_tasks = list(
                filter(lambda t: started_by == t.started_by, filtered_tasks)
            )
        return [t.task_arn for t in filtered_tasks]

    def stop_task(self, cluster_str, task_str, reason):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))

        if not task_str:
            raise Exception("A task ID or ARN is required")
        task_id = task_str.split("/")[-1]
        tasks = self.tasks.get(cluster_name, None)
        if not tasks:
            raise Exception("Cluster {} has no registered tasks".format(cluster_name))
        for task in tasks.keys():
            if task.endswith(task_id):
                container_instance_arn = tasks[task].container_instance_arn
                container_instance = self.container_instances[cluster_name][
                    container_instance_arn.split("/")[-1]
                ]
                self.update_container_instance_resources(
                    container_instance, tasks[task].resource_requirements, removing=True
                )
                tasks[task].last_status = "STOPPED"
                tasks[task].desired_status = "STOPPED"
                tasks[task].stopped_reason = reason
                return tasks[task]
        raise Exception(
            "Could not find task {} on cluster {}".format(task_str, cluster_name)
        )

    def create_service(
        self,
        cluster_str,
        service_name,
        desired_count,
        task_definition_str=None,
        load_balancers=None,
        scheduling_strategy=None,
        tags=None,
        deployment_controller=None,
    ):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name in self.clusters:
            cluster = self.clusters[cluster_name]
        else:
            raise Exception("{0} is not a cluster".format(cluster_name))
        if task_definition_str is not None:
            task_definition = self.describe_task_definition(task_definition_str)
        else:
            task_definition = None
        desired_count = desired_count if desired_count is not None else 0

        service = Service(
            cluster,
            service_name,
            desired_count,
            task_definition,
            load_balancers,
            scheduling_strategy,
            tags,
            deployment_controller,
        )
        cluster_service_pair = "{0}:{1}".format(cluster_name, service_name)
        self.services[cluster_service_pair] = service

        return service

    def list_services(self, cluster_str, scheduling_strategy=None):
        cluster_name = cluster_str.split("/")[-1]
        service_arns = []
        for key, value in self.services.items():
            if cluster_name + ":" in key:
                service = self.services[key]
                if (
                    scheduling_strategy is None
                    or service.scheduling_strategy == scheduling_strategy
                ):
                    service_arns.append(service.arn)

        return sorted(service_arns)

    def describe_services(self, cluster_str, service_names_or_arns):
        cluster_name = cluster_str.split("/")[-1]
        result = []
        for existing_service_name, existing_service_obj in sorted(
            self.services.items()
        ):
            for requested_name_or_arn in service_names_or_arns:
                cluster_service_pair = "{0}:{1}".format(
                    cluster_name, requested_name_or_arn
                )
                if (
                    cluster_service_pair == existing_service_name
                    or existing_service_obj.arn == requested_name_or_arn
                ):
                    result.append(existing_service_obj)

        return result

    def update_service(
        self, cluster_str, service_str, task_definition_str, desired_count
    ):
        cluster_name = cluster_str.split("/")[-1]
        service_name = service_str.split("/")[-1]
        cluster_service_pair = "{0}:{1}".format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            if task_definition_str is not None:
                self.describe_task_definition(task_definition_str)
                self.services[
                    cluster_service_pair
                ].task_definition = task_definition_str
            if desired_count is not None:
                self.services[cluster_service_pair].desired_count = desired_count
            return self.services[cluster_service_pair]
        else:
            raise ServiceNotFoundException(service_name)

    def delete_service(self, cluster_name, service_name):
        cluster_service_pair = "{0}:{1}".format(cluster_name, service_name)
        if cluster_service_pair in self.services:
            service = self.services[cluster_service_pair]
            if service.desired_count > 0:
                raise Exception("Service must have desiredCount=0")
            else:
                return self.services.pop(cluster_service_pair)
        else:
            raise Exception(
                "cluster {0} or service {1} does not exist".format(
                    cluster_name, service_name
                )
            )

    def register_container_instance(self, cluster_str, ec2_instance_id):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        container_instance = ContainerInstance(ec2_instance_id, self.region_name)
        if not self.container_instances.get(cluster_name):
            self.container_instances[cluster_name] = {}
        container_instance_id = container_instance.container_instance_arn.split("/")[-1]
        self.container_instances[cluster_name][
            container_instance_id
        ] = container_instance
        self.clusters[cluster_name].registered_container_instances_count += 1
        return container_instance

    def list_container_instances(self, cluster_str):
        cluster_name = cluster_str.split("/")[-1]
        container_instances_values = self.container_instances.get(
            cluster_name, {}
        ).values()
        container_instances = [
            ci.container_instance_arn for ci in container_instances_values
        ]
        return sorted(container_instances)

    def describe_container_instances(self, cluster_str, list_container_instance_ids):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        if not list_container_instance_ids:
            raise JsonRESTError(
                "InvalidParameterException", "Container instance cannot be empty"
            )
        failures = []
        container_instance_objects = []
        for container_instance_id in list_container_instance_ids:
            container_instance_id = container_instance_id.split("/")[-1]
            container_instance = self.container_instances[cluster_name].get(
                container_instance_id, None
            )
            if container_instance is not None:
                container_instance_objects.append(container_instance)
            else:
                failures.append(
                    ContainerInstanceFailure(
                        "MISSING", container_instance_id, self.region_name
                    )
                )

        return container_instance_objects, failures

    def update_container_instances_state(
        self, cluster_str, list_container_instance_ids, status
    ):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        status = status.upper()
        if status not in ["ACTIVE", "DRAINING"]:
            raise Exception(
                "An error occurred (InvalidParameterException) when calling the UpdateContainerInstancesState operation: \
                            Container instances status should be one of [ACTIVE,DRAINING]"
            )
        failures = []
        container_instance_objects = []
        list_container_instance_ids = [
            x.split("/")[-1] for x in list_container_instance_ids
        ]
        for container_instance_id in list_container_instance_ids:
            container_instance = self.container_instances[cluster_name].get(
                container_instance_id, None
            )
            if container_instance is not None:
                container_instance.status = status
                container_instance_objects.append(container_instance)
            else:
                failures.append(
                    ContainerInstanceFailure(
                        "MISSING", container_instance_id, self.region_name
                    )
                )

        return container_instance_objects, failures

    def update_container_instance_resources(
        self, container_instance, task_resources, removing=False
    ):
        resource_multiplier = 1
        if removing:
            resource_multiplier = -1
        for resource in container_instance.remaining_resources:
            if resource.get("name") == "CPU":
                resource["integerValue"] -= (
                    task_resources.get("CPU") * resource_multiplier
                )
            elif resource.get("name") == "MEMORY":
                resource["integerValue"] -= (
                    task_resources.get("MEMORY") * resource_multiplier
                )
            elif resource.get("name") == "PORTS":
                for port in task_resources.get("PORTS"):
                    if removing:
                        resource["stringSetValue"].remove(str(port))
                    else:
                        resource["stringSetValue"].append(str(port))
        container_instance.running_tasks_count += resource_multiplier * 1

    def deregister_container_instance(self, cluster_str, container_instance_str, force):
        failures = []
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        container_instance_id = container_instance_str.split("/")[-1]
        container_instance = self.container_instances[cluster_name].get(
            container_instance_id
        )
        if container_instance is None:
            raise Exception("{0} is not a container id in the cluster")
        if not force and container_instance.running_tasks_count > 0:
            raise Exception("Found running tasks on the instance.")
        # Currently assume that people might want to do something based around deregistered instances
        # with tasks left running on them - but nothing if no tasks were running already
        elif force and container_instance.running_tasks_count > 0:
            if not self.container_instances.get("orphaned"):
                self.container_instances["orphaned"] = {}
            self.container_instances["orphaned"][
                container_instance_id
            ] = container_instance
        del self.container_instances[cluster_name][container_instance_id]
        self._respond_to_cluster_state_update(cluster_str)
        return container_instance, failures

    def _respond_to_cluster_state_update(self, cluster_str):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception("{0} is not a cluster".format(cluster_name))
        pass

    def put_attributes(self, cluster_name, attributes=None):
        if cluster_name is None or cluster_name not in self.clusters:
            raise ClusterNotFoundException

        if attributes is None:
            raise JsonRESTError(
                "InvalidParameterException", "attributes value is required"
            )

        for attr in attributes:
            self._put_attribute(
                cluster_name,
                attr["name"],
                attr.get("value"),
                attr.get("targetId"),
                attr.get("targetType"),
            )

    def _put_attribute(
        self, cluster_name, name, value=None, target_id=None, target_type=None
    ):
        if target_id is None and target_type is None:
            for instance in self.container_instances[cluster_name].values():
                instance.attributes[name] = value
        elif target_type is None:
            # targetId is full container instance arn
            try:
                arn = target_id.rsplit("/", 1)[-1]
                self.container_instances[cluster_name][arn].attributes[name] = value
            except KeyError:
                raise JsonRESTError(
                    "TargetNotFoundException", "Could not find {0}".format(target_id)
                )
        else:
            # targetId is container uuid, targetType must be container-instance
            try:
                if target_type != "container-instance":
                    raise JsonRESTError(
                        "TargetNotFoundException",
                        "Could not find {0}".format(target_id),
                    )

                self.container_instances[cluster_name][target_id].attributes[
                    name
                ] = value
            except KeyError:
                raise JsonRESTError(
                    "TargetNotFoundException", "Could not find {0}".format(target_id)
                )

    def list_attributes(
        self,
        target_type,
        cluster_name=None,
        attr_name=None,
        attr_value=None,
        max_results=None,
        next_token=None,
    ):
        if target_type != "container-instance":
            raise JsonRESTError(
                "InvalidParameterException", "targetType must be container-instance"
            )

        filters = [lambda x: True]

        # item will be {0 cluster_name, 1 arn, 2 name, 3 value}
        if cluster_name is not None:
            filters.append(lambda item: item[0] == cluster_name)
        if attr_name:
            filters.append(lambda item: item[2] == attr_name)
        if attr_name:
            filters.append(lambda item: item[3] == attr_value)

        all_attrs = []
        for cluster_name, cobj in self.container_instances.items():
            for container_instance in cobj.values():
                for key, value in container_instance.attributes.items():
                    all_attrs.append(
                        (
                            cluster_name,
                            container_instance.container_instance_arn,
                            key,
                            value,
                        )
                    )

        return filter(lambda x: all(f(x) for f in filters), all_attrs)

    def delete_attributes(self, cluster_name, attributes=None):
        if cluster_name is None or cluster_name not in self.clusters:
            raise ClusterNotFoundException

        if attributes is None:
            raise JsonRESTError(
                "InvalidParameterException", "attributes value is required"
            )

        for attr in attributes:
            self._delete_attribute(
                cluster_name,
                attr["name"],
                attr.get("value"),
                attr.get("targetId"),
                attr.get("targetType"),
            )

    def _delete_attribute(
        self, cluster_name, name, value=None, target_id=None, target_type=None
    ):
        if target_id is None and target_type is None:
            for instance in self.container_instances[cluster_name].values():
                if name in instance.attributes and instance.attributes[name] == value:
                    del instance.attributes[name]
        elif target_type is None:
            # targetId is full container instance arn
            try:
                arn = target_id.rsplit("/", 1)[-1]
                instance = self.container_instances[cluster_name][arn]
                if name in instance.attributes and instance.attributes[name] == value:
                    del instance.attributes[name]
            except KeyError:
                raise JsonRESTError(
                    "TargetNotFoundException", "Could not find {0}".format(target_id)
                )
        else:
            # targetId is container uuid, targetType must be container-instance
            try:
                if target_type != "container-instance":
                    raise JsonRESTError(
                        "TargetNotFoundException",
                        "Could not find {0}".format(target_id),
                    )

                instance = self.container_instances[cluster_name][target_id]
                if name in instance.attributes and instance.attributes[name] == value:
                    del instance.attributes[name]
            except KeyError:
                raise JsonRESTError(
                    "TargetNotFoundException", "Could not find {0}".format(target_id)
                )

    def list_task_definition_families(
        self, family_prefix=None, status=None, max_results=None, next_token=None
    ):
        for task_fam in self.task_definitions:
            if family_prefix is not None and not task_fam.startswith(family_prefix):
                continue

            yield task_fam

    @staticmethod
    def _parse_resource_arn(resource_arn):
        match = re.match(
            "^arn:aws:ecs:(?P<region>[^:]+):(?P<account_id>[^:]+):(?P<service>[^:]+)/(?P<id>.*)$",
            resource_arn,
        )
        if not match:
            raise JsonRESTError(
                "InvalidParameterException", "The ARN provided is invalid."
            )
        return match.groupdict()

    def list_tags_for_resource(self, resource_arn):
        """Currently implemented only for task definitions and services"""
        parsed_arn = self._parse_resource_arn(resource_arn)
        if parsed_arn["service"] == "task-definition":
            for task_definition in self.task_definitions.values():
                for revision in task_definition.values():
                    if revision.arn == resource_arn:
                        return revision.tags
            else:
                raise TaskDefinitionNotFoundException()
        elif parsed_arn["service"] == "service":
            for service in self.services.values():
                if service.arn == resource_arn:
                    return service.tags
            else:
                raise ServiceNotFoundException(service_name=parsed_arn["id"])
        raise NotImplementedError()

    def _get_last_task_definition_revision_id(self, family):
        definitions = self.task_definitions.get(family, {})
        if definitions:
            return max(definitions.keys())

    def tag_resource(self, resource_arn, tags):
        """Currently implemented only for services"""
        parsed_arn = self._parse_resource_arn(resource_arn)
        if parsed_arn["service"] == "service":
            for service in self.services.values():
                if service.arn == resource_arn:
                    service.tags = self._merge_tags(service.tags, tags)
                return {}
            else:
                raise ServiceNotFoundException(service_name=parsed_arn["id"])
        raise NotImplementedError()

    def _merge_tags(self, existing_tags, new_tags):
        merged_tags = new_tags
        new_keys = self._get_keys(new_tags)
        for existing_tag in existing_tags:
            if existing_tag["key"] not in new_keys:
                merged_tags.append(existing_tag)
        return merged_tags

    @staticmethod
    def _get_keys(tags):
        return [tag["key"] for tag in tags]

    def untag_resource(self, resource_arn, tag_keys):
        """Currently implemented only for services"""
        parsed_arn = self._parse_resource_arn(resource_arn)
        if parsed_arn["service"] == "service":
            for service in self.services.values():
                if service.arn == resource_arn:
                    service.tags = [
                        tag for tag in service.tags if tag["key"] not in tag_keys
                    ]
                return {}
            else:
                raise ServiceNotFoundException(service_name=parsed_arn["id"])
        raise NotImplementedError()

    def create_task_set(
        self,
        service,
        cluster,
        task_definition,
        external_id=None,
        network_configuration=None,
        load_balancers=None,
        service_registries=None,
        launch_type=None,
        capacity_provider_strategy=None,
        platform_version=None,
        scale=None,
        client_token=None,
        tags=None,
    ):
        task_set = TaskSet(
            service,
            cluster,
            task_definition,
            self.region_name,
            external_id=external_id,
            network_configuration=network_configuration,
            load_balancers=load_balancers,
            service_registries=service_registries,
            launch_type=launch_type,
            capacity_provider_strategy=capacity_provider_strategy,
            platform_version=platform_version,
            scale=scale,
            client_token=client_token,
            tags=tags,
        )

        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]

        service_obj = self.services.get("{0}:{1}".format(cluster_name, service_name))
        if not service_obj:
            raise ServiceNotFoundException(service_name=service_name)

        cluster_obj = self.clusters.get(cluster_name)
        if not cluster_obj:
            raise ClusterNotFoundException

        task_set.task_definition = self.describe_task_definition(task_definition).arn
        task_set.service_arn = service_obj.arn
        task_set.cluster_arn = cluster_obj.arn

        service_obj.task_sets.append(task_set)
        # TODO: validate load balancers

        return task_set

    def describe_task_sets(self, cluster, service, task_sets=None, include=None):
        task_sets = task_sets or []
        include = include or []

        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]
        service_key = "{0}:{1}".format(cluster_name, service_name)

        service_obj = self.services.get(service_key)
        if not service_obj:
            raise ServiceNotFoundException(service_name=service_name)

        cluster_obj = self.clusters.get(cluster_name)
        if not cluster_obj:
            raise ClusterNotFoundException

        task_set_results = []
        if task_sets:
            for task_set in service_obj.task_sets:
                if task_set.task_set_arn in task_sets:
                    task_set_results.append(task_set)
        else:
            task_set_results = service_obj.task_sets

        return task_set_results

    def delete_task_set(self, cluster, service, task_set, force=False):
        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]

        service_key = "{0}:{1}".format(cluster_name, service_name)
        task_set_element = None
        for i, ts in enumerate(self.services[service_key].task_sets):
            if task_set == ts.task_set_arn:
                task_set_element = i

        if task_set_element is not None:
            deleted_task_set = self.services[service_key].task_sets.pop(
                task_set_element
            )
        else:
            raise TaskSetNotFoundException

        # TODO: add logic for `force` to raise an exception if `PRIMARY` task has not been scaled to 0.

        return deleted_task_set

    def update_task_set(self, cluster, service, task_set, scale):
        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]
        task_set_obj = self.describe_task_sets(
            cluster_name, service_name, task_sets=[task_set]
        )[0]
        task_set_obj.scale = scale
        return task_set_obj

    def update_service_primary_task_set(self, cluster, service, primary_task_set):
        """ Updates task sets be PRIMARY or ACTIVE for given cluster:service task sets """
        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]
        task_set_obj = self.describe_task_sets(
            cluster_name, service_name, task_sets=[primary_task_set]
        )[0]

        service_obj = self.describe_services(cluster, [service])[0]
        service_obj.load_balancers = task_set_obj.load_balancers
        service_obj.task_definition = task_set_obj.task_definition

        for task_set in service_obj.task_sets:
            if task_set.task_set_arn == primary_task_set:
                task_set.status = "PRIMARY"
            else:
                task_set.status = "ACTIVE"
        return task_set_obj


ecs_backends = {}
for region in Session().get_available_regions("ecs"):
    ecs_backends[region] = EC2ContainerServiceBackend(region)
for region in Session().get_available_regions("ecs", partition_name="aws-us-gov"):
    ecs_backends[region] = EC2ContainerServiceBackend(region)
for region in Session().get_available_regions("ecs", partition_name="aws-cn"):
    ecs_backends[region] = EC2ContainerServiceBackend(region)
