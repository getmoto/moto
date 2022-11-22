import re
from copy import copy
from datetime import datetime
from typing import Any
import pytz

from moto import settings
from moto.core import BaseBackend, BackendDict, BaseModel, CloudFormationModel
from moto.core.exceptions import JsonRESTError
from moto.core.utils import unix_time, pascal_to_camelcase, remap_nested_keys

from ..ec2.utils import random_private_ip
from moto.ec2 import ec2_backends
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService
from .exceptions import (
    EcsClientException,
    ServiceNotFoundException,
    TaskDefinitionNotFoundException,
    TaskSetNotFoundException,
    ClusterNotFoundException,
    InvalidParameterException,
    RevisionNotFoundException,
    UnknownAccountSettingException,
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
            if key.startswith("_"):
                del response_object[key]
            elif "_" in key:
                response_object[self.camelCase(key)] = value
                del response_object[key]
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class AccountSetting(BaseObject):
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Cluster(BaseObject, CloudFormationModel):
    def __init__(self, cluster_name, account_id, region_name, cluster_settings=None):
        self.active_services_count = 0
        self.arn = f"arn:aws:ecs:{region_name}:{account_id}:cluster/{cluster_name}"
        self.name = cluster_name
        self.pending_tasks_count = 0
        self.registered_container_instances_count = 0
        self.running_tasks_count = 0
        self.status = "ACTIVE"
        self.region_name = region_name
        self.settings = cluster_settings

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

    @staticmethod
    def cloudformation_name_type():
        return "ClusterName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-cluster.html
        return "AWS::ECS::Cluster"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        ecs_backend = ecs_backends[account_id][region_name]
        return ecs_backend.create_cluster(
            # ClusterName is optional in CloudFormation, thus create a random
            # name if necessary
            cluster_name=resource_name
        )

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        if original_resource.name != new_resource_name:
            ecs_backend = ecs_backends[account_id][region_name]
            ecs_backend.delete_cluster(original_resource.arn)
            return ecs_backend.create_cluster(
                # ClusterName is optional in CloudFormation, thus create a
                # random name if necessary
                cluster_name=new_resource_name
            )
        else:
            # no-op when nothing changed between old and new resources
            return original_resource

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Arn"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()


class TaskDefinition(BaseObject, CloudFormationModel):
    def __init__(
        self,
        family,
        revision,
        container_definitions,
        account_id,
        region_name,
        network_mode=None,
        volumes=None,
        tags=None,
        placement_constraints=None,
        requires_compatibilities=None,
        cpu=None,
        memory=None,
        task_role_arn=None,
        execution_role_arn=None,
    ):
        self.family = family
        self.revision = revision
        self.arn = f"arn:aws:ecs:{region_name}:{account_id}:task-definition/{family}:{revision}"

        default_container_definition = {
            "cpu": 0,
            "portMappings": [],
            "essential": True,
            "environment": [],
            "mountPoints": [],
            "volumesFrom": [],
        }
        self.container_definitions = []
        for container_definition in container_definitions:
            full_definition = default_container_definition.copy()
            full_definition.update(container_definition)
            self.container_definitions.append(full_definition)

        self.tags = tags if tags is not None else []

        if volumes is None:
            self.volumes = []
        else:
            self.volumes = volumes

        if not requires_compatibilities or requires_compatibilities == ["EC2"]:
            self.compatibilities = ["EC2"]
        else:
            self.compatibilities = ["EC2", "FARGATE"]

        if network_mode is None and "FARGATE" not in self.compatibilities:
            self.network_mode = "bridge"
        elif "FARGATE" in self.compatibilities:
            self.network_mode = "awsvpc"
        else:
            self.network_mode = network_mode

        if task_role_arn is not None:
            self.task_role_arn = task_role_arn
        if execution_role_arn is not None:
            self.execution_role_arn = execution_role_arn

        self.placement_constraints = (
            placement_constraints if placement_constraints is not None else []
        )

        self.requires_compatibilities = requires_compatibilities

        self.cpu = cpu
        self.memory = memory
        self.status = "ACTIVE"

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["taskDefinitionArn"] = response_object["arn"]
        del response_object["arn"]
        del response_object["tags"]

        if not response_object["requiresCompatibilities"]:
            del response_object["requiresCompatibilities"]
        if not response_object["cpu"]:
            del response_object["cpu"]
        if not response_object["memory"]:
            del response_object["memory"]

        return response_object

    @property
    def physical_resource_id(self):
        return self.arn

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html
        return "AWS::ECS::TaskDefinition"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        family = properties.get(
            "Family", f"task-definition-{int(mock_random.random() * 10**6)}"
        )
        container_definitions = remap_nested_keys(
            properties.get("ContainerDefinitions", []), pascal_to_camelcase
        )
        volumes = remap_nested_keys(properties.get("Volumes", []), pascal_to_camelcase)

        ecs_backend = ecs_backends[account_id][region_name]
        return ecs_backend.register_task_definition(
            family=family, container_definitions=container_definitions, volumes=volumes
        )

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        properties = cloudformation_json["Properties"]
        family = properties.get(
            "Family", f"task-definition-{int(mock_random.random() * 10**6)}"
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
            ecs_backend = ecs_backends[account_id][region_name]
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
        backend,
        launch_type="",
        overrides=None,
        started_by="",
        tags=None,
        networking_configuration=None,
    ):
        self.id = str(mock_random.uuid4())
        self.cluster_name = cluster.name
        self.cluster_arn = cluster.arn
        self.container_instance_arn = container_instance_arn
        self.last_status = "RUNNING"
        self.desired_status = "RUNNING"
        self.task_definition_arn = task_definition.arn
        self.overrides = overrides or {}
        self.containers = []
        self.started_by = started_by
        self.tags = tags or []
        self.launch_type = launch_type
        self.stopped_reason = ""
        self.resource_requirements = resource_requirements
        self.region_name = cluster.region_name
        self._account_id = backend.account_id
        self._backend = backend
        self.attachments = []

        if task_definition.network_mode == "awsvpc":
            if not networking_configuration:

                raise InvalidParameterException(
                    "Network Configuration must be provided when networkMode 'awsvpc' is specified."
                )

            self.network_configuration = networking_configuration
            net_conf = networking_configuration["awsvpcConfiguration"]
            ec2_backend = ec2_backends[self._account_id][self.region_name]

            eni = ec2_backend.create_network_interface(
                subnet=net_conf["subnets"][0],
                private_ip_address=random_private_ip(),
                group_ids=net_conf["securityGroups"],
                description="moto ECS",
            )
            eni.status = "in-use"
            eni.device_index = 0

            self.attachments.append(
                {
                    "id": str(mock_random.uuid4()),
                    "type": "ElasticNetworkInterface",
                    "status": "ATTACHED",
                    "details": [
                        {"name": "subnetId", "value": net_conf["subnets"][0]},
                        {"name": "networkInterfaceId", "value": eni.id},
                        {"name": "macAddress", "value": eni.mac_address},
                        {"name": "privateDnsName", "value": eni.private_dns_name},
                        {"name": "privateIPv4Address", "value": eni.private_ip_address},
                    ],
                }
            )

    @property
    def task_arn(self):
        if self._backend.enable_long_arn_for_name(name="taskLongArnFormat"):
            return f"arn:aws:ecs:{self.region_name}:{self._account_id}:task/{self.cluster_name}/{self.id}"
        return f"arn:aws:ecs:{self.region_name}:{self._account_id}:task/{self.id}"

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["taskArn"] = self.task_arn
        return response_object


class CapacityProvider(BaseObject):
    def __init__(self, account_id, region_name, name, asg_details, tags):
        self._id = str(mock_random.uuid4())
        self.capacity_provider_arn = f"arn:aws:ecs:{region_name}:{account_id}:capacity_provider/{name}/{self._id}"
        self.name = name
        self.status = "ACTIVE"
        self.auto_scaling_group_provider = asg_details
        self.tags = tags


class CapacityProviderFailure(BaseObject):
    def __init__(self, reason, name, account_id, region_name):
        self.reason = reason
        self.arn = f"arn:aws:ecs:{region_name}:{account_id}:capacity_provider/{name}"

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["reason"] = self.reason
        response_object["arn"] = self.arn
        return response_object


class Service(BaseObject, CloudFormationModel):
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
        launch_type=None,
        backend=None,
        service_registries=None,
    ):
        self.cluster_name = cluster.name
        self.cluster_arn = cluster.arn
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
        self.launch_type = launch_type
        self.service_registries = service_registries or []
        if self.deployment_controller["type"] == "ECS":
            self.deployments = [
                {
                    "createdAt": datetime.now(pytz.utc),
                    "desiredCount": self.desired_count,
                    "id": f"ecs-svc/{mock_random.randint(0, 32**12)}",
                    "launchType": self.launch_type,
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
        self.region_name = cluster.region_name
        self._account_id = backend.account_id
        self._backend = backend

    @property
    def arn(self):
        if self._backend.enable_long_arn_for_name(name="serviceLongArnFormat"):
            return f"arn:aws:ecs:{self.region_name}:{self._account_id}:service/{self.cluster_name}/{self.name}"
        return f"arn:aws:ecs:{self.region_name}:{self._account_id}:service/{self.name}"

    @property
    def physical_resource_id(self):
        return self.arn

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        del response_object["name"], response_object["tags"]
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

    @staticmethod
    def cloudformation_name_type():
        return "ServiceName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-service.html
        return "AWS::ECS::Service"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
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
        desired_count = properties.get("DesiredCount", None)
        # TODO: LoadBalancers
        # TODO: Role

        ecs_backend = ecs_backends[account_id][region_name]
        return ecs_backend.create_service(
            cluster, resource_name, desired_count, task_definition_str=task_definition
        )

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
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
        desired_count = properties.get("DesiredCount", None)

        ecs_backend = ecs_backends[account_id][region_name]
        service_name = original_resource.name
        if (
            original_resource.cluster_arn
            != Cluster(cluster_name, account_id, region_name).arn
        ):
            # TODO: LoadBalancers
            # TODO: Role
            ecs_backend.delete_service(cluster_name, service_name)
            return ecs_backend.create_service(
                cluster_name,
                new_resource_name,
                desired_count,
                task_definition_str=task_definition,
            )
        else:
            return ecs_backend.update_service(
                cluster_name, service_name, task_definition, desired_count
            )

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Name"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Name":
            return self.name
        raise UnformattedGetAttTemplateException()


class ContainerInstance(BaseObject):
    def __init__(self, ec2_instance_id, account_id, region_name, cluster_name, backend):
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
        ec2_backend = ec2_backends[account_id][region_name]
        ec2_instance = ec2_backend.get_instance(ec2_instance_id)
        self.attributes = {
            "ecs.ami-id": ec2_instance.image_id,
            "ecs.availability-zone": ec2_instance.placement,
            "ecs.instance-type": ec2_instance.instance_type,
            "ecs.os-type": ec2_instance.platform
            if ec2_instance.platform == "windows"
            else "linux",  # options are windows and linux, linux is default
        }
        self.registered_at = datetime.now(pytz.utc)
        self.region_name = region_name
        self.id = str(mock_random.uuid4())
        self.cluster_name = cluster_name
        self._account_id = backend.account_id
        self._backend = backend

    @property
    def container_instance_arn(self):
        if self._backend.enable_long_arn_for_name(
            name="containerInstanceLongArnFormat"
        ):
            return f"arn:aws:ecs:{self.region_name}:{self._account_id}:container-instance/{self.cluster_name}/{self.id}"
        return f"arn:aws:ecs:{self.region_name}:{self._account_id}:container-instance/{self.id}"

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["containerInstanceArn"] = self.container_instance_arn
        response_object["attributes"] = [
            self._format_attribute(name, value)
            for name, value in response_object["attributes"].items()
        ]
        if isinstance(response_object["registeredAt"], datetime):
            response_object["registeredAt"] = unix_time(
                response_object["registeredAt"].replace(tzinfo=None)
            )
        return response_object

    def _format_attribute(self, name, value):
        formatted_attr = {"name": name}
        if value is not None:
            formatted_attr["value"] = value
        return formatted_attr


class ClusterFailure(BaseObject):
    def __init__(self, reason, cluster_name, account_id, region_name):
        self.reason = reason
        self.arn = f"arn:aws:ecs:{region_name}:{account_id}:cluster/{cluster_name}"

    @property
    def response_object(self):
        response_object = self.gen_response_object()
        response_object["reason"] = self.reason
        response_object["arn"] = self.arn
        return response_object


class ContainerInstanceFailure(BaseObject):
    def __init__(self, reason, container_instance_id, account_id, region_name):
        self.reason = reason
        self.arn = f"arn:aws:ecs:{region_name}:{account_id}:container-instance/{container_instance_id}"

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
        account_id,
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
        self.id = f"ecs-svc/{mock_random.randint(0, 32**12)}"
        self.service_arn = ""
        self.cluster_arn = ""

        cluster_name = self.cluster.split("/")[-1]
        service_name = self.service.split("/")[-1]
        self.task_set_arn = f"arn:aws:ecs:{region_name}:{account_id}:task-set/{cluster_name}/{service_name}/{self.id}"

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
    """
    ECS resources use the new ARN format by default.
    Use the following environment variable to revert back to the old/short ARN format:
    `MOTO_ECS_NEW_ARN=false`

    AWS reference: https://aws.amazon.com/blogs/compute/migrating-your-amazon-ecs-deployment-to-the-new-arn-and-resource-id-format-2/
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.account_settings = dict()
        self.capacity_providers = dict()
        self.clusters = {}
        self.task_definitions = {}
        self.tasks = {}
        self.services = {}
        self.container_instances = {}
        self.task_sets = {}
        self.tagger = TaggingService(
            tag_name="tags", key_name="key", value_name="value"
        )

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "ecs"
        )

    def _get_cluster(self, name):
        # short name or full ARN of the cluster
        cluster_name = name.split("/")[-1]

        cluster = self.clusters.get(cluster_name)
        if not cluster:
            raise ClusterNotFoundException

        return cluster

    def create_capacity_provider(self, name, asg_details, tags):
        capacity_provider = CapacityProvider(
            self.account_id, self.region_name, name, asg_details, tags
        )
        self.capacity_providers[name] = capacity_provider
        if tags:
            self.tagger.tag_resource(capacity_provider.capacity_provider_arn, tags)
        return capacity_provider

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
            raise Exception(f"{task_definition_name} is not a task_definition")

    def create_cluster(
        self, cluster_name: str, tags: Any = None, cluster_settings: Any = None
    ) -> Cluster:
        """
        The following parameters are not yet implemented: configuration, capacityProviders, defaultCapacityProviderStrategy
        """
        cluster = Cluster(
            cluster_name, self.account_id, self.region_name, cluster_settings
        )
        self.clusters[cluster_name] = cluster
        if tags:
            self.tagger.tag_resource(cluster.arn, tags)
        return cluster

    def _get_provider(self, name_or_arn):
        for provider in self.capacity_providers.values():
            if (
                provider.name == name_or_arn
                or provider.capacity_provider_arn == name_or_arn
            ):
                return provider

    def describe_capacity_providers(self, names):
        providers = []
        failures = []
        for name in names:
            provider = self._get_provider(name)
            if provider:
                providers.append(provider)
            else:
                failures.append(
                    CapacityProviderFailure(
                        "MISSING", name, self.account_id, self.region_name
                    )
                )
        return providers, failures

    def delete_capacity_provider(self, name_or_arn):
        provider = self._get_provider(name_or_arn)
        self.capacity_providers.pop(provider.name)
        return provider

    def list_clusters(self):
        """
        maxSize and pagination not implemented
        """
        return [cluster.arn for cluster in self.clusters.values()]

    def describe_clusters(self, list_clusters_name=None, include=None):
        """
        Only include=TAGS is currently supported.
        """
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
                        ClusterFailure(
                            "MISSING", cluster_name, self.account_id, self.region_name
                        )
                    )

        if "TAGS" in (include or []):
            for cluster in list_clusters:
                cluster_arn = cluster["clusterArn"]
                if self.tagger.has_tags(cluster_arn):
                    cluster_tags = self.tagger.list_tags_for_resource(cluster_arn)
                    cluster.update(cluster_tags)

        return list_clusters, failures

    def delete_cluster(self, cluster_str: str) -> Cluster:
        cluster = self._get_cluster(cluster_str)

        return self.clusters.pop(cluster.name)

    def register_task_definition(
        self,
        family,
        container_definitions,
        volumes=None,
        network_mode=None,
        tags=None,
        placement_constraints=None,
        requires_compatibilities=None,
        cpu=None,
        memory=None,
        task_role_arn=None,
        execution_role_arn=None,
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
            self.account_id,
            self.region_name,
            volumes=volumes,
            network_mode=network_mode,
            tags=tags,
            placement_constraints=placement_constraints,
            requires_compatibilities=requires_compatibilities,
            cpu=cpu,
            memory=memory,
            task_role_arn=task_role_arn,
            execution_role_arn=execution_role_arn,
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
        try:
            family, revision = task_definition_name.split(":")
        except ValueError:
            raise RevisionNotFoundException
        try:
            revision = int(revision)
        except ValueError:
            raise InvalidParameterException(
                "Invalid revision number. Number: " + revision
            )
        if (
            family in self.task_definitions
            and revision in self.task_definitions[family]
        ):
            task_definition = self.task_definitions[family].pop(revision)
            task_definition.status = "INACTIVE"
            return task_definition
        else:
            raise TaskDefinitionNotFoundException

    def run_task(
        self,
        cluster_str,
        task_definition_str,
        count,
        overrides,
        started_by,
        tags,
        launch_type,
        networking_configuration=None,
    ):
        cluster = self._get_cluster(cluster_str)

        task_definition = self.describe_task_definition(task_definition_str)
        if cluster.name not in self.tasks:
            self.tasks[cluster.name] = {}
        tasks = []
        container_instances = list(
            self.container_instances.get(cluster.name, {}).keys()
        )
        if not container_instances:
            raise Exception(f"No instances found in cluster {cluster.name}")
        active_container_instances = [
            x
            for x in container_instances
            if self.container_instances[cluster.name][x].status == "ACTIVE"
        ]
        resource_requirements = self._calculate_task_resource_requirements(
            task_definition
        )
        # TODO: return event about unable to place task if not able to place enough tasks to meet count
        placed_count = 0
        for container_instance in active_container_instances:
            container_instance = self.container_instances[cluster.name][
                container_instance
            ]
            container_instance_arn = container_instance.container_instance_arn
            try_to_place = True
            while try_to_place:
                can_be_placed = self._can_be_placed(
                    container_instance, resource_requirements
                )
                if can_be_placed:
                    task = Task(
                        cluster,
                        task_definition,
                        container_instance_arn,
                        resource_requirements,
                        backend=self,
                        overrides=overrides or {},
                        started_by=started_by or "",
                        tags=tags or [],
                        launch_type=launch_type or "",
                        networking_configuration=networking_configuration,
                    )
                    self.update_container_instance_resources(
                        container_instance, resource_requirements
                    )
                    tasks.append(task)
                    self.tasks[cluster.name][task.task_arn] = task
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
            return False
        if task_resource_requirements.get("MEMORY") > remaining_memory:
            return False
        ports_needed = task_resource_requirements.get("PORTS")
        for port in ports_needed:
            if str(port) in reserved_ports:
                return False
        return True

    def start_task(
        self,
        cluster_str,
        task_definition_str,
        container_instances,
        overrides,
        started_by,
    ):
        cluster = self._get_cluster(cluster_str)

        task_definition = self.describe_task_definition(task_definition_str)
        if cluster.name not in self.tasks:
            self.tasks[cluster.name] = {}
        tasks = []
        if not container_instances:
            raise EcsClientException("Container Instances cannot be empty.")

        container_instance_ids = [x.split("/")[-1] for x in container_instances]
        resource_requirements = self._calculate_task_resource_requirements(
            task_definition
        )
        for container_instance_id in container_instance_ids:
            container_instance = self.container_instances[cluster.name][
                container_instance_id
            ]
            task = Task(
                cluster,
                task_definition,
                container_instance.container_instance_arn,
                resource_requirements,
                backend=self,
                overrides=overrides or {},
                started_by=started_by or "",
            )
            tasks.append(task)
            self.update_container_instance_resources(
                container_instance, resource_requirements
            )
            self.tasks[cluster.name][task.task_arn] = task
        return tasks

    def describe_tasks(self, cluster_str, tasks):
        self._get_cluster(cluster_str)

        if not tasks:
            raise InvalidParameterException("Tasks cannot be empty.")
        response = []
        for cluster_tasks in self.tasks.values():
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
            for task in tasks.values():
                filtered_tasks.append(task)
        if cluster_str:
            cluster = self._get_cluster(cluster_str)

            filtered_tasks = list(
                filter(lambda t: cluster.name in t.cluster_arn, filtered_tasks)
            )

        if container_instance:
            filtered_tasks = list(
                filter(
                    lambda t: container_instance in t.container_instance_arn,
                    filtered_tasks,
                )
            )

        if family:
            task_definition_arns = self.list_task_definitions(family)
            filtered_tasks = list(
                filter(
                    lambda t: t.task_definition_arn in task_definition_arns,
                    filtered_tasks,
                )
            )

        if started_by:
            filtered_tasks = list(
                filter(lambda t: started_by == t.started_by, filtered_tasks)
            )

        if service_name:
            # TODO: We can't filter on `service_name` until the backend actually
            # launches tasks as part of the service creation process.
            pass

        if desiredStatus:
            filtered_tasks = list(
                filter(lambda t: t.desired_status == desiredStatus, filtered_tasks)
            )

        return [t.task_arn for t in filtered_tasks]

    def stop_task(self, cluster_str, task_str, reason):
        cluster = self._get_cluster(cluster_str)

        task_id = task_str.split("/")[-1]
        tasks = self.tasks.get(cluster.name, None)
        if not tasks:
            raise Exception(f"Cluster {cluster.name} has no registered tasks")
        for task in tasks.keys():
            if task.endswith(task_id):
                container_instance_arn = tasks[task].container_instance_arn
                container_instance = self.container_instances[cluster.name][
                    container_instance_arn.split("/")[-1]
                ]
                self.update_container_instance_resources(
                    container_instance, tasks[task].resource_requirements, removing=True
                )
                tasks[task].last_status = "STOPPED"
                tasks[task].desired_status = "STOPPED"
                tasks[task].stopped_reason = reason
                return tasks[task]
        raise Exception(f"Could not find task {task_str} on cluster {cluster.name}")

    def _get_service(self, cluster_str, service_str):
        cluster = self._get_cluster(cluster_str)
        for service in self.services.values():
            if service.cluster_name == cluster.name and (
                service.name == service_str or service.arn == service_str
            ):
                return service
        raise ServiceNotFoundException

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
        launch_type=None,
        service_registries=None,
    ):
        cluster = self._get_cluster(cluster_str)

        if task_definition_str is not None:
            task_definition = self.describe_task_definition(task_definition_str)
        else:
            task_definition = None
        desired_count = desired_count if desired_count is not None else 0

        launch_type = launch_type if launch_type is not None else "EC2"
        if launch_type not in ["EC2", "FARGATE"]:
            raise EcsClientException("launch type should be one of [EC2,FARGATE]")

        service = Service(
            cluster,
            service_name,
            desired_count,
            task_definition,
            load_balancers,
            scheduling_strategy,
            tags,
            deployment_controller,
            launch_type,
            backend=self,
            service_registries=service_registries,
        )
        cluster_service_pair = f"{cluster.name}:{service_name}"
        self.services[cluster_service_pair] = service

        return service

    def list_services(self, cluster_str, scheduling_strategy=None, launch_type=None):
        cluster_name = cluster_str.split("/")[-1]
        service_arns = []
        for key, service in self.services.items():
            if cluster_name + ":" not in key:
                continue

            if (
                scheduling_strategy is not None
                and service.scheduling_strategy != scheduling_strategy
            ):
                continue

            if launch_type is not None and service.launch_type != launch_type:
                continue

            service_arns.append(service.arn)

        return sorted(service_arns)

    def describe_services(self, cluster_str, service_names_or_arns):
        cluster = self._get_cluster(cluster_str)
        service_names = [name.split("/")[-1] for name in service_names_or_arns]

        result = []
        failures = []
        for name in service_names:
            cluster_service_pair = f"{cluster.name}:{name}"
            if cluster_service_pair in self.services:
                result.append(self.services[cluster_service_pair])
            else:
                missing_arn = (
                    f"arn:aws:ecs:{self.region_name}:{self.account_id}:service/{name}"
                )
                failures.append({"arn": missing_arn, "reason": "MISSING"})

        return result, failures

    def update_service(
        self, cluster_str, service_str, task_definition_str, desired_count
    ):
        cluster = self._get_cluster(cluster_str)

        service_name = service_str.split("/")[-1]
        cluster_service_pair = f"{cluster.name}:{service_name}"
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
            raise ServiceNotFoundException

    def delete_service(self, cluster_name, service_name, force):
        cluster = self._get_cluster(cluster_name)
        service = self._get_service(cluster_name, service_name)

        cluster_service_pair = f"{cluster.name}:{service.name}"

        service = self.services[cluster_service_pair]
        if service.desired_count > 0 and not force:
            raise InvalidParameterException(
                "The service cannot be stopped while it is scaled above 0."
            )
        else:
            return self.services.pop(cluster_service_pair)

    def register_container_instance(self, cluster_str, ec2_instance_id):
        cluster_name = cluster_str.split("/")[-1]
        if cluster_name not in self.clusters:
            raise Exception(f"{cluster_name} is not a cluster")
        container_instance = ContainerInstance(
            ec2_instance_id,
            self.account_id,
            self.region_name,
            cluster_name,
            backend=self,
        )
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
        cluster = self._get_cluster(cluster_str)

        if not list_container_instance_ids:
            raise EcsClientException("Container Instances cannot be empty.")
        failures = []
        container_instance_objects = []
        for container_instance_id in list_container_instance_ids:
            container_instance_id = container_instance_id.split("/")[-1]
            container_instance = self.container_instances[cluster.name].get(
                container_instance_id, None
            )
            if container_instance is not None:
                container_instance_objects.append(container_instance)
            else:
                failures.append(
                    ContainerInstanceFailure(
                        "MISSING",
                        container_instance_id,
                        self.account_id,
                        self.region_name,
                    )
                )

        return container_instance_objects, failures

    def update_container_instances_state(
        self, cluster_str, list_container_instance_ids, status
    ):
        cluster = self._get_cluster(cluster_str)

        status = status.upper()
        if status not in ["ACTIVE", "DRAINING"]:
            raise InvalidParameterException(
                "Container instance status should be one of [ACTIVE, DRAINING]"
            )
        failures = []
        container_instance_objects = []
        list_container_instance_ids = [
            x.split("/")[-1] for x in list_container_instance_ids
        ]
        for container_instance_id in list_container_instance_ids:
            container_instance = self.container_instances[cluster.name].get(
                container_instance_id, None
            )
            if container_instance is not None:
                container_instance.status = status
                container_instance_objects.append(container_instance)
            else:
                failures.append(
                    ContainerInstanceFailure(
                        "MISSING",
                        container_instance_id,
                        self.account_id,
                        self.region_name,
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
        cluster = self._get_cluster(cluster_str)

        container_instance_id = container_instance_str.split("/")[-1]
        container_instance = self.container_instances[cluster.name].get(
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
        del self.container_instances[cluster.name][container_instance_id]
        self._respond_to_cluster_state_update(cluster_str)
        return container_instance

    def _respond_to_cluster_state_update(self, cluster_str):
        self._get_cluster(cluster_str)

        pass

    def put_attributes(self, cluster_name, attributes=None):
        cluster = self._get_cluster(cluster_name)

        if attributes is None:
            raise InvalidParameterException("attributes can not be empty")

        for attr in attributes:
            self._put_attribute(
                cluster.name,
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
                    "TargetNotFoundException", f"Could not find {target_id}"
                )
        else:
            # targetId is container uuid, targetType must be container-instance
            try:
                if target_type != "container-instance":
                    raise JsonRESTError(
                        "TargetNotFoundException", f"Could not find {target_id}"
                    )

                self.container_instances[cluster_name][target_id].attributes[
                    name
                ] = value
            except KeyError:
                raise JsonRESTError(
                    "TargetNotFoundException", f"Could not find {target_id}"
                )

    def list_attributes(
        self,
        target_type,
        cluster_name=None,
        attr_name=None,
        attr_value=None,
    ):
        """
        Pagination is not yet implemented
        """
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
        cluster = self._get_cluster(cluster_name)

        if attributes is None:
            raise JsonRESTError(
                "InvalidParameterException", "attributes value is required"
            )

        for attr in attributes:
            self._delete_attribute(
                cluster.name,
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
                    "TargetNotFoundException", f"Could not find {target_id}"
                )
        else:
            # targetId is container uuid, targetType must be container-instance
            try:
                if target_type != "container-instance":
                    raise JsonRESTError(
                        "TargetNotFoundException", f"Could not find {target_id}"
                    )

                instance = self.container_instances[cluster_name][target_id]
                if name in instance.attributes and instance.attributes[name] == value:
                    del instance.attributes[name]
            except KeyError:
                raise JsonRESTError(
                    "TargetNotFoundException", f"Could not find {target_id}"
                )

    def list_task_definition_families(self, family_prefix=None):
        """
        The Status and pagination parameters are not yet implemented
        """
        for task_fam in self.task_definitions:
            if family_prefix is not None and not task_fam.startswith(family_prefix):
                continue

            yield task_fam

    @staticmethod
    def _parse_resource_arn(resource_arn):
        match = re.match(
            "^arn:aws:ecs:(?P<region>[^:]+):(?P<account_id>[^:]+):(?P<service>[^:]+)/(?P<cluster_id>[^:]+)/(?P<id>.*)$",
            resource_arn,
        )
        if not match:
            # maybe a short-format ARN
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
            raise TaskDefinitionNotFoundException()
        elif parsed_arn["service"] == "service":
            for service in self.services.values():
                if service.arn == resource_arn:
                    return service.tags
            raise ServiceNotFoundException
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
            raise ServiceNotFoundException
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
            raise ServiceNotFoundException
        raise NotImplementedError()

    def create_task_set(
        self,
        service,
        cluster_str,
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
        launch_type = launch_type if launch_type is not None else "EC2"
        if launch_type not in ["EC2", "FARGATE"]:
            raise EcsClientException("launch type should be one of [EC2,FARGATE]")

        task_set = TaskSet(
            service,
            cluster_str,
            task_definition,
            self.account_id,
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

        service_name = service.split("/")[-1]

        cluster_obj = self._get_cluster(cluster_str)
        service_obj = self.services.get(f"{cluster_obj.name}:{service_name}")
        if not service_obj:
            raise ServiceNotFoundException

        task_set.task_definition = self.describe_task_definition(task_definition).arn
        task_set.service_arn = service_obj.arn
        task_set.cluster_arn = cluster_obj.arn

        service_obj.task_sets.append(task_set)
        # TODO: validate load balancers

        return task_set

    def describe_task_sets(self, cluster_str, service, task_sets=None, include=None):
        task_sets = task_sets or []
        include = include or []

        cluster_obj = self._get_cluster(cluster_str)

        service_name = service.split("/")[-1]
        service_key = f"{cluster_obj.name}:{service_name}"

        service_obj = self.services.get(service_key)
        if not service_obj:
            raise ServiceNotFoundException

        task_set_results = []
        if task_sets:
            for task_set in service_obj.task_sets:
                if task_set.task_set_arn in task_sets:
                    task_set_results.append(task_set)
        else:
            task_set_results = service_obj.task_sets

        return task_set_results

    def delete_task_set(self, cluster, service, task_set):
        """
        The Force-parameter is not yet implemented
        """
        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]

        service_key = f"{cluster_name}:{service_name}"
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
        """Updates task sets be PRIMARY or ACTIVE for given cluster:service task sets"""
        cluster_name = cluster.split("/")[-1]
        service_name = service.split("/")[-1]
        task_set_obj = self.describe_task_sets(
            cluster_name, service_name, task_sets=[primary_task_set]
        )[0]

        services, _ = self.describe_services(cluster, [service])
        service_obj = services[0]
        service_obj.load_balancers = task_set_obj.load_balancers
        service_obj.task_definition = task_set_obj.task_definition

        for task_set in service_obj.task_sets:
            if task_set.task_set_arn == primary_task_set:
                task_set.status = "PRIMARY"
            else:
                task_set.status = "ACTIVE"
        return task_set_obj

    def list_account_settings(self, name=None, value=None):
        expected_names = [
            "serviceLongArnFormat",
            "taskLongArnFormat",
            "containerInstanceLongArnFormat",
            "containerLongArnFormat",
            "awsvpcTrunking",
            "containerInsights",
            "dualStackIPv6",
        ]
        if name and name not in expected_names:
            raise UnknownAccountSettingException()
        all_settings = self.account_settings.values()
        return [
            s
            for s in all_settings
            if (not name or s.name == name) and (not value or s.value == value)
        ]

    def put_account_setting(self, name, value):
        account_setting = AccountSetting(name, value)
        self.account_settings[name] = account_setting
        return account_setting

    def delete_account_setting(self, name):
        self.account_settings.pop(name, None)

    def enable_long_arn_for_name(self, name):
        account = self.account_settings.get(name, None)
        if account and account.value == "disabled":
            return False
        return settings.ecs_new_arn_format()


ecs_backends = BackendDict(EC2ContainerServiceBackend, "ecs")
