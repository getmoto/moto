from __future__ import unicode_literals

from boto3 import Session
from datetime import datetime
from moto.core import BaseBackend, ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from .exceptions import (
    ResourceNotFoundException,
    ResourceInUseException,
    InvalidRequestException,
    InvalidParameterException,
)
from .utils import set_partition, validate_role_arn, method_name
from ..utilities.utils import random_string

# String Templates
CLUSTER_ARN_TEMPLATE = (
    "arn:{partition}:eks:{region}:" + str(ACCOUNT_ID) + ":cluster/{name}"
)
NODEGROUP_ARN_TEMPLATE = (
    "arn:{partition}:eks:{region}:"
    + str(ACCOUNT_ID)
    + ":nodegroup/{cluster_name}/{nodegroup_name}/{uuid}"
)
ISSUER_TEMPLATE = "https://oidc.eks.{region}.amazonaws.com/id/" + random_string(10)
ENDPOINT_TEMPLATE = (
    "https://"
    + random_string()
    + "."
    + random_string(3)
    + ".{region}.eks.amazonaws.com/"
)

# Defaults used for creating a Cluster
DEFAULT_KUBERNETES_NETWORK_CONFIG = {"serviceIpv4Cidr": "172.20.0.0/16"}
DEFAULT_KUBERNETES_VERSION = "1.19"
DEFAULT_LOGGING = {
    "clusterLogging": [
        {
            "types": [
                "api",
                "audit",
                "authenticator",
                "controllerManager",
                "scheduler",
            ],
            "enabled": False,
        }
    ]
}
DEFAULT_PLATFORM_VERSION = "eks.4"
DEFAULT_STATUS = "ACTIVE"

# Defaults used for creating a Managed Nodegroup
DEFAULT_AMI_TYPE = "AL2_x86_64"
DEFAULT_CAPACITY_TYPE = "ON_DEMAND"
DEFAULT_DISK_SIZE = "20"
DEFAULT_INSTANCE_TYPES = ["t3.medium"]
DEFAULT_NODEGROUP_HEALTH = {"issues": []}
DEFAULT_RELEASE_VERSION = "1.19.8-20210414"
DEFAULT_REMOTE_ACCESS = {"ec2SshKey": "eksKeypair"}
DEFAULT_SCALING_CONFIG = {"minSize": 2, "maxSize": 2, "desiredSize": 2}

# Exception messages, also imported into testing
# example: "An error occurred (ResourceInUseException) when calling the CreateNodegroup
# operation: NodeGroup already exists with name ng1 and cluster name cluster"
BASE_MSG = "An error occurred ({exception_name}) when calling the {method} operation: "
CLUSTER_IN_USE_MSG = BASE_MSG + "Cluster has nodegroups attached"
CLUSTER_EXISTS_MSG = BASE_MSG + "Cluster already exists with name: {cluster_name}"
CLUSTER_NOT_FOUND_MSG = BASE_MSG + "No cluster found for name: {cluster_name}."
CLUSTER_NOT_READY_MSG = BASE_MSG + "Cluster '{cluster_name}' is not in ACTIVE status"
LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG = (
    BASE_MSG + "Disk size must be specified within the launch template."
)
LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG = (
    BASE_MSG + "Remote access configuration cannot be specified with a launch template."
)
NODEGROUP_EXISTS_MSG = (
    BASE_MSG
    + "NodeGroup already exists with name {nodegroup_name} and cluster name {cluster_name}"
)
NODEGROUP_NOT_FOUND_MSG = BASE_MSG + "No node group found for name: {nodegroup_name}."


class Cluster:
    def __init__(
        self,
        name,
        roleArn,
        resourcesVpcConfig,
        regionName,
        awsPartition,
        version=None,
        kubernetesNetworkConfig=None,
        logging=None,
        clientRequestToken=None,
        tags=None,
        encryptionConfig=None,
    ):
        if encryptionConfig is None:
            encryptionConfig = dict()
        if tags is None:
            tags = dict()

        self.nodegroups = dict()
        self.nodegroup_count = 0

        self.arn = CLUSTER_ARN_TEMPLATE.format(
            partition=awsPartition, region=regionName, name=name
        )
        self.certificateAuthority = {"data": random_string(1400)}
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.identity = {"oidc": {"issuer": ISSUER_TEMPLATE.format(region=regionName)}}
        self.endpoint = ENDPOINT_TEMPLATE.format(region=regionName)

        self.kubernetes_network_config = (
            kubernetesNetworkConfig or DEFAULT_KUBERNETES_NETWORK_CONFIG
        )
        self.logging = logging or DEFAULT_LOGGING
        self.platformVersion = DEFAULT_PLATFORM_VERSION
        self.status = DEFAULT_STATUS
        self.version = version or DEFAULT_KUBERNETES_VERSION

        self.client_request_token = clientRequestToken
        self.encryption_config = encryptionConfig
        self.name = name
        self.resources_vpc_config = resourcesVpcConfig
        self.role_arn = roleArn
        self.tags = tags

    def __iter__(self):
        yield "name", self.name
        yield "arn", self.arn
        yield "createdAt", self.creation_date
        yield "version", self.version
        yield "endpoint", self.endpoint
        yield "roleArn", self.role_arn
        yield "resourcesVpcConfig", self.resources_vpc_config
        yield "kubernetesNetworkConfig", self.kubernetes_network_config
        yield "logging", self.logging
        yield "identity", self.identity
        yield "status", self.status
        yield "certificateAuthority", self.certificateAuthority
        yield "clientRequestToken", self.client_request_token
        yield "platformVersion", self.platformVersion
        yield "tags", self.tags
        yield "encryptionConfig", self.encryption_config

    def isActive(self):
        return self.status == "ACTIVE"


class ManagedNodegroup:
    def __init__(
        self,
        cluster_name,
        node_role,
        nodegroup_name,
        subnets,
        regionName,
        awsPartition,
        scaling_config=None,
        disk_size=None,
        instance_types=None,
        ami_type=None,
        remote_access=None,
        labels=None,
        taints=None,
        tags=None,
        client_request_token=None,
        launch_template=None,
        capacity_type=None,
        version=None,
        release_version=None,
    ):
        if tags is None:
            tags = dict()
        if labels is None:
            labels = dict()
        if taints is None:
            taints = dict()

        self.uuid = "-".join([random_string(_) for _ in [8, 4, 4, 4, 12]]).lower()
        self.arn = NODEGROUP_ARN_TEMPLATE.format(
            partition=awsPartition,
            region=regionName,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
            uuid=self.uuid,
        )
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.modified_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.health = DEFAULT_NODEGROUP_HEALTH
        self.resources = {
            "autoScalingGroups": [{"name": "eks-" + self.uuid}],
            "remoteAccessSecurityGroup": "sg-" + random_string(17).lower(),
        }

        self.ami_type = ami_type or DEFAULT_AMI_TYPE
        self.capacity_type = capacity_type or DEFAULT_CAPACITY_TYPE
        self.disk_size = disk_size or DEFAULT_DISK_SIZE
        self.instance_types = instance_types or DEFAULT_INSTANCE_TYPES
        self.release_version = release_version or DEFAULT_RELEASE_VERSION
        self.remote_access = remote_access or DEFAULT_REMOTE_ACCESS
        self.scaling_config = scaling_config or DEFAULT_SCALING_CONFIG
        self.status = DEFAULT_STATUS
        self.version = version or DEFAULT_KUBERNETES_VERSION

        self.client_request_token = client_request_token
        self.cluster_name = cluster_name
        self.labels = labels
        self.launch_template = launch_template
        self.node_role = node_role
        self.nodegroup_name = nodegroup_name
        self.partition = awsPartition
        self.region = regionName
        self.subnets = subnets
        self.tags = tags
        self.taints = taints

    def __iter__(self):
        yield "nodegroupName", self.nodegroup_name
        yield "nodegroupArn", self.arn
        yield "clusterName", self.cluster_name
        yield "version", self.version
        yield "releaseVersion", self.release_version
        yield "createdAt", self.creation_date
        yield "modifiedAt", self.modified_date
        yield "status", self.status
        yield "capacityType", self.capacity_type
        yield "scalingConfig", self.scaling_config
        yield "instanceTypes", self.instance_types
        yield "subnets", self.subnets
        yield "remoteAccess", self.remote_access
        yield "amiType", self.ami_type
        yield "nodeRole", self.node_role
        yield "labels", self.labels
        yield "taints", self.taints
        yield "resources", self.resources
        yield "diskSize", self.disk_size
        yield "health", self.health
        yield "launchTemplate", self.launch_template
        yield "tags", self.tags


class EKSBackend(BaseBackend):
    def __init__(self, region_name):
        super(EKSBackend, self).__init__()
        self.clusters = dict()
        self.cluster_count = 0
        self.region_name = region_name
        self.partition = set_partition(region_name)

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def list_clusters(self, max_results, next_token):
        cluster_names = sorted(self.clusters.keys())
        start = cluster_names.index(next_token) if next_token else 0
        end = min(start + max_results, self.cluster_count)
        new_next = "null" if end == self.cluster_count else cluster_names[end]

        return cluster_names[start:end], new_next

    def create_cluster(
        self,
        name,
        role_arn,
        resources_vpc_config,
        version=None,
        kubernetes_network_config=None,
        logging=None,
        client_request_token=None,
        tags=None,
        encryption_config=None,
    ):
        validate_role_arn(role_arn)

        cluster = Cluster(
            name=name,
            roleArn=role_arn,
            resourcesVpcConfig=resources_vpc_config,
            version=version,
            kubernetesNetworkConfig=kubernetes_network_config,
            logging=logging,
            clientRequestToken=client_request_token,
            tags=tags,
            encryptionConfig=encryption_config,
            regionName=self.region_name,
            awsPartition=self.partition,
        )
        self.clusters[name] = cluster
        self.cluster_count += 1
        return cluster

    def create_nodegroup(
        self,
        cluster_name,
        node_role,
        nodegroup_name,
        subnets,
        scaling_config=None,
        disk_size=None,
        instance_types=None,
        ami_type=None,
        remote_access=None,
        labels=None,
        taints=None,
        tags=None,
        client_request_token=None,
        launch_template=None,
        capacity_type=None,
        version=None,
        release_version=None,
    ):
        if cluster_name not in self.clusters.keys():
            exception = ResourceNotFoundException
            raise exception(
                CLUSTER_NOT_FOUND_MSG.format(
                    exception_name=exception.TYPE,
                    method=method_name(),
                    cluster_name=cluster_name,
                )
            )
        if nodegroup_name in self.clusters[cluster_name].nodegroups.keys():
            exception = ResourceInUseException
            raise exception(
                NODEGROUP_EXISTS_MSG.format(
                    exception_name=exception.TYPE,
                    method=method_name(),
                    cluster_name=cluster_name,
                    nodegroup_name=nodegroup_name,
                )
            )
        if not self.clusters[cluster_name].isActive():
            exception = InvalidRequestException
            raise exception(
                CLUSTER_NOT_READY_MSG.format(
                    exception_name=exception.TYPE,
                    method=method_name(),
                    cluster_name=cluster_name,
                )
            )

        if launch_template and disk_size:
            exception = InvalidParameterException
            raise exception(
                LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG.format(
                    exception_name=exception.TYPE, method=method_name(),
                )
            )
        if launch_template and remote_access:
            exception = InvalidParameterException
            raise exception(
                LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG.format(
                    exception_name=exception.TYPE, method=method_name(),
                )
            )

        validate_role_arn(node_role)

        nodegroup = ManagedNodegroup(
            cluster_name=cluster_name,
            node_role=node_role,
            nodegroup_name=nodegroup_name,
            subnets=subnets,
            scaling_config=scaling_config,
            disk_size=disk_size,
            instance_types=instance_types,
            ami_type=ami_type,
            remote_access=remote_access,
            labels=labels,
            taints=taints,
            tags=tags,
            client_request_token=client_request_token,
            launch_template=launch_template,
            capacity_type=capacity_type,
            version=version,
            release_version=release_version,
            regionName=self.region_name,
            awsPartition=self.partition,
        )
        self.clusters[cluster_name].nodegroups[nodegroup_name] = nodegroup
        self.clusters[cluster_name].nodegroup_count += 1
        return nodegroup

    def describe_cluster(self, name):
        try:
            return self.clusters[name]
        except KeyError:
            exception = ResourceNotFoundException
            raise exception(
                CLUSTER_NOT_FOUND_MSG.format(
                    exception_name=exception.TYPE,
                    method=method_name(),
                    cluster_name=name,
                )
            )

    def describe_nodegroup(self, cluster_name, nodegroup_name):
        self.check_cluster_exists(cluster_name)
        try:
            return self.clusters[cluster_name].nodegroups[nodegroup_name]
        except KeyError:
            exception = ResourceNotFoundException
            raise exception(
                NODEGROUP_NOT_FOUND_MSG.format(
                    exception_name=exception.TYPE,
                    method=method_name(),
                    nodegroup_name=nodegroup_name,
                )
            )

    def delete_cluster(self, name):
        self.check_cluster_exists(name)
        if self.clusters[name].nodegroup_count:
            exception = ResourceInUseException
            raise exception(
                CLUSTER_IN_USE_MSG.format(
                    exception_name=exception.TYPE, method=method_name()
                )
            )

        result = self.clusters.pop(name)
        self.cluster_count -= 1
        return result

    def list_nodegroups(self, cluster_name, max_results, next_token):
        cluster = self.clusters[cluster_name]
        nodegroup_names = sorted(cluster.nodegroups.keys())
        start = nodegroup_names.index(next_token) if next_token else 0
        end = min(start + max_results, cluster.nodegroup_count)
        new_next = "null" if end == cluster.nodegroup_count else nodegroup_names[end]

        return nodegroup_names[start:end], new_next

    def check_cluster_exists(self, cluster_name):
        if cluster_name not in self.clusters:
            exception = ResourceNotFoundException
            raise exception(
                CLUSTER_NOT_FOUND_MSG.format(
                    exception_name=exception.TYPE,
                    method=method_name(parent=True),
                    cluster_name=cluster_name,
                )
            )


eks_backends = {}
for region in Session().get_available_regions("eks"):
    eks_backends[region] = EKSBackend(region)
for region in Session().get_available_regions("eks", partition_name="aws-us-gov"):
    eks_backends[region] = EKSBackend(region)
for region in Session().get_available_regions("eks", partition_name="aws-cn"):
    eks_backends[region] = EKSBackend(region)
